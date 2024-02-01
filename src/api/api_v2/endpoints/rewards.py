import datetime
import logging
from collections import defaultdict
from decimal import Decimal
from math import floor

import pytz
from redis import Redis
from fastapi import APIRouter, Depends, HTTPException
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter

from api.api_v2.models import RewardsRequest, ValidatorRewards, RewardForDate, \
    RocketPoolValidatorRewards, RewardsResponseRocketPool, RewardsResponseFull, RocketPoolNodeRewardForDate
from db.tables import Withdrawal, RocketPoolBondReduction
from providers.beacon_node import BeaconNode, depends_beacon_node
from providers.db_provider import DbProvider, depends_db
from providers.execution_node import ExecutionNode
from providers.rocket_pool import SMOOTHING_POOL_ADDRESS, RocketPoolDataProvider

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_rocket_pool_reward_share_withdrawal_for_bond_fee(withdrawal, bond, fee):
    _FULL_MINIPOOL_BOND = 32 * Decimal(1e18)

    if withdrawal.amount > 8 * Decimal(1e18):
        # Consider this a full withdrawal
        # TODO
        # We need to take into account "penalties",
        # see _distributeBalance

        # uint256 nodeAmount = 0;
        #         uint256 userCapital = getUserDepositBalance();
        #         // Check if node operator was slashed
        #         if (_balance < userCapital) {
        #             // Only slash on first call to distribute
        #             if (withdrawalBlock == 0) {
        #                 // Record shortfall for slashing
        #                 nodeSlashBalance = userCapital.sub(_balance);
        #             }

        # First check - if the withdrawal amount is less than the "user" part
        # the node operator gets nothing (likely due to being slashed)
        # -> they will actually lose RPL from their node's RPL collateral
        # -> that will not be part of the output, not supported for now
        # TODO

        # nodeAmount = _calculateNodeShare(_balance);
        #     function _calculateNodeShare(uint256 _balance) internal view returns (uint256) {
        #         uint256 userCapital = getUserDepositBalance();
        #         uint256 nodeCapital = nodeDepositBalance;
        #         uint256 nodeShare = 0;
        #         // Calculate the total capital (node + user)
        #         uint256 capital = userCapital.add(nodeCapital);
        #         if (_balance > capital) {
        #             // Total rewards to share
        #             uint256 rewards = _balance.sub(capital);
        #             nodeShare = nodeCapital.add(calculateNodeRewards(nodeCapital, userCapital, rewards));
        #         } else if (_balance > userCapital) {
        #             nodeShare = _balance.sub(userCapital);
        #         }
        #         // Check if node has an ETH penalty
        #         uint256 penaltyRate = RocketMinipoolPenaltyInterface(rocketMinipoolPenalty).getPenaltyRate(address(this));
        #         if (penaltyRate > 0) {
        #             uint256 penaltyAmount = nodeShare.mul(penaltyRate).div(calcBase);
        #             if (penaltyAmount > nodeShare) {
        #                 penaltyAmount = nodeShare;
        #             }
        #             nodeShare = nodeShare.sub(penaltyAmount);
        #         }
        #         return nodeShare;

        pass

    return Decimal(1e9) * withdrawal.amount * (
        # NO bond part
        (bond / _FULL_MINIPOOL_BOND)
        # User bond part - commission
        + ((_FULL_MINIPOOL_BOND - bond) / _FULL_MINIPOOL_BOND) * (fee / Decimal(1e18))
    )


def get_rocket_pool_reward_share_withdrawal(withdrawal: Withdrawal, bond_reductions: list[RocketPoolBondReduction], initial_bond: Decimal, initial_fee: Decimal) -> RewardForDate:
    # Figure out correct bond & fee for this withdrawal
    withdrawal_dt = BeaconNode.datetime_for_slot(
        slot=withdrawal.slot,
        timezone=pytz.UTC
    )

    # Go over bond reductions in reverse order - most recent to least recent
    # If the withdrawal occurred after a given bond reduction, its value
    # will be split among the node and user based on the bond/fee at
    # that time
    for bond_reduction in sorted(bond_reductions,
                                 key=lambda x: x.timestamp, reverse=True):
        if withdrawal_dt > bond_reduction.timestamp:
            amount_no = _get_rocket_pool_reward_share_withdrawal_for_bond_fee(
                withdrawal=withdrawal,
                bond=bond_reduction.new_bond_amount,
                fee=bond_reduction.new_fee,
            )

            return RewardForDate(
                date=withdrawal_dt.date(),
                amount_wei=amount_no,
            )

    # The withdrawal occurred before any bond reductions
    # => apply minipool's initial bond & fee
    amount_no = _get_rocket_pool_reward_share_withdrawal_for_bond_fee(
        withdrawal=withdrawal,
        bond=initial_bond,
        fee=initial_fee
    )

    return RewardForDate(
        date=withdrawal_dt.date(),
        amount_wei=amount_no,
    )


async def get_rocket_pool_reward_share_proposal_fee_distributor(
    node_address: str,
    fee_distributor: str,
    slot: int,
    beacon_node: BeaconNode,
    rocket_pool_data: RocketPoolDataProvider,
) -> int:
    logger.info(f"Getting reward share for proposal in slot {slot}, FD {fee_distributor}...")

    # TODO pass block_number here directly once those are indexed
    #  and present in the block reward table
    block_number = (await beacon_node.get_slot_proposer_data(slot)).block_number

    try:
        node_share_before_proposal = await rocket_pool_data.get_node_fee_distributor_share(
            node_fee_distributor_address=fee_distributor,
            block_number=block_number-1,
        )
        node_share_after_proposal = await rocket_pool_data.get_node_fee_distributor_share(
            node_fee_distributor_address=fee_distributor,
            block_number=block_number,
        )
        # TODO check if units correct here
        return node_share_after_proposal - node_share_before_proposal
    except ValueError:
        # getNodeShare only available in post-Atlas distributor delegate...
        # We have to calculate the shares manually here
        avg_node_fee = await rocket_pool_data.get_node_average_fee(
            node_address=node_address,
            block_number=block_number,
        )
        # assume the collateralization ratio is half in this case
        # see e.g. https://github.com/rocket-pool/rocketpool/commit/f50109be11d68043446528c25c015a060475e6ca#diff-67701dbf2e859026c6c26c91b5e6e87f63a74de84093b0b98e08e92ade041cc5
        # "// Fallback for backwards compatibility before ETH matched was recorded (all minipools matched 16 ETH from protocol)"
        # "// All legacy minipools had a 1:1 ratio"
        # Verify if this value is ok (in terms of order of magnitude too)
        collateralization_ratio = 2 * Decimal(1e18)

        fee_distributor_balance_change = await rocket_pool_data.execution_node.get_balance(
            address=fee_distributor, block_number=block_number,
            use_infura=True) - await rocket_pool_data.execution_node.get_balance(
            address=fee_distributor, block_number=block_number - 1, use_infura=True)
        # Note - no need to adjust this balance change for withdrawal operations since all RP
        # withdrawal operations go to the minipool smart contracts
        node_balance_change = fee_distributor_balance_change * Decimal(1e18) / collateralization_ratio
        user_balance_change = fee_distributor_balance_change - node_balance_change
        node_share = node_balance_change + user_balance_change * avg_node_fee / Decimal(1e18)
        user_share = fee_distributor_balance_change - node_share

        # TODO check if units correct here
        # Round down like SafeMath does, which is used in RP smart contracts
        return floor(node_share)


async def _preprocess_request_input_data(rewards_request: RewardsRequest) -> tuple[
    list[int],
    datetime.datetime,
    datetime.datetime,
    int,
    int
]:
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
    end_datetime = datetime.datetime.combine(
        datetime.datetime(
            year=rewards_request.end_date.year,
            month=rewards_request.end_date.month,
            day=rewards_request.end_date.day,
            tzinfo=pytz.UTC,
        ),
        datetime.time(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
    )

    min_slot = BeaconNode.slot_for_datetime(start_datetime)
    max_slot = BeaconNode.slot_for_datetime(end_datetime)

    logger.info(f"Input data - validator indexes: {validator_indexes}")
    logger.info(f"Input data - date range: {start_datetime} ({min_slot}) - {end_datetime} ({max_slot})")

    return validator_indexes, start_datetime, end_datetime, min_slot, max_slot


@router.post(  # POST method to support bigger requests
    "/rewards/rocket_pool",
    response_model=RewardsResponseRocketPool,
)
async def rewards(
    rewards_request: RewardsRequest,
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    db_provider: DbProvider = Depends(depends_db),
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
) -> RewardsResponseRocketPool:
    (validator_indexes, start_datetime, end_datetime,
     min_slot, max_slot) = await _preprocess_request_input_data(rewards_request)

    # Get all withdrawals
    logger.debug(f"Getting withdrawals")
    all_withdrawals = sorted(db_provider.withdrawals(
        min_slot=min_slot,
        max_slot=max_slot,
        validator_indexes=validator_indexes
    ), key=lambda x: x.slot)

    # Get all block rewards
    logger.debug(f"Getting block rewards for ({min_slot} - {max_slot})")
    all_block_rewards = db_provider.block_rewards(
        min_slot=min_slot,
        max_slot=max_slot,
        proposer_indexes=validator_indexes
    )

    rocket_pool_minipools = db_provider.minipools_for_validators(validator_indexes=validator_indexes)

    if len(rocket_pool_minipools.keys()) != len(validator_indexes):
        mp_indexes = set(rocket_pool_minipools.keys())
        request_indexes = set(validator_indexes)
        unknown_validator_indexes = request_indexes.difference(mp_indexes)
        logger.warning(f"Unable to find RP minipools ({rocket_pool_minipools}) for all validators ({validator_indexes})!")
        raise HTTPException(status_code=400, detail=f"Unable to find RP minipools for all validators, missing {unknown_validator_indexes}!")

    rocket_pool_validator_indexes = [index for index, mp in
                                     rocket_pool_minipools.items()]
    rocket_pool_node_rewards = db_provider.rocket_pool_node_rewards_for_minipools(
        minipool_addresses=[mp.minipool_address for mp in
                            rocket_pool_minipools.values()],
        from_datetime=start_datetime,
        to_datetime=end_datetime,
    )
    rocket_pool_fee_distributors = db_provider.fee_distributor_addresses_for_validator_indexes(
        validator_indexes=rocket_pool_validator_indexes
    )
    rocket_pool_data = None
    if len(rocket_pool_validator_indexes) > 0:
        # we'll need Rocket Pool data
        rocket_pool_data = RocketPoolDataProvider(execution_node=ExecutionNode())

    validator_rewards_list = []
    for validator_index in sorted(validator_indexes):
        minipool_data = rocket_pool_minipools[validator_index]

        withdrawals_node_operator = []
        for withdrawal in [w for w in all_withdrawals if
                           w.validator_index == validator_index]:
            withdrawals_node_operator.append(
                get_rocket_pool_reward_share_withdrawal(
                    withdrawal=withdrawal,
                    bond_reductions=minipool_data.bond_reductions,
                    initial_bond=minipool_data.initial_bond_value,
                    initial_fee=minipool_data.initial_fee_value,
                )
            )

        # Sum in case multiple proposals happen on the same day
        exec_layer_rewards_node_operator_for_date = defaultdict(Decimal)
        # Only count block rewards if they didn't go to Rocket Pool's Smoothing Pool
        for br in [br for br in all_block_rewards if br.proposer_index == validator_index]:
            reward_recipient = br.mev_reward_recipient if br.mev else br.fee_recipient
            reward_recipient = reward_recipient.lower()

            if reward_recipient == SMOOTHING_POOL_ADDRESS:
                # This reward does not belong to the proposer only
                # It is accounted for in the 28-day smoothing pool rewards
                continue
            elif reward_recipient == rocket_pool_fee_distributors[
                validator_index]:
                # Get the balance delta of the fee distributor contract
                date = BeaconNode.datetime_for_slot(slot=br.slot, timezone=pytz.UTC).date()

                exec_layer_rewards_node_operator_for_date[date] += await get_rocket_pool_reward_share_proposal_fee_distributor(
                    node_address=minipool_data.node_address,
                    fee_distributor=rocket_pool_fee_distributors[validator_index],
                    slot=br.slot,
                    beacon_node=beacon_node,
                    rocket_pool_data=rocket_pool_data,
                )
            else:
                message = f"Block reward for slot {br.slot} "\
                          f"proposed by RP minipool ({minipool_data.minipool_address} / {validator_index})"\
                          f" did not go to smoothing pool ({SMOOTHING_POOL_ADDRESS}) "\
                          f"or fee distributor ({rocket_pool_fee_distributors[validator_index]}) "\
                          f"but {reward_recipient}!"
                logger.error(message)
                raise HTTPException(
                    status_code=500,
                    detail=message
                )

        execution_layer_rewards_node_operator = []
        for date, reward_amount in exec_layer_rewards_node_operator_for_date.items():
            execution_layer_rewards_node_operator.append(RewardForDate(
                date=date,
                amount_wei=reward_amount
            ))

        validator_rewards = RocketPoolValidatorRewards.construct(
            validator_index=validator_index,
            execution_layer_rewards=execution_layer_rewards_node_operator,
            withdrawals=withdrawals_node_operator,
        )
        validator_rewards_list.append(validator_rewards)

    return RewardsResponseRocketPool.construct(
        validator_rewards_list=validator_rewards_list,
        rocket_pool_node_rewards=[
            RocketPoolNodeRewardForDate(
                date=reward.reward_period.reward_period_end_time,
                node_address=reward.node_address,
                amount_wei=reward.reward_smoothing_pool_wei,
                amount_rpl=reward.reward_collateral_rpl,
            )
            for reward in rocket_pool_node_rewards
        ],
    )


@router.post(  # POST method to support bigger requests
    "/rewards/full",
    response_model=RewardsResponseFull,
)
async def rewards(
    rewards_request: RewardsRequest,
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    db_provider: DbProvider = Depends(depends_db),
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
) -> RewardsResponseFull:
    validator_indexes, start_datetime, end_datetime, min_slot, max_slot = await _preprocess_request_input_data(rewards_request)

    # Let's get the rewards
    first_slot_in_requested_period = min_slot
    try:
        activation_slots = await beacon_node.activation_slots_for_validators(validator_indexes=validator_indexes, cache=cache)
    except Exception:
        raise HTTPException(status_code=500,
                            detail=f"Failed to get activation slots for {', '.join(validator_indexes)}")
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
            initial_balance_maybe = db_provider.balances(
                slots=[act_slot],
                validator_indexes=[validator_index],
            )
            if len(initial_balance_maybe) == 1:
                initial_balance = initial_balance_maybe[0]
            else:
                raise HTTPException(status_code=500, detail=f"No initial balance found for {validator_index}")
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
    all_withdrawals = sorted(db_provider.withdrawals(
        min_slot=min_slot,
        max_slot=max_slot,
        validator_indexes=validator_indexes
    ), key=lambda x: x.slot)

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
            if eod_balance.slot < activation_slots[validator_index]:
                # End of day balance before validator was activated -> discard
                continue

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

    validator_rewards_list = []
    for validator_index in sorted(validator_indexes):
        if validator_index in pending_validator_indexes:
            continue

        validator_rewards_list.append(ValidatorRewards.construct(
            validator_index=validator_index,
            consensus_layer_rewards=consensus_layer_rewards[validator_index],
            execution_layer_rewards=execution_layer_rewards[validator_index],
            withdrawals=withdrawals[validator_index],
        ))

    return RewardsResponseFull.construct(validator_rewards_list=validator_rewards_list)
