import logging
import asyncio

import pytz
from tqdm import tqdm
from prometheus_client import start_http_server, Gauge

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from providers.execution_node import ExecutionNode
from db.tables import BlockReward
from db.db_helpers import session_scope
from indexer.block_rewards_mev import MEV_BUILDERS, MevPayoutType

logger = logging.getLogger(__name__)

START_SLOT = 4700013 # First PoS slot
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

            if slot % 10 == 0:
                logger.info(f"Indexing block rewards for slot {slot}")

            # Retrieve block info
            block_reward_data = await beacon_node.get_block_reward_data(slot)

            if block_reward_data.block_number is None:
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

            # Check if MEV
            block_contains_mev = False
            if block_reward_data.fee_recipient in MEV_BUILDERS.keys():
                # Definitely MEV block
                block_contains_mev = True
                expected_mev_payout_type = MEV_BUILDERS[block_reward_data.fee_recipient].payout_type
                if expected_mev_payout_type != MevPayoutType.LAST_TX:
                    raise ValueError(
                        f"Fee recipient is a builder but has unsupported payout type {expected_mev_payout_type}")

                tx_count = await execution_node.get_block_tx_count(block_number=block_reward_data.block_number)
                last_tx = await execution_node.get_tx_data(block_number=block_reward_data.block_number,
                                                           tx_index=tx_count - 1)
                assert last_tx.from_ == block_reward_data.fee_recipient
                proposer_reward = last_tx.value
            else:
                # Fee recipient is not a known MEV builder
                # This could still be MEV but built by Manifold/other builders who do not override
                # the fee recipient and therefore don't have to make a transaction to pay out rewards
                miner_data = await execution_node.get_miner_data(block_number=block_reward_data.block_number)

                if miner_data.extra_data in ("Manifold", ):
                    block_contains_mev = True
                    logger.debug(f"MEV found in {block_reward_data.block_number} through extra data - {miner_data.extra_data}")

                # Check transactions in block for the MEV recipient by checking for:
                # - coinbase different from fee recipient
                if miner_data.coinbase != block_reward_data.fee_recipient:
                    raise ValueError(f"Coinbase {miner_data.coinbase} != fee recipient {block_reward_data.fee_recipient}, block number {block_reward_data.block_number}")

                burnt_tx_fees = await execution_node.get_burnt_tx_fees_for_block(block_number=block_reward_data.block_number)
                logger.debug(f"Proposer reward: {miner_data.tx_fee} - {burnt_tx_fees}")
                proposer_reward = miner_data.tx_fee - burnt_tx_fees

            session.add(
                BlockReward(
                    slot=slot,
                    proposer_index=block_reward_data.proposer_index,
                    fee_recipient=block_reward_data.fee_recipient,
                    proposer_reward=proposer_reward,
                    mev=block_contains_mev,
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
