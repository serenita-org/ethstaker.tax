import pytest

from indexer.block_rewards_mev import get_block_reward_value
from providers.beacon_node import SlotProposerData


@pytest.mark.parametrize(
    "slot_proposer_data,"
    "expected_priority_tx_fees,expected_contains_mev,expected_mev_reward_recipient,expected_mev_reward",
    [
        pytest.param(
            SlotProposerData(
                slot=4700013,
                proposer_index=347963,
                fee_recipient="0xeee27662c2b8eba3cd936a23f039f3189633e4c8",
                block_number=15537394,
            ),
            45031378244766393234,
            False,
            None,
            None,
            id="First PoS block, no MEV, but high value transactions",
        ),
        pytest.param(
            SlotProposerData(
                slot=5000001,
                proposer_index=5639,
                fee_recipient="0x9780713736db73d09b7fecba15c25679f55bd13e",
                block_number=15835293,
            ),
            1206869874028342,
            False,
            None,
            None,
            id="Random PoS block, no MEV, low value transactions",
        ),
        pytest.param(
            SlotProposerData(
                slot=5000000,
                proposer_index=347963,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15835292,
            ),
            29142324295936892,
            True,
            "0xe688b84b23f322a994a53dbf8e15fa82cdb71127",
            28854222256963892,
            id="Flashbots",
        ),
        pytest.param(
            SlotProposerData(
                slot=5000007,
                proposer_index=451800,
                fee_recipient="0xf573d99385c05c23b24ed33de616ad16a43a0919",
                block_number=15835299,
            ),
            39398734994266385,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            39059287790086385,
            id="BloXroute ethical",
        ),
        pytest.param(
            SlotProposerData(
                slot=4705463,
                proposer_index=291537,
                fee_recipient="0x6b333b20fbae3c5c0969dd02176e30802e2fbbdb",
                block_number=15542760,
            ),
            231472088438174089,
            True,
            "0x6b333b20fbae3c5c0969dd02176e30802e2fbbdb",
            243579569124789055,
            id="bloXroute external builder",
        ),
        pytest.param(
            SlotProposerData(
                slot=4705459,
                proposer_index=18899,
                fee_recipient="0x0038598ecb3b308ebc6c6e2c635bacaa3c5298a3",
                block_number=15542756,
            ),
            120293380470556287,
            True,
            "0x0038598ecb3b308ebc6c6e2c635bacaa3c5298a3",
            120293380470556287,
            id="98a3 with MEV",
        ),
        pytest.param(
            SlotProposerData(
                slot=4702298,
                proposer_index=22557,
                fee_recipient="0x0038598ecb3b308ebc6c6e2c635bacaa3c5298a3",
                block_number=15539648,
            ),
            37456424946802627,
            False,
            None,
            None,
            id="98a3 without MEV",
        ),
        pytest.param(
            SlotProposerData(
                slot=5063206,
                proposer_index=7230,
                fee_recipient="0x5be9b269a83018e3192d6139dc6431de5656ea8a",
                block_number=15898112,
            ),
            93942016060897429,
            True,
            "0x5be9b269a83018e3192d6139dc6431de5656ea8a",
            93942016060897429,
            id="Manifold",
        ),
        pytest.param(
            SlotProposerData(
                slot=4727100,
                proposer_index=420884,
                fee_recipient="0xb646d87963da1fb9d192ddba775f24f33e857128",
                block_number=15564152,
            ),
            31517716262808181,
            True,
            "0xffd22b84fb1d46ef74ed6530b2635be61340f347",
            31184310984882181,
            id="extra data containing gethgo",
        ),
        pytest.param(
            SlotProposerData(
                slot=4732957,
                proposer_index=187321,
                fee_recipient="0x4675c7e5baafbffbca748158becba61ef3b0a263",
                block_number=15569949,
            ),
            17768060523787522,
            False,
            None,
            None,
            id="no MEV, fee recipient made a tx during block",
        ),
        pytest.param(
            SlotProposerData(
                slot=5062861,
                proposer_index=10225,
                fee_recipient="0x43afeaa23a4f201a8a888b4d3d054876a085e593",
                block_number=15897767,
            ),
            140057406631590583,
            True,
            "0x43afeaa23a4f201a8a888b4d3d054876a085e593",
            140692479934170844,
            id="Relayooor.wtf - reward combination",
        ),
        pytest.param(
            SlotProposerData(
                slot=4725102,
                proposer_index=4725102,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15562178,
            ),
            32525554942338742,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            37757395860474785,
            id="MEV Bot contract - reward sent in internal tx",
        ),
        pytest.param(
            SlotProposerData(
                slot=4723311,
                proposer_index=368535,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15560403,
            ),
            22617275274652751,
            False,
            None,
            None,
            id="Lido proposer and Lido rewards distribution in same block without MEV,"
               " with other balance changes on stETH token",
        ),
        pytest.param(
            SlotProposerData(
                slot=4716096,
                proposer_index=368535,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15553257,
            ),
            22617275274652751,
            False,
            None,
            None,
            id="Lido proposer and Lido rewards distribution in same block without MEV",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_block_reward_value(slot_proposer_data, expected_priority_tx_fees, expected_contains_mev, expected_mev_reward_recipient, expected_mev_reward):
    priority_tx_fees, contains_mev, mev_reward_recipient, mev_reward_value = await get_block_reward_value(slot_proposer_data=slot_proposer_data)
    assert priority_tx_fees == expected_priority_tx_fees
    assert contains_mev == expected_contains_mev
    assert mev_reward_recipient == expected_mev_reward_recipient
    assert mev_reward_value == expected_mev_reward
