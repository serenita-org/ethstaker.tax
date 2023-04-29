import logging
import asyncio

from tqdm import tqdm
from prometheus_client import start_http_server, Gauge
from sqlalchemy import text
from sqlalchemy import func

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from db.tables import Withdrawal
from db.db_helpers import session_scope

logger = logging.getLogger(__name__)

START_SLOT = 6_209_536  # First post-Shapella slot

SLOTS_WITH_MISSING_WITHDRAWAL_DATA = Gauge(
    "slots_with_missing_withdrawal_data",
    "Slots for which withdrawals still need to be indexed and inserted into the database",
)


async def index_withdrawals():
    beacon_node = BeaconNode()

    # Remove slots that have already been indexed previously
    logger.info("Calculating where to start indexing")
    with session_scope() as session:
        LATEST_SLOT_IN_DB, = session.query(func.max(Withdrawal.slot)).one_or_none()
        logger.info(f"Latest slot: {LATEST_SLOT_IN_DB}")

        if LATEST_SLOT_IN_DB is not None:
            START_SLOT = LATEST_SLOT_IN_DB + 1

    slots_needed = {s for s in range(START_SLOT, (await beacon_node.head_finalized()) + 1)}
    logger.info(f"Slots needed: {slots_needed}")

    logger.info(f"Indexing withdrawals for {len(slots_needed)} slots")
    SLOTS_WITH_MISSING_WITHDRAWAL_DATA.set(len(slots_needed))
    commit_every = 10
    current_tx = 0
    with session_scope() as session:
        for slot in tqdm(sorted(slots_needed)):
            current_tx += 1

            logger.debug(f"Getting withdrawals for {slot}")
            withdrawals = await beacon_node.withdrawals_for_slot(slot=slot)
            if len(withdrawals) == 0:
                continue

            session.execute(
                text(
                    "INSERT INTO withdrawal(slot, validator_index, amount_gwei) VALUES(:slot, :validator_index, :amount_gwei)"
                ),
                [
                    {
                        "slot": withdrawal.slot,
                        "validator_index": withdrawal.validator_index,
                        "amount_gwei": withdrawal.amount_gwei,
                    }
                    for withdrawal in withdrawals
                ]
            )
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
