import pytest

from providers.db_provider import DbProvider
from providers.execution_node import ExecutionNode


@pytest.fixture
def execution_node() -> ExecutionNode:
    yield ExecutionNode()


@pytest.fixture
def db_provider() -> DbProvider:
    yield DbProvider()
