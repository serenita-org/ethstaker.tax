import logging
import asyncio
import os

from tqdm import tqdm
from prometheus_client import start_http_server, Gauge
from sqlalchemy import text

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from db.tables import Withdrawal
from db.db_helpers import session_scope

logger = logging.getLogger(__name__)

START_SLOT = 6_209_536  # First post-Shapella slot

ALREADY_INDEXED_SLOTS = set()

SLOTS_WITH_MISSING_WITHDRAWAL_DATA = Gauge(
    "slots_with_missing_withdrawal_data",
    "Slots for which withdrawals still need to be indexed and inserted into the database",
)


async def index_withdrawals():
    global ALREADY_INDEXED_SLOTS
    beacon_node = BeaconNode()

    slots_needed = {s for s in range(START_SLOT, (await beacon_node.head_slot()))}

    # Remove slots that have already been indexed previously
    if not os.getenv("INDEX_ALL") == "true":
        logger.info("Removing previously indexed slots")
        if len(ALREADY_INDEXED_SLOTS) == 0:
            with session_scope() as session:
                ALREADY_INDEXED_SLOTS = {s for s, in
                                         session.query(Withdrawal.slot).all()}
        slots_needed = slots_needed.difference(ALREADY_INDEXED_SLOTS)

    logger.info(f"Indexing withdrawals for {len(slots_needed)} slots")
    SLOTS_WITH_MISSING_WITHDRAWAL_DATA.set(len(slots_needed))
    commit_every = 100
    current_tx = 0
    with session_scope() as session:
        for slot in tqdm(sorted(slots_needed, reverse=True)):
            current_tx += 1

            # Wait for slot to be finalized
            if not await beacon_node.is_slot_finalized(slot):
                SLOTS_WITH_MISSING_WITHDRAWAL_DATA.dec(1)
                logger.info(f"Waiting for slot {slot} to be finalized")
                continue

            logger.debug(f"Getting withdrawals for {slot}")
            withdrawals = await beacon_node.withdrawals_for_slot(slot=slot)
            if len(withdrawals) == 0:
                continue

            session.execute(
                text(
                    "INSERT INTO withdrawal(slot, validator_index, amount) VALUES(:slot, :validator_index, :amount)"
                ),
                [
                    {
                        "slot": withdrawal.slot,
                        "validator_index": withdrawal.validator_index,
                        "amount": withdrawal.amount,
                    }
                    for withdrawal in withdrawals
                ]
            )
            ALREADY_INDEXED_SLOTS.add(slot)
            SLOTS_WITH_MISSING_WITHDRAWAL_DATA.dec(1)
            if current_tx == commit_every:
                logger.debug(f"Committing @ {slot}")
                current_tx = 0
                session.commit()


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(index_withdrawals())
        except Exception as e:
            logger.error(f"Error occurred while indexing withdrawals: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(60)
