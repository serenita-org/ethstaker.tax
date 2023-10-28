import datetime

from pydantic import BaseModel


class RewardsRequest(BaseModel):
    validator_indexes: list[int]
    start_date: datetime.date
    end_date: datetime.date


class PriceForDate(BaseModel):
    date: datetime.date
    price: float


class PricesResponse(BaseModel):
    currency: str
    prices: list[PriceForDate]


class RewardForDate(BaseModel):
    date: datetime.date
    amount_wei: int


class RocketPoolRewardForDate(RewardForDate):
    node_address: str
    amount_rpl: int


class ValidatorRewards(BaseModel):
    validator_index: int

    consensus_layer_rewards: list[RewardForDate]
    execution_layer_rewards: list[RewardForDate]

    withdrawals: list[RewardForDate]


class RocketPoolValidatorRewards(ValidatorRewards):
    fee: int
    bond_reduced: bool


class RewardsResponse(BaseModel):
    validator_rewards: list[ValidatorRewards | RocketPoolValidatorRewards]
    rocket_pool_rewards: list[RocketPoolRewardForDate]
