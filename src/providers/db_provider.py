import logging
from typing import Any, Iterable, List
from contextlib import contextmanager

import starlette.requests
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from db.tables import Balance, BlockReward, Withdrawal
from db.db_helpers import _get_db_uri
from prometheus_client.metrics import Histogram

DB_REQUESTS_SECONDS = Histogram("db_requests_seconds",
                                "Time it takes to pull data from the database",
                                buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30,
                                         60, 120, 180, 300, float("inf")])

logger = logging.getLogger(__name__)


@contextmanager
def session_scope(engine: Engine) -> Session:
    """Provide a transactional scope around a series of operations."""
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DbProvider:
    async def __call__(self) -> Any:
        return self

    async def init_app(self, app: FastAPI) -> None:
        self.engine = create_engine(_get_db_uri(), pool_pre_ping=True)

        app.state.DB_PROVIDER = self

    def __init__(self) -> None:
        self.engine = create_engine(_get_db_uri(), pool_pre_ping=True)

    @DB_REQUESTS_SECONDS.time()
    def balances(self,
                 slots: Iterable[int],
                 validator_indexes: Iterable[int],
                 ) -> List[Balance]:

        with session_scope(self.engine) as session:
            balances = session\
                .query(Balance) \
                .filter(Balance.slot.in_(slots))\
                .filter(Balance.validator_index.in_(validator_indexes))\
                .all()
            session.expunge_all()

        return balances

    @DB_REQUESTS_SECONDS.time()
    def block_rewards(self, min_slot: int, max_slot: int, proposer_indexes: Iterable[int], limit: int | None = None) -> List[BlockReward]:
        with session_scope(self.engine) as session:
            query = session\
                .query(BlockReward) \
                .filter(BlockReward.slot.between(min_slot, max_slot))\
                .order_by(BlockReward.slot.desc())\
                .limit(limit)

            if proposer_indexes:
                query = query.filter(BlockReward.proposer_index.in_(proposer_indexes))

            block_rewards = query.all()
            session.expunge_all()

        return block_rewards

    @DB_REQUESTS_SECONDS.time()
    def withdrawals_to_address(self, address: str) -> List[Withdrawal]:
        with session_scope(self.engine) as session:
            withdrawals = session.query(Withdrawal).filter(Withdrawal.withdrawal_address.has(address=address)).all()
            session.expunge_all()
        return withdrawals

    @DB_REQUESTS_SECONDS.time()
    def withdrawals(self, min_slot: int, max_slot: int, validator_indexes: Iterable[int]) -> List[Withdrawal]:
        with session_scope(self.engine) as session:
            withdrawals = session\
                .query(Withdrawal) \
                .filter(Withdrawal.slot.between(min_slot, max_slot))\
                .filter(Withdrawal.validator_index.in_(validator_indexes))\
                .all()
            session.expunge_all()

        return withdrawals


db_plugin = DbProvider()


async def depends_db(request: starlette.requests.Request) -> DbProvider:
    return await request.app.state.DB_PROVIDER()
