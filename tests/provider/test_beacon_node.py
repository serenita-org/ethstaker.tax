import pytest

from providers.beacon_node import BeaconNode


@pytest.mark.asyncio
@pytest.mark.skip
async def test_get_slot_proposer_data():
    beacon_node = BeaconNode()
    data = await beacon_node.get_slot_proposer_data(6190092)
    assert data.block_hash == "0x28619501c85af72ad865970de6fc044d9e248e7aaf2c2cea2a2081fa2e8fb107"
