import pytest

from providers.execution_node import ExecutionNode
from providers.rocket_pool import RocketPoolDataProvider, _STORAGE_ROCKET_NODE_MANAGER_KEY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "minipool_address, block_number, expected_fee",
    [
        pytest.param(
            "0xb8D17ec656d5353d04d7f876e0ff6cC10F9d3B65",
            15899815,
            150000000000000000,
            id="Minipool created as 16ETH minipool with 15% fee",
        ),
        pytest.param(
            "0xb8D17ec656d5353d04d7f876e0ff6cC10F9d3B65",
            17075657,
            140000000000000000,
            id="Minipool created as 16ETH minipool with 15% fee, after bond reduction",
        ),
    ]
)
async def test_get_minipool_node_fee(minipool_address: str, block_number: int, expected_fee: int):
    rocket_pool_data = RocketPoolDataProvider(execution_node=ExecutionNode())
    fee = await rocket_pool_data.get_minipool_node_fee(
        minipool_address=minipool_address,
        block_number=block_number,
    )
    assert fee == expected_fee


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "minipool_address, block_number, expected_bond",
    [
        pytest.param(
            "0xb8D17ec656d5353d04d7f876e0ff6cC10F9d3B65",
            15899815,
            16 * 1e18,
            id="Minipool created as 16ETH minipool with 15% fee",
        ),
        pytest.param(
            "0xb8D17ec656d5353d04d7f876e0ff6cC10F9d3B65",
            17075657,
            8 * 1e18,
            id="Minipool created as 16ETH minipool with 15% fee, after bond reduction",
        ),
    ]
)
async def test_get_minipool_bond(minipool_address: str, block_number: int, expected_bond: int):
    rocket_pool_data = RocketPoolDataProvider(execution_node=ExecutionNode())
    bond = await rocket_pool_data.get_minipool_bond(
        minipool_address=minipool_address,
        block_number=block_number,
    )
    assert bond == expected_bond


@pytest.mark.asyncio
async def test_get_rocket_storage_value():
    rocket_pool_data = RocketPoolDataProvider(execution_node=ExecutionNode())
    assert await rocket_pool_data.get_rocket_storage_value(_STORAGE_ROCKET_NODE_MANAGER_KEY, block_number=15_300_000) == "0x4477fbf4af5b34e49662d9217681a763ddc0a322"
    assert await rocket_pool_data.get_rocket_storage_value(_STORAGE_ROCKET_NODE_MANAGER_KEY, block_number=15_500_000) == "0x67cde7af920682a29fcfea1a179ef0f30f48df3e"
    assert await rocket_pool_data.get_rocket_storage_value(_STORAGE_ROCKET_NODE_MANAGER_KEY, block_number=16_500_000) == "0x372236c940f572020c0c0eb1ac7212460e4e5a33"
