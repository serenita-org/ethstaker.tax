import pytest

from providers.execution_node import ExecutionNode


@pytest.fixture
def execution_node() -> ExecutionNode:
    yield ExecutionNode()
