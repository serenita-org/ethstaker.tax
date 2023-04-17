import os

import pytest
from sqlalchemy.engine import create_engine

from db.tables import Base


@pytest.fixture(scope="session", autouse=True)
def _init_db() -> None:
    """
    Initialize the necessary DB structure as defined in src/db/tables.py .
    """
    engine = create_engine(os.getenv("DB_URI"))
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    yield
    engine = create_engine(os.getenv("DB_URI"))
    Base.metadata.drop_all(bind=engine)
