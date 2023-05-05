from sqlalchemy import Column, Boolean, LargeBinary, Numeric, Integer, Float, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Balance(Base):
    __tablename__ = "balance"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True)
    balance = Column(Float, nullable=False)


class BlockReward(Base):
    __tablename__ = "block_reward"

    # A precision of 27 for the numeric type is enough to store the whole current supply of ETH, ~100M. Should be safe?

    slot = Column(Integer, nullable=False, primary_key=True, autoincrement=False)
    proposer_index = Column(Integer, nullable=True)
    fee_recipient = Column(String(length=42), nullable=True)
    priority_fees_wei = Column(Numeric(precision=27), nullable=True)
    block_extra_data = Column(LargeBinary)
    mev = Column(Boolean, nullable=True)
    mev_reward_recipient = Column(String(length=42), nullable=True)
    mev_reward_value_wei = Column(Numeric(precision=27), nullable=True)


class Withdrawal(Base):
    __tablename__ = "withdrawal"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True)
    amount_gwei = Column(Numeric(precision=18), nullable=True)

    # Relationships
    withdrawal_address_id = Column(ForeignKey("withdrawal_address.id"))
    withdrawal_address = relationship("WithdrawalAddress", back_populates="withdrawals")


class WithdrawalAddress(Base):
    __tablename__ = "withdrawal_address"

    id = Column(Integer, primary_key=True)
    address = Column(String(length=42), nullable=False)

    # Relationships
    withdrawals = relationship("Withdrawal", back_populates="withdrawal_address")
