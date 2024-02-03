import datetime

from pydantic import BaseModel


class RewardsRequest(BaseModel):
    validator_indexes: list[int]
    start_date: datetime.date
    end_date: datetime.date
    expected_withdrawal_addresses: list[str] = []


class PriceForDate(BaseModel):
    date: datetime.date
    price: float


class PricesResponse(BaseModel):
    currency: str
    prices: list[PriceForDate]


class RewardForDate(BaseModel):
    date: datetime.date
    amount_wei: int


class RocketPoolNodeRewardForDate(RewardForDate):
    node_address: str
    amount_rpl: int


class ValidatorRewardsBase(BaseModel):
    validator_index: int

    consensus_layer_rewards: list[RewardForDate] | None
    execution_layer_rewards: list[RewardForDate]

    withdrawals: list[RewardForDate]


class ValidatorRewards(ValidatorRewardsBase):
    consensus_layer_rewards: list[RewardForDate]


class RocketPoolValidatorRewards(ValidatorRewardsBase):
    # Returns None for Rocket Pool validators - no way to determine the exact CL
    # income at any point in time (and therefore every 24h at midnight UTC)
    consensus_layer_rewards: None = None


class RewardsResponseRocketPool(BaseModel):
    validator_rewards_list: list[RocketPoolValidatorRewards]
    rocket_pool_node_rewards: list[RocketPoolNodeRewardForDate]


class RewardsResponseFull(BaseModel):
    validator_rewards_list: list[ValidatorRewards]
