from sqlalchemy import Column, Boolean, LargeBinary, Numeric, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Balance(Base):
    __tablename__ = "balance"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True)
    balance = Column(Float, nullable=False)


class BlockReward(Base):
    __tablename__ = "block_reward"

    slot = Column(Integer, nullable=False, primary_key=True, autoincrement=False)
    proposer_index = Column(Integer, nullable=True)
    fee_recipient = Column(String(length=42), nullable=True)
    block_extra_data = Column(LargeBinary)
    # A precision of 27 is enough to store the whole current supply of ETH, ~100M. Should be safe?
    proposer_reward = Column(Numeric(precision=27, scale=0), nullable=True)
    mev = Column(Boolean, nullable=True)
