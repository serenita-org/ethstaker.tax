import pytest

from indexer.block_rewards.block_rewards_mev_simple import get_block_reward_value
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
            id="Flashbots builder",
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
                slot=4898292,
                proposer_index=237311,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15734167,
            ),
            21431599381708251,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            55911493587517345,
            id="BloXroute normal tx in middle of block",
        ),
        pytest.param(
            SlotProposerData(
                slot=5161642,
                proposer_index=310877,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15996004,
            ),
            45128158154852272,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            45128158154852272,
            id="Manifold - no fee recipient replacement",
        ),
        pytest.param(
            SlotProposerData(
                slot=5161324,
                proposer_index=168492,
                fee_recipient="0x221507c5cae31196a535f223c022eb0e38c3377d",
                block_number=15995686,
            ),
            16472709150448070,
            True,
            "0x221507c5cae31196a535f223c022eb0e38c3377d",
            16472709150448070,
            id="Blocknative - no fee recipient replacement",
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
            # https://ptb.discord.com/channels/694822223575384095/870681728862277662/1040357928475054142
            id="MEV Bot contract, example from builder0x69 in Discord, via Relayooor.wtf",
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
            marks=pytest.mark.xfail(reason="MEV value over manual inspection threshold"),
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
            # https://etherscan.io/tx/0x863548e6ae8838191c71bbbef39b3f42c692b9d7c381fa62e266ee3c43eb5761
            # https://etherscan.io/tx/0x6ad08ccd179a1fd02f2ae959bb68f7eb8349b36b6f8ee26c5c5f4a306360528f
            # Beaconcha.in shows Blocknative and Eden relay
            id="No extra data, MEV recipient = fee recipient, MEV transferred in 2 separate contract calls",
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
            id="1 regular tx in block, contains MEV payout",
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
            # https://etherscan.io/tx/0xba1d031197063ef0e7b5c2d77ee35d28e22c3cd4eb58c12fb0d6dea1de119371
            id="MevRefunder - MEV reward sent from different address."
               " Sending money to Tornado cash donation via Flashbots relay",
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
                slot=5058563,
                proposer_index=5058563,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15893491,
            ),
            17113653986482171,
            True,
            "0xdf50d17985f28c9396a2bc19c8784d838fac958f",
            35810297896739199,
            id="Kraken rewards distribution contract 1 called",
        ),
        pytest.param(
            SlotProposerData(
                slot=5113026,
                proposer_index=443188,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15947655,
            ),
            87799533387315766,
            True,
            "0xc9e30152fdb48b6535a1cd4cbbd78349b36afd21",
            86081731827337120,
            # Tx 0x8dc17b83ec0adee11f02a84a03a5783558ae70dbafe923e3b5228d447711d882
            id="Kraken rewards distribution contract 2 called",
        ),
        pytest.param(
            SlotProposerData(
                slot=5035922,
                proposer_index=26993,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15871004,
            ),
            151503275950244782,
            True,
            "0x036d539e2f1ba71ef2e8dec66ca0ffeae9e15f17",
            150625172981951218,
            # https://etherscan.io/tx/0xe0fca403951b3604cafcd0adf799ac7ec5bae493adf944b8a12a114f95a7674b
            id="Kraken rewards distribution contract 3 called",
        ),
        pytest.param(
            SlotProposerData(
                slot=5108972,
                proposer_index=265497,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15943629,
            ),
            24456361394331056,
            True,
            "0xbd28c94ff48f9c9c1abbf2691b1c5523c5c7a7a8",
            23367384745318778,
            id="Kraken contract 4",
        ),
        pytest.param(
            SlotProposerData(
                slot=4867314,
                proposer_index=371162,
                fee_recipient="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
                block_number=15703347,
            ),
            117646288386850207,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            0,
            id="huge but FAKE reward via Eden",
        ),
        pytest.param(
            SlotProposerData(
                slot=4882764,
                proposer_index=337362,
                fee_recipient="0xa45ae232688be5b472c1d3fc83d55c63c7aa80e3",
                block_number=15718719,
            ),
            66959833957515037,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            0,
            id="MEV transfer tx ran out of gas",
        ),
        pytest.param(
            SlotProposerData(
                slot=4882802,
                proposer_index=253184,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15718756,
            ),
            91103796007739987,
            True,
            "0x6b9c23e50d6d5c2854cff4d305f279ad4007ec1e",
            89323651150811628,
            id="Kraken contract 5",
        ),
        pytest.param(
            SlotProposerData(
                slot=4899125,
                proposer_index=332660,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15734999,
            ),
            54365676887932534,
            True,
            "0xdfa1119cbfd974810276d88ae3e5c2ff360b85e0",
            53586236646342550,
            id="Kraken contract 6",
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
            # https://etherscan.io/tx/0x0b1a86b1160dc260b7db6e123b7d965f0c8d73946349b90c32479c014192ac07
            id="Otherdeed NFT buyer contract. Supports Opensea/Seaport/Looksrare/X2Y2 exchanges."
               " Exchange to use is determined by function name, e.g. 0xc7c5454e=X2Y2."
               " The buyer contract pays the fee recipient directly, presumably for including the tx.",
        ),
        pytest.param(
            SlotProposerData(
                slot=4884504,
                proposer_index=291026,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15720449,
            ),
            32602383294203787,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            122602383294203787,
            # https://etherscan.io/tx/0x0b1a86b1160dc260b7db6e123b7d965f0c8d73946349b90c32479c014192ac07
            id="Otherdeed NFT buyer contract example 2. No other MEV bot contracts called in this block",
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
            # https://etherscan.io/tx/0x68865e4e3b0c1afc1539daf7c02a57f0ca55da777198ed6489f0072c40a54be3
            id="Stakefish fee recipient contract, receives a regular transaction",
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
        pytest.param(
            SlotProposerData(
                slot=4700435,
                proposer_index=257475,
                fee_recipient="0x4675c7e5baafbffbca748158becba61ef3b0a263",
                block_number=15537812,
            ),
            105098414472062089,
            False,
            None,
            None,
            id="Fee recipient makes a regular tx",
        ),
        pytest.param(
            SlotProposerData(
                slot=4700826,
                proposer_index=211774,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15538196,
            ),
            42537399459467107,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            42620933959467107,
            id="Lido ETHReceived event - exec layer rewards sent as regular ETH transfer",
        ),
        pytest.param(
            SlotProposerData(
                slot=4702530,
                proposer_index=255156,
                fee_recipient="0x7d00a2bc1370b9005eb100004da500924600a2e1",
                block_number=15539878,
            ),
            116531199186242605,
            True,
            "0x7d00a2bc1370b9005eb100004da500924600a2e1",
            14566399898280327,
            id="a2e1 contract recipient and MEV bot contract called in block, example 1"
        ),
        pytest.param(
            SlotProposerData(
                slot=4722223,
                proposer_index=255643,
                fee_recipient="0x7d00a2bc1370b9005eb100004da500924600a2e1",
                block_number=15559326,
            ),
            19530228111440101,
            True,
            "0x7d00a2bc1370b9005eb100004da500924600a2e1",
            2441278513930014,
            id="a2e1 contract recipient and MEV bot contract called in block, example 2",
        ),
        pytest.param(
            SlotProposerData(
                slot=4723237,
                proposer_index=255571,
                fee_recipient="0x7d00a2bc1370b9005eb100004da500924600a2e1",
                block_number=15560330,
            ),
            28503513692536312,
            True,
            "0x7d00a2bc1370b9005eb100004da500924600a2e1",
            3562939211567039,
            # This case is the reason why we still need the separate a2e1 condition...
            id="a2e1 contract recipient and no (known?) MEV bot contract called in block",
        ),
        pytest.param(
            SlotProposerData(
                slot=4704746,
                proposer_index=74950,
                fee_recipient="0xe688b84b23f322a994a53dbf8e15fa82cdb71127",
                block_number=15542062,
            ),
            79917019598960152,
            True,
            "0xe688b84b23f322a994a53dbf8e15fa82cdb71127",
            101917019598960152,
            # https://etherscan.io/tx/0xddf2258c0a696f9685b03bbe5ab4579874b63750a64286193366782a6e229228
            id="MEV Bot contract",
        ),
        pytest.param(
            SlotProposerData(
                slot=4801543,
                proposer_index=7346,
                fee_recipient="0xf107a9b3a91d0fe0e063e37e4dd3f6fd2dc3bdc6",
                block_number=15638012,
            ),
            68520736002508191,
            True,
            "0xf107a9b3a91d0fe0e063e37e4dd3f6fd2dc3bdc6",
            68620736002508191,
            # https://etherscan.io/tx/0x1064c04859c016f2febc2c70e9067d90f65366db568937088ff0cba5e144dac5
            id="MEV Bot contract - swapping USDC for Ether, transferred directly",
        ),
        pytest.param(
            SlotProposerData(
                slot=4799855,
                proposer_index=94564,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15636332,
            ),
            35180387516127932,
            True,
            "0x0b3b161b8abeb6b04cb95c3e6047f80c120a0292",
            34959073261693932,
            # https://etherscan.io/tx/0x1064c04859c016f2febc2c70e9067d90f65366db568937088ff0cba5e144dac5
            id="MEV Bot contract - swapping USDC for Ether, transferred in last tx",
        ),
        pytest.param(
            SlotProposerData(
                slot=5173346,
                proposer_index=73475,
                fee_recipient="0xde139fb131edba4bc468422158589070239a0efd",
                block_number=16007650,
            ),
            47084614301770735,
            True,
            "0xde139fb131edba4bc468422158589070239a0efd",
            51084614301770735,
            id="MEV Bot contract",
        ),
        pytest.param(
            SlotProposerData(
                slot=5233220,
                proposer_index=443166,
                fee_recipient="0xfeebabe6b0418ec13b30aadf129f5dcdd4f70cea",
                block_number=16067171,
            ),
            119237863664011794,
            True,
            "0x7cd1af7d5299c5bfd4a63291eb5aa57f0ce60024",
            12385111686554897,
            id="contract that forwards rewards to Kraken?",
            marks=pytest.mark.xfail(reason="not handled right now"),
        ),
        pytest.param(
            SlotProposerData(
                slot=5362004,
                proposer_index=442302,
                fee_recipient="0x0000000000000000000000000000000000000000",
                block_number=16195134,
            ),
            36417235491435301,
            False,
            None,
            None,
            id="fee recipient null address 0x00..00 while someone also sent something to the burn address",
            marks=pytest.mark.xfail(reason="fee recipient null address 0x00..00 while someone also sent something to the burn address"),
        ),
        pytest.param(
            SlotProposerData(
                slot=5442676,
                proposer_index=469716,
                fee_recipient="0x00000000219ab540356cbb839cbe05303d7705fa",
                block_number=16275423,
            ),
            36417235491435301,
            False,
            None,
            None,
            id="fee recipient is beacon deposit contract, during same block a deposit was made",
            marks=pytest.mark.xfail(reason="not handled yet"),
        ),
        pytest.param(
            SlotProposerData(
                slot=5573539,
                proposer_index=20707,
                fee_recipient="0xbaf6dc2e647aeb6f510f9e318856a1bcd66c5e19",
                block_number=16405641,
            ),
            36417235491435301,
            True,
            "0xffee087852cb4898e6c3532e776e68bc68b1143b",
            42,
            id="fee recipient is beacon deposit contract, during same block a deposit was made",
            marks=pytest.mark.xfail(reason="not handled yet"),
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_block_reward_value(
        slot_proposer_data, expected_priority_tx_fees, expected_contains_mev, expected_mev_reward_recipient, expected_mev_reward,
        execution_node
):
    block_reward_value = await get_block_reward_value(
        slot_proposer_data=slot_proposer_data,
        execution_node=execution_node,
    )
    assert block_reward_value.block_priority_tx_fees == expected_priority_tx_fees
    assert block_reward_value.contains_mev == expected_contains_mev
    assert block_reward_value.mev_recipient == expected_mev_reward_recipient
    assert block_reward_value.mev_recipient_balance_change == expected_mev_reward
