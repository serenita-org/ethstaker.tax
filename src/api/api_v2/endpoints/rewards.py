import datetime
import json
import logging
from collections import defaultdict
from decimal import Decimal

import pytz
from redis import Redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter

from api.api_v2.models import RewardsRequest, ValidatorRewards, RewardForDate
from db.tables import Balance
from providers.beacon_node import BeaconNode, depends_beacon_node
from providers.db_provider import DbProvider, depends_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(  # POST method to support bigger requests
    "/rewards",
    response_model=list[ValidatorRewards],
)
async def rewards(
    rewards_request: RewardsRequest,
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    db_provider: DbProvider = Depends(depends_db),
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
):
    # Handle inputs
    if rewards_request.end_date <= rewards_request.start_date:
        raise HTTPException(
            status_code=400, detail=f"End date must be after start date"
        )
    validator_indexes = list(set(rewards_request.validator_indexes))

    # Cap end date at previous day - income and price for today (current day)
    # are not final yet
    today = datetime.datetime.now(tz=pytz.UTC).date()
    rewards_request.end_date = min(rewards_request.end_date, today - datetime.timedelta(days=1))

    start_datetime = datetime.datetime(
        year=rewards_request.start_date.year,
        month=rewards_request.start_date.month,
        day=rewards_request.start_date.day,
        tzinfo=pytz.UTC,
    )
    end_datetime = datetime.datetime(
        year=rewards_request.end_date.year,
        month=rewards_request.end_date.month,
        day=rewards_request.end_date.day,
        tzinfo=pytz.UTC,
    )
    min_slot = beacon_node.slot_for_datetime(start_datetime)
    max_slot = beacon_node.slot_for_datetime(datetime.datetime.combine(
        end_datetime,
        datetime.time(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
    ))

    # Let's get the rewards
    first_slot_in_requested_period = min_slot
    activation_slots = await beacon_node.activation_slots_for_validators(validator_indexes=validator_indexes, cache=cache)
    consensus_layer_rewards: dict[int, list[RewardForDate]] = defaultdict(list)
    execution_layer_rewards: dict[int, list[RewardForDate]] = defaultdict(list)
    withdrawals: dict[int, list[RewardForDate]] = defaultdict(list)

    # - Get initial balances
    logger.debug(f"Getting initial balances")
    initial_balances = {}
    pending_validator_indexes = set()
    for validator_index in validator_indexes:
        act_slot = activation_slots[validator_index]
        if act_slot is None:
            # Pending validator without an activation slot
            pending_validator_indexes.add(validator_index)
            continue

        if act_slot > first_slot_in_requested_period:
            initial_balance = Balance(
                slot=act_slot,
                validator_index=validator_index,
                balance=32,
            )
        else:
            initial_balance_slot = BeaconNode.slot_for_datetime(dt=start_datetime)
            initial_balance = db_provider.balances(
                slots=[initial_balance_slot],
                validator_indexes=[validator_index],
            )[0]
        initial_balances[validator_index] = initial_balance

    # - Get all end-of-day balances
    logger.debug(f"Getting EOD balances")
    range_day_count = (end_datetime - start_datetime).days + 1
    eod_slots = [
        beacon_node.slot_for_datetime(
            dt=datetime.datetime.combine(
                (rewards_request.start_date + datetime.timedelta(days=day_idx)),
                time=datetime.time(hour=23, minute=59, second=59),
                tzinfo=pytz.UTC,
            )
        )
        for day_idx in range(range_day_count)
    ]
    eod_balances = db_provider.balances(slots=eod_slots, validator_indexes=validator_indexes)

    # Get all withdrawals
    logger.debug(f"Getting withdrawals")
    all_withdrawals = db_provider.withdrawals(
        min_slot=min_slot,
        max_slot=max_slot,
        validator_indexes=validator_indexes
    )

    # Get all block rewards
    logger.debug(f"Getting block rewards")
    all_block_rewards = db_provider.block_rewards(
        min_slot=min_slot,
        max_slot=max_slot,
        proposer_indexes=validator_indexes
    )
    # Check if all execution layer rewards were processed correctly
    for br in all_block_rewards:
        if not br.reward_processed_ok:
            msg = (f"Execution layer rewards not available"
                   f" - missing data for proposer {br.proposer_index} - {br.slot}")
            logger.error(msg)
            raise HTTPException(
                status_code=500,
                detail=msg
            )

    total_validators = len(validator_indexes)
    for idx, validator_index in enumerate(validator_indexes):
        logger.debug(f"Processing {validator_index} - {100 * idx / total_validators:.2f}%")
        if validator_index in pending_validator_indexes:
            continue
        prev_balance = initial_balances[validator_index]

        validator_withdrawals = [w for w in all_withdrawals if w.validator_index == validator_index]
        for eod_balance in [eodb for eodb in eod_balances if eodb.validator_index == validator_index]:
            amount_earned_wei = Decimal(1e18) * (eod_balance.balance - prev_balance.balance)

            # Account for withdrawals
            amount_withdrawn_this_day_wei = Decimal(1e9) * sum(
                w.amount_gwei for w in validator_withdrawals
                if eod_balance.slot >= w.slot > prev_balance.slot
            )
            amount_earned_wei += amount_withdrawn_this_day_wei

            date = beacon_node.datetime_for_slot(
                slot=eod_balance.slot,
                timezone=pytz.UTC,
            )
            consensus_layer_rewards[validator_index].append(
                RewardForDate.construct(
                    date=date,
                    amount_wei=amount_earned_wei,
                )
            )
            if amount_withdrawn_this_day_wei > 0:
                withdrawals[validator_index].append(
                    RewardForDate.construct(
                        date=date,
                        amount_wei=amount_withdrawn_this_day_wei
                    )
                )
            prev_balance = eod_balance

        # Sum in case multiple blocks proposed on same day
        exec_layer_rewards_for_date = defaultdict(int)
        for br in [br for br in all_block_rewards if br.proposer_index == validator_index]:
            exec_layer_rewards_for_date[
                beacon_node.datetime_for_slot(br.slot, pytz.UTC).date()
            ] += br.mev_reward_value_wei if br.mev else br.priority_fees_wei
        for date, rewards_sum in sorted(exec_layer_rewards_for_date.items()):
            execution_layer_rewards[validator_index].append(
                RewardForDate.construct(
                    date=date,
                    amount_wei=rewards_sum
                )
            )

    return [
        ValidatorRewards.construct(
            validator_index=validator_index,
            consensus_layer_rewards=consensus_layer_rewards[validator_index],
            execution_layer_rewards=execution_layer_rewards[validator_index],
            withdrawals=withdrawals[validator_index],
        ) for validator_index in validator_indexes if validator_index not in pending_validator_indexes
    ]