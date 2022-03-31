from sqlalchemy import Column, Integer, Float
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Balance(Base):
    __tablename__ = "balance"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True)
    balance = Column(Float, nullable=False)
