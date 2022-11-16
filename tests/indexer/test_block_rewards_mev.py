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
        pytest.param(
            SlotProposerData(
                slot=5140097,
                proposer_index=237786,
                fee_recipient="0xae08c571e771f360c35f5715e36407ecc89d91ed",
                block_number=15974598,
            ),
            154817970642327532,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            147746526377856659,
            id="Builder extra data matched using regex",
        ),
        pytest.param(
            SlotProposerData(
                slot=4892252,
                proposer_index=280071,
                fee_recipient="0x8d5998a27b3cdf33479b65b18f075e20a7aa05b9",
                block_number=15728162,
            ),
            137730979190821160,
            True,
            "0xe688b84b23f322a994a53dbf8e15fa82cdb71127",
            137300162630179160,
            id="Builder extra data matched using regex - geth",
        ),
        pytest.param(
            SlotProposerData(
                slot=4810472,
                proposer_index=266974,
                fee_recipient="0xd4e96ef8eee8678dbff4d535e033ed1a4f7605b7",
                block_number=15646882,
            ),
            41999182696740266,
            True,
            "0xd4e96ef8eee8678dbff4d535e033ed1a4f7605b7",
            557605958391302970,
            id="No extra data, MEV recipient = fee recipient, MEV transferred via contract",
        ),
        pytest.param(
            SlotProposerData(
                slot=4895347,
                proposer_index=266974,
                fee_recipient="0xdefe33795803f2353c69fd8cdb432f9d5cee6762",
                block_number=15731242,
            ),
            600611770605000,
            True,
            "0xdefe33795803f2353c69fd8cdb432f9d5cee6762",
            42600611770605000,
            id="No extra data, MEV recipient = fee recipient, MEV transferred via contract",
        ),
        pytest.param(
            SlotProposerData(
                slot=4876774,
                proposer_index=69348,
                fee_recipient="0x8589427373d6d84e98730d7795d8f6f8731fda16",
                block_number=15712761,
            ),
            30727956763046266,
            True,
            "0xa79ac574245e21e69c46bc25581b482148fb79b6",
            40000000000000000,
            id="Sending money to Tornado cash donation via Flashbots relay",
        ),
        pytest.param(
            SlotProposerData(
                slot=4735659,
                proposer_index=62682,
                fee_recipient="0x54cd0e6771b6487c721ec620c4de1240d3b07696",
                block_number=15572628,
            ),
            201932030839597779,
            False,
            None,
            None,
            # Tx 0x4253bb749162e024ad53ab86a3f5e6f199b185ebf1b52dc908807e3cab2361d8
            id="Stakefish rewards distribution contract called",
        ),
        pytest.param(
            SlotProposerData(
                slot=4951292,
                proposer_index=322201,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15786872,
            ),
            102648185105740891,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            115648185105740891,
            # Tx 0x0b1a86b1160dc260b7db6e123b7d965f0c8d73946349b90c32479c014192ac07
            id="Fee recipient balance change > priority fees because of internal tx - fallback assume MEV",
        ),
        pytest.param(
            SlotProposerData(
                slot=4745381,
                proposer_index=69177,
                fee_recipient="0x54cd0e6771b6487c721ec620c4de1240d3b07696",
                block_number=15582188,
            ),
            83219714028892180,
            True,
            "0x54cd0e6771b6487c721ec620c4de1240d3b07696",
            83219714028902180,
            id="Stakefish rewards distribution + ?",
        ),
        pytest.param(
            SlotProposerData(
                slot=4719366,
                proposer_index=395742,
                fee_recipient="0x34f4261360d0372176d1d521bf99bf803ced4f6b",
                block_number=15556494,
            ),
            7799444800208322,
            False,
            None,
            None,
            # tx 0x67ff466b8a7ba064e241d1f8243159f55f017cad39f018072f97ce3499c0d585
            id="rocketpool deposit in rocketpool proposer block",
        ),
        pytest.param(
            SlotProposerData(
                slot=4917736,
                proposer_index=146676,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15753511,
            ),
            41112354986993524,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            41112354986993524,
            id="Manifold huge reward bug (not real)",
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
