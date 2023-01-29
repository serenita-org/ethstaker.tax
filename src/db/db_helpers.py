import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def get_db_uri():
    db_uri = os.getenv("DB_URI")
    if db_uri is None or db_uri == "":
        raise ValueError("DB_URI is not defined")
    return db_uri


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    engine = create_engine(get_db_uri())
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
