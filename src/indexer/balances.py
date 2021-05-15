import datetime
from contextlib import contextmanager

import asyncio
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tqdm import tqdm
from prometheus_client import start_http_server, Gauge

from shared.setup_logging import setup_logging
from shared.config import config
from providers.beacon_node import BeaconNode, GENESIS_DATETIME
from db.tables import Balance


logger = setup_logging(name=__file__)
engine = create_engine(config["db"]["url"], executemany_mode="batch")

START_DATE = "2020-01-01"

ALREADY_INDEXED_SLOTS = set()

slots_with_missing_balances = Gauge(
    "slots_with_missing_balances",
    "Slots for which balances still need to be indexed and inserted into the database",
)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


async def index_balances():
    global ALREADY_INDEXED_SLOTS

    start_date = datetime.date.fromisoformat(START_DATE)
    end_date = datetime.date.today() + datetime.timedelta(days=1)

    beacon_node = BeaconNode(
        host=config["beacon_node"]["host"],
        port=config["beacon_node"]["port"],
        response_timeout=300,
    )

    logger.info(f"Indexing balances for {len(pytz.common_timezones)} timezones.")
    slots_needed = set()
    logger.debug(f"Calculating the needed slot numbers...")
    for timezone in pytz.common_timezones:
        timezone = pytz.timezone(timezone)

        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.min)
        start_dt = timezone.localize(start_dt)
        end_dt = timezone.localize(end_dt)

        # Cap the start datetime at genesis
        start_dt = max(start_dt.astimezone(pytz.utc), GENESIS_DATETIME)
        start_dt = start_dt.astimezone(timezone)

        # Cap the end date at today
        end_dt = min(
            end_dt.astimezone(pytz.utc),
            datetime.datetime.utcnow().replace(tzinfo=pytz.utc),
        )
        end_dt = end_dt.astimezone(timezone)

        initial_slot = await BeaconNode.slot_for_datetime(start_dt)
        slots = [initial_slot]

        current_dt = start_dt.replace(hour=23, minute=59, second=59)
        datetimes = []
        while current_dt <= end_dt:
            datetimes.append(current_dt)
            current_dt += datetime.timedelta(days=1)

        head_slot = await beacon_node.head_slot()
        slots.extend(
            await asyncio.gather(
                *(beacon_node.slot_for_datetime(dt) for dt in datetimes)
            )
        )

        # Cap slots at head slot
        slots = [s for s in slots if s < head_slot]

        for slot in slots:
            slots_needed.add(slot)

    # Remove slots that have already been retrieved previously
    logger.info("Removing previously retrieved slots")
    if len(ALREADY_INDEXED_SLOTS) == 0:
        with session_scope() as session:
            ALREADY_INDEXED_SLOTS = [
                s for s, in session.query(Balance.slot).distinct().all()
            ]

    for s in ALREADY_INDEXED_SLOTS:
        slots_needed.remove(s)

    # Order the slots - to retrieve the balances for the oldest slots first
    slots_needed = sorted(slots_needed)

    logger.info(f"Getting balances for {len(slots_needed)} slots")
    slots_with_missing_balances.set(len(slots_needed))

    commit_every = 3
    current_tx = 0
    with session_scope() as session:
        for slot in tqdm(slots_needed):
            current_tx += 1
            # Store balances in DB
            logger.debug(f"Executing insert statements for slot {slot}")
            balances_for_slot = await beacon_node.balances_for_slot(slot)
            if len(balances_for_slot) == 0:
                # No balances available for slot (yet?), move on
                continue
            session.execute(
                "INSERT INTO balance(validator_index, slot, balance) VALUES(:validator_index, :slot, :balance)",
                [
                    {
                        "validator_index": balance.validator_index,
                        "slot": balance.slot,
                        "balance": balance.balance,
                    }
                    for balance in balances_for_slot
                ],
            )
            ALREADY_INDEXED_SLOTS.append(slot)
            slots_with_missing_balances.dec(1)
            if current_tx == commit_every:
                logger.debug("Committing")
                current_tx = 0
                session.commit()
        session.commit()


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    from time import sleep

    loop = asyncio.get_event_loop()
    try:
        while True:
            loop.run_until_complete(index_balances())
            logger.info("Sleeping for a minute now")
            sleep(60)
    except KeyboardInterrupt:
        loop.close()
