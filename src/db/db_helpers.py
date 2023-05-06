import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session, sessionmaker

_ENGINE = None


def _get_db_uri():
    db_uri = os.getenv("DB_URI")
    if db_uri is None or db_uri == "":
        raise ValueError("DB_URI is not defined")
    return db_uri


def _get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(_get_db_uri(), pool_pre_ping=True)
    return _ENGINE


def get_session(engine: Engine) -> Session:
    """
    Creates a new session connected to the database defined in the
    provided engine argument.

    Args:
         engine: A SQLAlchemy engine object, created by using
            the sqlalchemy.create_engine function.

    Returns:
          A SQLAlchemy Session object bound to the provided engine.
    """
    s = sessionmaker(bind=engine)
    return s()


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = get_session(_get_engine())

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
