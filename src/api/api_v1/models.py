from typing import Dict, List, Optional
import datetime

from pydantic import BaseModel, Field


class BalanceAtSlot(BaseModel):
    date: datetime.date = Field(..., example=datetime.date.fromisoformat("2020-01-31"))
    slot: int = Field(..., example=78391)
    balance: float = Field(..., example=32.42)


class EndOfDayBalance(BalanceAtSlot):
    pass


class ErrorMessage(BaseModel):
    message: str = Field(..., example="No data found for the provided input.")


class InitialBalance(BalanceAtSlot):
    pass


class ExecLayerBlockReward(BaseModel):
    date: datetime.date = Field(..., example=datetime.date.fromisoformat("2022-09-15"))
    reward: float = Field(..., example=0.013)
    slot: int = Field(..., example=78391)
    mev: bool = Field(..., example=False)

    def __str__(self):
        return f"ExecLayerBlockReward for {self.slot}"


class Withdrawal(BaseModel):
    date: datetime.date = Field(..., example=datetime.date.fromisoformat("2022-09-15"))
    amount: float = Field(..., example=0.013)

    class Config:
        orm_mode = True


class ValidatorRewards(BaseModel):
    validator_index: int = Field(..., example=1234)
    # This field is optional - if a validator has not been active in the requested
    # time period, it will be set to None
    initial_balance: Optional[InitialBalance]
    eod_balances: List[EndOfDayBalance]

    exec_layer_block_rewards: List[ExecLayerBlockReward]
    withdrawals: List[Withdrawal]

    total_consensus_layer_eth: float = Field(...,
                                             example=12.456,
                                             description="Total rewards from the consensus layer (attestations, block proposals, sync committees)")
    total_consensus_layer_currency: float = Field(...,
                                                  example=12.456,
                                                  description="Total rewards from the consensus layer (attestations, block proposals, sync committees) in the requested currency")
    total_execution_layer_eth: float = Field(...,
                                             example=12.456,
                                             description="Total rewards from the execution layer (transaction fees, MEV)")
    total_execution_layer_currency: float = Field(...,
                                                  example=12.456,
                                                  description="Total rewards from the execution layer (transaction fees, MEV) in the requested currency")


class AggregateRewards(BaseModel):
    validator_rewards: List[ValidatorRewards]
    currency: str = Field(..., example="EUR")
    eth_prices: Dict = Field(..., example={"2021-01-01": 502.4, "2021-01-02": 554.32})
