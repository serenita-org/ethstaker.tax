import asyncio
import json
import os
import logging
import gc

from aioredis import create_redis
from httpx import AsyncClient
from prometheus_client import start_http_server, Gauge

from providers.beacon_node import BeaconNode, SLOTS_PER_EPOCH
from shared.setup_logging import setup_logging

logger = logging.getLogger(__name__)

CACHE_KEY_ATTESTATION_DATA = "indexer_merge_attestation_data"
CACHE_KEY_ACTIVE_VALIDATORS = "indexer_merge_validators_active"
CACHE_KEY_ALREADY_INDEXED_EPOCHS = "indexer_merge_indexed_epochs"
CACHE_KEY_TOTAL_DIFFICULTY = "indexer_merge_total_difficulty"
CACHE_KEY_BLOCK_NUMBER = "indexer_merge_block_number"
CACHE_KEY_VALIDATOR_INCLUSION = "indexer_merge_validator_inclusion"

START_EPOCH = 144_000  # Bellatrix was at 144896

PRUNING_LIMIT_VAL_INCLUSION = 20
PRUNING_LIMIT_ATT_DATA_RECENT = 0
PRUNING_HISTORICAL_KEEP_EVERY = 25

METRIC_BLOCK_NUMBER = Gauge(
    "indexer_merge_block_number",
    "Current block number as reported by Besu",
)

METRIC_TOTAL_DIFFICULTY = Gauge(
    "indexer_merge_total_difficulty",
    "Total difficulty as reported by Besu",
)

METRIC_ATTESTATION_DATA_HEAD = Gauge(
    "indexer_merge_att_data_head",
    "Latest epoch for which we have detailed attestation data",
)


def process_epoch_participation_data(participation_data: list[str]) -> dict[str, int]:
    indexes_missing = 0
    indexes_timely_source = 0
    indexes_timely_target = 0
    indexes_timely_head = 0
    validators_active = 0

    for idx, status in enumerate(participation_data):
        validators_active += 1
        if status == "0":
            indexes_missing += 1
            continue

        if status in ("1", "3", "5", "7"):
            indexes_timely_source += 1
        if status in ("2", "3", "6", "7"):
            indexes_timely_target += 1
        if status in ("4", "5", "6", "7"):
            indexes_timely_head += 1

    return dict(
        indexes_missing=indexes_missing,
        indexes_timely_source=indexes_timely_source,
        indexes_timely_target=indexes_timely_target,
        indexes_timely_head=indexes_timely_head,
        validators_active=validators_active,
    )


async def get_current_total_difficulty():
    EXEC_NODE_RPC_URL = "http://100.94.206.119:8545"
    cache = await create_redis(f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")

    while True:
        logger.info(f"Getting total difficulty")

        try:
            async with AsyncClient() as client:
                response = await client.post(EXEC_NODE_RPC_URL, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                })

                block_number_hex = response.json()["result"]
                block_number = int(block_number_hex, 16)
                await cache.set(CACHE_KEY_BLOCK_NUMBER, block_number)
                METRIC_BLOCK_NUMBER.set(block_number)

                response = await client.post(EXEC_NODE_RPC_URL, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [
                        block_number_hex,
                        False
                    ],
                    "id": 1,
                })

                total_difficulty = int(response.json()["result"]["totalDifficulty"], 16)
                await cache.set(CACHE_KEY_TOTAL_DIFFICULTY, total_difficulty)
                METRIC_TOTAL_DIFFICULTY.set(total_difficulty)
        except Exception as e:
            logger.exception(f"Exception occurred in get_current_total_difficulty - {repr(e)}")

        await asyncio.sleep(5)


async def get_current_validator_inclusion():
    beacon_node = BeaconNode()
    cache = await create_redis(f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")

    while True:
        logger.info(f"Getting validator inclusion")

        try:
            current_head_slot = await beacon_node.head_slot()
            prev_epoch = (current_head_slot // SLOTS_PER_EPOCH) - 1
            if beacon_node._use_infura():
                # Infura doesn't expose this Teku endpoint...
                await asyncio.sleep(1_000_000)
                continue
            data = await beacon_node.get_validator_inclusion_global(prev_epoch)


            # Store in cache
            try:
                all_epochs_data = json.loads(await cache.get(CACHE_KEY_VALIDATOR_INCLUSION))
            except Exception as e:
                logger.warning(f"No CACHE_KEY_VALIDATOR_INCLUSION data retrieved, starting from scratch - {repr(e)}")
                all_epochs_data = {}

            # Prune old data
            keys_to_delete = set()
            for epoch, att_data in all_epochs_data.items():
                if int(epoch) < (prev_epoch + 1 - PRUNING_LIMIT_VAL_INCLUSION) and int(epoch) % PRUNING_HISTORICAL_KEEP_EVERY != 0:
                    logger.info(f"Pruning epoch {epoch} from validator inclusion  data")
                    keys_to_delete.add(epoch)

            for ktd in keys_to_delete:
                all_epochs_data.pop(ktd)

            all_epochs_data[prev_epoch] = data
            await cache.set(CACHE_KEY_VALIDATOR_INCLUSION, json.dumps(all_epochs_data))
        except Exception as e:
            logger.exception(f"Exception occurred in get_current_validator_inclusion - {repr(e)}")

        await asyncio.sleep(60)


async def index_attestations():
    beacon_node = BeaconNode()
    cache = await create_redis(f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}")

    while True:
        # Trigger garbage collection manually to avoid memory leak
        logger.info(f"Garbage collecting...")
        gc.collect()

        epochs_needed = []

        current_head_slot = await beacon_node.head_slot()
        current_head_epoch = current_head_slot // 32
        for epoch in range(START_EPOCH, 1 + (await beacon_node.head_slot()) // SLOTS_PER_EPOCH):  # inclusive range
            # Accessing old states is slow - only get every n-th state until we catch up with the chain head
            # Current setting - every 50th epoch and
            if epoch < (current_head_epoch - PRUNING_LIMIT_ATT_DATA_RECENT) and epoch % PRUNING_HISTORICAL_KEEP_EVERY != 0:
                continue
            epochs_needed.append(epoch)

        # Remove epochs for which we already retrieved the data
        try:
            already_indexed_epochs = json.loads((await cache.get(CACHE_KEY_ALREADY_INDEXED_EPOCHS)))
            for aie in already_indexed_epochs:
                if aie in epochs_needed:
                    epochs_needed.remove(aie)
        except Exception as e:
            logger.warning(f"No indexed epochs retrieved, starting from scratch - {repr(e)}")
            already_indexed_epochs = []

        logger.info(f"Epochs needed [{len(epochs_needed)}]: {sorted(epochs_needed)}")
        if len(epochs_needed) <= 2:
            # Let the beacon node rest a bit if we're caught up
            await asyncio.sleep(60)

        for current_epoch in list(sorted(epochs_needed, reverse=True))[:3]:
            # To get complete data for the current epoch, we need to look at the last state of the next epoch
            state_id = ((current_epoch + 1) * SLOTS_PER_EPOCH) + (SLOTS_PER_EPOCH - 1)
            current_head_slot = await beacon_node.head_slot()
            if state_id < current_head_slot:
                complete_data_for_current_epoch_available = True
            else:
                # this was different during merge for real, now only storing epochs once they are finalized
                logger.warning(f"Not indexing {current_epoch} - no complete data yet")
                continue
                complete_data_for_current_epoch_available = False
                state_id = current_head_slot
                logger.info(f"No complete data for {current_epoch}, using current head slot as state id = {state_id}")
                # This is a temporary state - only makes sense to retrieve it for the ongoing epoch
                if current_epoch < (current_head_slot // SLOTS_PER_EPOCH):
                    logger.info(
                        f"Skipping {current_epoch} - {state_id} not in current epoch and complete data not available yet")
                    continue

            # retrieve state from beacon node, save important stuff to redis
            logger.info(f"Getting beacon state for epoch {current_epoch} @ {state_id}")
            state_data_dict = await beacon_node.get_full_state(state_id)

            # Store summary to Redis
            try:
                all_data = json.loads(await cache.get(CACHE_KEY_ATTESTATION_DATA))
            except Exception:
                logger.warning("No data present in Redis, starting with empty dict")
                all_data = {}

            if complete_data_for_current_epoch_available:
                participation_data = process_epoch_participation_data(state_data_dict.pop("previous_epoch_participation"))
                # No need to store # of active validators at that point in time
                _ = participation_data.pop("validators_active")
                all_data[str(current_epoch)] = participation_data
                # If >2/3 voted for it, we can consider it done?

                if await beacon_node.is_slot_finalized(current_epoch * SLOTS_PER_EPOCH):
                    logger.info(f"Epoch {current_epoch} finalized, marking as indexed")
                    already_indexed_epochs.append(current_epoch)
                else:
                    logger.warning(f"Epoch {current_epoch} not finalized yet...")
            else:
                # Final data not available yet - which epoch did we get data for by using head?
                current_epoch_bn = current_head_slot // SLOTS_PER_EPOCH
                all_data[str(current_epoch_bn - 1)] = process_epoch_participation_data(state_data_dict.pop("previous_epoch_participation"))
                curr_epoch_data = process_epoch_participation_data(state_data_dict.pop("current_epoch_participation"))
                await cache.set(CACHE_KEY_ACTIVE_VALIDATORS, curr_epoch_data.get("validators_active"))
                all_data[str(current_epoch_bn)] = curr_epoch_data

            # Reduce memory usage
            del state_data_dict

            # Remove old detailed data (prune)
            # - keep epoch-per-epoch data for last 50 epochs
            # - the rest only keep every 50th epoch
            keys_to_delete = set()
            head_epoch = await beacon_node.head_slot() // SLOTS_PER_EPOCH
            for epoch, att_data in all_data.items():
                if int(epoch) < (head_epoch - PRUNING_LIMIT_ATT_DATA_RECENT) and int(epoch) % PRUNING_HISTORICAL_KEEP_EVERY != 0:
                    logger.info(f"Pruning epoch {epoch} from att  data")
                    keys_to_delete.add(epoch)

            for ktd in keys_to_delete:
                all_data.pop(ktd)
                if int(ktd) in already_indexed_epochs:
                    already_indexed_epochs.remove(int(ktd))

            await cache.set(CACHE_KEY_ATTESTATION_DATA, json.dumps(dict(sorted(all_data.items()))))
            await cache.set(CACHE_KEY_ALREADY_INDEXED_EPOCHS, json.dumps(already_indexed_epochs))

            METRIC_ATTESTATION_DATA_HEAD.set(max(already_indexed_epochs))


async def main():
    await asyncio.gather(
        index_attestations(),
#        get_current_total_difficulty(),
        get_current_validator_inclusion(),
    )

if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Error occurred while indexing merge data: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(1)
