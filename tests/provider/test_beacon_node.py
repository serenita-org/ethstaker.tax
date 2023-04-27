import pytest

from providers.beacon_node import BeaconNode


@pytest.mark.asyncio
@pytest.mark.skip
async def test_get_slot_proposer_data():
    beacon_node = BeaconNode()
    data = await beacon_node.get_slot_proposer_data(6190092)
    assert data.block_hash == "0x28619501c85af72ad865970de6fc044d9e248e7aaf2c2cea2a2081fa2e8fb107"


@pytest.mark.parametrize(
    "slot,exp_withdrawal_count,exp_max_amount,exp_min_amount,",
    [
        pytest.param(
            6_209_535,
            16,
            1_627_879_029,
            11_038_767,
            id="Pre-Shapella",
            marks=pytest.mark.xfail(reason="Pre-Shapella - missing key in API response",
                                    raises=KeyError),
        ),
        pytest.param(
            6_209_536,
            0,
            None,
            None,
            id="First post-Shapella slot - missed",
        ),
        pytest.param(
            6_209_538,
            0,
            None,
            None,
            id="First post-Shapella slot - no withdrawals",
        ),
        pytest.param(
            6_209_540,
            3,
            4_547_643_423,
            4_440_880_509,
            id="First post-Shapella slot including withdrawals",
        ),
        pytest.param(
            6_242_674,
            16,
            1_627_879_029,
            11_038_767,
            id="Random slot with withdrawals",
        ),
    ]
)
@pytest.mark.asyncio
async def test_get_withdrawals(slot: int, exp_withdrawal_count: int, exp_max_amount: int, exp_min_amount: int):
    beacon_node = BeaconNode()
    withdrawals = await beacon_node.withdrawals_for_slot(slot)
    assert len(withdrawals) == exp_withdrawal_count
    if len(withdrawals) > 0:
        assert max(w.amount_gwei for w in withdrawals) == exp_max_amount
        assert min(w.amount_gwei for w in withdrawals) == exp_min_amount
