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
                slot=5105080,
                proposer_index=8660,
                fee_recipient="0x8faf1050379e5026cfddc59b24b0b78daef7c255",
                block_number=15939759,
            ),
            863081035702331217,
            True,
            "0x8faf1050379e5026cfddc59b24b0b78daef7c255",
            1302651208866927813,
            id="Example from builder0x69 in Discord, via Relayooor.wtf",
            # https://ptb.discord.com/channels/694822223575384095/870681728862277662/1040357928475054142
        ),
        pytest.param(
            SlotProposerData(
                slot=4747786,
                proposer_index=149800,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15584566,
            ),
            72741750891599650,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            293457340971917571,
            id="Non-standard MEV payout in 3 separate transactions in the middle of a block",
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
