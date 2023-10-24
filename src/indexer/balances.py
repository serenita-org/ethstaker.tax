import datetime
import logging
import asyncio
import os
from collections import defaultdict

import pytz
import redis.asyncio as redis
from tqdm import tqdm
from prometheus_client import start_http_server, Gauge
from sqlalchemy import text

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode, GENESIS_DATETIME, SLOTS_PER_EPOCH
from db.tables import Balance
from db.db_helpers import session_scope

logger = logging.getLogger(__name__)

START_DATE = "2020-01-01"
TIMEZONES_TO_INDEX = (
    pytz.utc,
)

ALREADY_INDEXED_SLOTS = set()

SLOTS_WITH_MISSING_BALANCES = Gauge(
    "slots_with_missing_balances",
    "Slots for which balances still need to be indexed and inserted into the database",
)


async def index_balances():
    global ALREADY_INDEXED_SLOTS

    start_date = datetime.date.fromisoformat(START_DATE)
    end_date = datetime.date.today() + datetime.timedelta(days=1)

    beacon_node = BeaconNode()
    cache = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")))

    logger.info(f"Indexing balances for {len(TIMEZONES_TO_INDEX)} timezones.")
    slots_to_index = set()
    logger.debug(f"Calculating the needed slot numbers...")

    # Slot numbers for balances at activation slot
    # We only want to store activation balances for validators during their activation epoch
    # TODO uncomment when indexing act balances
    # validator_index_to_activation_slot = await beacon_node.activation_slots_for_validators(validator_indexes=None, cache=cache)
    validator_index_to_activation_slot = {}
    activation_slot_to_validators = defaultdict(list)
    for vi, as_ in validator_index_to_activation_slot.items():
        if as_ is not None:
            activation_slot_to_validators[as_].append(vi)
            # TODO uncomment once teku is historically synced again
            #  also block rewards indexer is confused by the 404s, it thinks the block were skipped... we will need to reindex all slots where proposer_index is null...
            #  ... think about adding a column to blocks table - boolean - processing_error insteat of using the cache - block rewards indexer
            #slots_to_index.add(as_)

    # Slot numbers for end-of-day balances
    eod_slots = set()
    for timezone in TIMEZONES_TO_INDEX:

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

        initial_slot = BeaconNode.slot_for_datetime(start_dt)
        slots = [initial_slot]

        current_dt = start_dt.replace(hour=23, minute=59, second=59)
        datetimes = []
        while current_dt <= end_dt:
            datetimes.append(current_dt)
            current_dt += datetime.timedelta(days=1)

        head_slot = beacon_node.head_slot()
        slots.extend(beacon_node.slot_for_datetime(dt) for dt in datetimes)

        # Cap slots at head slot
        slots = [s for s in slots if s < head_slot]

        for slot in slots:
            eod_slots.add(slot)
            # TODO uncomment I temporarily have 2 services indexing - the regular one only indexing activation balances,
            #  and the EOD one that independently only indexes EOD balances
            slots_to_index.add(slot)

    # Remove slots that have already been indexed previously
    logger.info("Removing previously indexed slots")
    if len(ALREADY_INDEXED_SLOTS) == 0:
        with session_scope() as session:
            ALREADY_INDEXED_SLOTS = [
                s for s, in session.query(Balance.slot).distinct().all()
            ]

    for s in ALREADY_INDEXED_SLOTS:
        try:
            slots_to_index.remove(s)
            eod_slots.remove(s)
        # TODO remove excepton handling
        except KeyError as e:
            pass

    # Order the slots - to retrieve the balances for the oldest slots first
    # TODO undo reverse
    slots_to_index = sorted(slots_to_index)

    logger.info(f"Indexing balances for {len(slots_to_index)} slots")
    SLOTS_WITH_MISSING_BALANCES.set(len(slots_to_index))

    commit_every = 1
    current_tx = 0
    with session_scope() as session:
        # TODO undo list + indexes
        for slot in tqdm((list(eod_slots) + list(slots_to_index))[:1000]):
            logger.info(f"Indexing slot {slot}")
            current_tx += 1

            # Wait for slot to be finalized
            # TODO uncomment
            if not await beacon_node.is_slot_finalized(slot):
                logger.info(f"Waiting for slot {slot} to be finalized")
                continue

            # Store balances in DB
            if slot in eod_slots:
                # Index balances for all validators
                balances_for_slot = await beacon_node.balances_for_slot(slot)
            else:
                # Activation slot - only index balances for validators which were activated at this point
                balances_for_slot = await beacon_node.balances_for_slot(
                    slot=slot, validator_indexes=activation_slot_to_validators[slot]
                )
            logger.debug(f"Executing insert statements for slot {slot}")
            if len(balances_for_slot) == 0:
                # No balances available for slot (yet?), move on
                logger.warning(f"No balances retrieved for slot {slot}")
                continue
            session.execute(
                text(
                    "INSERT INTO balance(validator_index, slot, balance)"
                    " VALUES(:validator_index, :slot, :balance)"
                    " ON CONFLICT ON CONSTRAINT balance_pkey DO NOTHING"
                ),
                [
                    {
                        "validator_index": balance.validator_index,
                        "slot": balance.slot,
                        "balance": balance.balance,
                    }
                    for balance in balances_for_slot
                ]
            )
            ALREADY_INDEXED_SLOTS.append(slot)
            SLOTS_WITH_MISSING_BALANCES.dec(1)
            if current_tx == commit_every:
                logger.debug("Committing")
                current_tx = 0
                session.commit()
        session.commit()


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(index_balances())
        except Exception as e:
            logger.error(f"Error occurred while indexing balances: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(300)
