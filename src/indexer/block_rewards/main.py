import json
import logging
import asyncio
import os

import pytz
from tqdm import tqdm
from prometheus_client import start_http_server, Gauge

import redis
from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from providers.execution_node import ExecutionNode
from providers.http_client_w_backoff import RateLimited
from db.tables import BlockReward
from db.db_helpers import session_scope
from indexer.block_rewards.block_rewards_mev_simple import get_block_reward_value, ManualInspectionRequired

logger = logging.getLogger(__name__)

START_SLOT = 4700013  # First PoS slot
TIMEZONES_TO_INDEX = (
    pytz.utc,
)

ALREADY_INDEXED_SLOTS = set()
CACHE_KEY_MISSING_DATA = "INDEXER_BLOCK_REWARDS_MISSING_DATA"

SLOTS_WITH_MISSING_BLOCK_REWARDS = Gauge(
    "slots_with_missing_block_rewards",
    "Slots for which block rewards still need to be indexed and inserted into the database",
)
SLOTS_INDEXING_FAILURES = Gauge(
    "slots_indexing_failures",
    "Slots where indexing failed"
)
SLOT_BEING_INDEXED = Gauge(
    "slot_being_indexed",
    "The slot that is currently being indexed",
)


def _get_redis() -> redis.Redis:
    return redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))


def reset_missing_data_cache() -> None:
    _redis = _get_redis()
    _redis.set(CACHE_KEY_MISSING_DATA, json.dumps({}))


def update_missing_data_cache(proposer_index: int, slot_w_missing_data: int) -> None:
    _redis = _get_redis()

    cache_data = _redis.get(CACHE_KEY_MISSING_DATA)
    if cache_data is not None:
        cache_data = json.loads(cache_data)

    proposer_missing_data = cache_data.get(proposer_index, [])
    if slot_w_missing_data not in proposer_missing_data:
        proposer_missing_data.append(slot_w_missing_data)

    cache_data[proposer_index] = proposer_missing_data

    logger.info(f"Updating missing execution layer rewards data -> {cache_data}")
    _redis.set(CACHE_KEY_MISSING_DATA, json.dumps(cache_data))


async def index_block_rewards():
    global ALREADY_INDEXED_SLOTS
    beacon_node = BeaconNode()
    execution_node = ExecutionNode()

    slots_needed = {s for s in range(START_SLOT, (await beacon_node.head_slot()))}

    # Remove slots that have already been indexed previously
    if not os.getenv("INDEX_ALL") == "true":
        logger.info("Removing previously indexed slots")
        if len(ALREADY_INDEXED_SLOTS) == 0:
            with session_scope() as session:
                ALREADY_INDEXED_SLOTS = {s for s, in session.query(BlockReward.slot).all()}
        slots_needed = slots_needed.difference(ALREADY_INDEXED_SLOTS)

    logger.info(f"Indexing block rewards for {len(slots_needed)} slots")
    SLOTS_WITH_MISSING_BLOCK_REWARDS.set(len(slots_needed))

    with session_scope() as session:
        for slot in tqdm(sorted(slots_needed, reverse=True)):
            # Wait for slot to be finalized
            if not await beacon_node.is_slot_finalized(slot):
                SLOTS_WITH_MISSING_BLOCK_REWARDS.dec(1)
                logger.info(f"Waiting for slot {slot} to be finalized")
                continue

            logger.info(f"Indexing block rewards for slot {slot}") if slot % 100 == 0 else None
            SLOT_BEING_INDEXED.set(slot)

            # Retrieve block info
            slot_proposer_data = await beacon_node.get_slot_proposer_data(slot)

            if slot_proposer_data.block_number is None:
                # No block in this slot
                session.merge(
                    BlockReward(
                        slot=slot,
                    ),
                )
                ALREADY_INDEXED_SLOTS.add(slot)
                SLOTS_WITH_MISSING_BLOCK_REWARDS.dec(1)
                session.commit()
                continue

            try:
                block_reward_value = await get_block_reward_value(slot_proposer_data, execution_node=execution_node)
            except (ManualInspectionRequired, AssertionError, RateLimited) as e:
                logger.error(f"Failed to process slot {slot} -> {str(e)}")
                update_missing_data_cache(proposer_index=slot_proposer_data.proposer_index, slot_w_missing_data=slot)
                SLOTS_INDEXING_FAILURES.inc(1)
                continue

            block_extra_data = (
                await execution_node.get_miner_data(block_number=slot_proposer_data.block_number)).extra_data
            session.merge(
                BlockReward(
                    slot=slot,
                    proposer_index=slot_proposer_data.proposer_index,
                    fee_recipient=slot_proposer_data.fee_recipient,
                    priority_fees=block_reward_value.block_priority_tx_fees,
                    block_extra_data=bytes.fromhex(block_extra_data[2:]) if block_extra_data else None,
                    mev=block_reward_value.contains_mev,
                    mev_reward_recipient=block_reward_value.mev_recipient,
                    mev_reward_value=block_reward_value.mev_recipient_balance_change,
                ),
            )
            ALREADY_INDEXED_SLOTS.add(slot)
            SLOTS_WITH_MISSING_BLOCK_REWARDS.dec(1)
            session.commit()
        session.commit()


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()
    reset_missing_data_cache()

    from time import sleep

    while True:
        try:
            asyncio.run(index_block_rewards())
        except Exception as e:
            logger.error(f"Error occurred while indexing block rewards: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(300)