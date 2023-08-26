import datetime

from pydantic import BaseModel


class RewardsRequest(BaseModel):
    validator_indexes: list[int]
    start_date: datetime.date
    end_date: datetime.date


class RewardForDate(BaseModel):
    date: datetime.date
    amount_wei: int


class RewardsResponse(BaseModel):
    validator_index: int

    consensus_layer_rewards: list[RewardForDate]
    execution_layer_rewards: list[RewardForDate]

    withdrawals: list[RewardForDate]
