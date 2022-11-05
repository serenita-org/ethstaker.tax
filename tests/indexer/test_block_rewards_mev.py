import pytest

from indexer.block_rewards_mev import get_block_reward_value, MEV_BUILDERS, MevPayoutType
from providers.beacon_node import BlockRewardData


@pytest.mark.parametrize(
    "slot,block_reward_data,builder_name,expected_proposer_reward,expected_contains_mev",
    [
        pytest.param(
            4700013,
            BlockRewardData(
                proposer_index=347963,
                fee_recipient="0xeee27662c2b8eba3cd936a23f039f3189633e4c8",
                block_number=15537394,
            ),
            None,
            45031378244766393234,
            False,
            id="First PoS block, no MEV, but high value transactions",
        ),
        pytest.param(
            5000001,
            BlockRewardData(
                proposer_index=5639,
                fee_recipient="0x9780713736db73d09b7fecba15c25679f55bd13e",
                block_number=15835293,
            ),
            None,
            1206869874028342,
            False,
            id="Random PoS block, no MEV, low value transactions",
        ),
        pytest.param(
            5000000,
            BlockRewardData(
                proposer_index=347963,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15835292,
            ),
            "Flashbots builder",
            28854222256963892,
            True,
            id="Flashbots",
        ),
        pytest.param(
            5000007,
            BlockRewardData(
                proposer_index=451800,
                fee_recipient="0xf573d99385c05c23b24ed33de616ad16a43a0919",
                block_number=15835299,
            ),
            "bloxroute ethical builder",
            39059287790086385,
            True,
            id="BloXroute ethical",
        ),
        pytest.param(
            5063206,
            BlockRewardData(
                proposer_index=7230,
                fee_recipient="0x5be9b269a83018e3192d6139dc6431de5656ea8a",
                block_number=15898112,
            ),
            "Manifold",
            93942016060897429,
            True,
            id="Manifold",
        ),
        pytest.param(
            5062861,
            BlockRewardData(
                proposer_index=10225,
                fee_recipient="0x43afeaa23a4f201a8a888b4d3d054876a085e593",
                block_number=15897767,
            ),
            "Viva relayooor.wtf",
            140692479934170844,
            True,
            id="Relayooor.wtf - reward combination",
        ),

    ],
)
@pytest.mark.asyncio
async def test_get_block_reward_value(slot, block_reward_data, builder_name, expected_proposer_reward, expected_contains_mev):
    if builder_name is not None:
        builder = next(b for b in MEV_BUILDERS if b.name == builder_name)
        if builder.payout_type == MevPayoutType.LAST_TX:
            assert block_reward_data.fee_recipient == builder.fee_recipient_address
    proposer_reward, contains_mev = await get_block_reward_value(block_reward_data=block_reward_data)
    assert proposer_reward == expected_proposer_reward
    assert contains_mev == expected_contains_mev
