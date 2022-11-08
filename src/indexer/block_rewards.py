import logging
import asyncio

import pytz
from tqdm import tqdm
from prometheus_client import start_http_server, Gauge

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from providers.execution_node import ExecutionNode
from providers.http_client_w_backoff import RateLimited
from db.tables import BlockReward
from db.db_helpers import session_scope
from indexer.block_rewards_mev import get_block_reward_value

logger = logging.getLogger(__name__)

START_SLOT = 4700013  # First PoS slot
TIMEZONES_TO_INDEX = (
    pytz.utc,
)

ALREADY_INDEXED_SLOTS = set()

SLOTS_WITH_MISSING_BLOCK_REWARDS = Gauge(
    "slots_with_missing_block_rewards",
    "Slots for which block rewards still need to be indexed and inserted into the database",
)


async def index_block_rewards():
    global ALREADY_INDEXED_SLOTS
    beacon_node = BeaconNode()
    execution_node = ExecutionNode()

    slots_needed = [s for s in range(START_SLOT, (await beacon_node.head_slot()))]

    # Remove slots that have already been indexed previously
    logger.info("Removing previously indexed slots")
    if len(ALREADY_INDEXED_SLOTS) == 0:
        with session_scope() as session:
            ALREADY_INDEXED_SLOTS = [
                s for s, in session.query(BlockReward.slot).all()
            ]

    for s in ALREADY_INDEXED_SLOTS:
        slots_needed.remove(s)

    logger.info(f"Indexing block rewards for {len(slots_needed)} slots")
    SLOTS_WITH_MISSING_BLOCK_REWARDS.set(len(slots_needed))

    with session_scope() as session:
        for slot in tqdm(slots_needed):
            # Wait for slot to be finalized
            if not await beacon_node.is_slot_finalized(slot):
                logger.info(f"Waiting for slot {slot} to be finalized")
                continue

            logger.info(f"Indexing block rewards for slot {slot}") if slot % 100 == 0 else None

            # Retrieve block info
            slot_proposer_data = await beacon_node.get_slot_proposer_data(slot)

            if slot_proposer_data.block_number is None:
                # No block in this slot
                session.add(
                    BlockReward(
                        slot=slot,
                    )
                )
                ALREADY_INDEXED_SLOTS.append(slot)
                SLOTS_WITH_MISSING_BLOCK_REWARDS.dec(1)
                session.commit()
                continue

            try:
                priority_fees, contains_mev, mev_reward_recipient, mev_reward_value = await get_block_reward_value(slot_proposer_data)
            except (ValueError, AssertionError, RateLimited) as e:
                logger.error(f"Failed to process slot {slot} -> {str(e)}")
                continue
            block_extra_data = (await execution_node.get_miner_data(block_number=slot_proposer_data.block_number)).extra_data

            session.add(
                BlockReward(
                    slot=slot,
                    proposer_index=slot_proposer_data.proposer_index,
                    fee_recipient=slot_proposer_data.fee_recipient,
                    priority_fees=priority_fees,
                    block_extra_data=bytes.fromhex(block_extra_data[2:]) if block_extra_data else None,
                    mev=contains_mev,
                    mev_reward_recipient=mev_reward_recipient,
                    mev_reward_value=mev_reward_value,
                )
            )
            ALREADY_INDEXED_SLOTS.append(slot)
            SLOTS_WITH_MISSING_BLOCK_REWARDS.dec(1)
            session.commit()
        session.commit()


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(index_block_rewards())
        except Exception as e:
            logger.error(f"Error occurred while indexing block rewards: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(60)
