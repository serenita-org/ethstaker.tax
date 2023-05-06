import pytest

from indexer.block_rewards.block_rewards_mev_simple import get_block_reward_value, ManualInspectionRequired
from providers.beacon_node import SlotProposerData
from db.db_helpers import session_scope
from db.tables import Withdrawal, WithdrawalAddress


@pytest.fixture(scope="session")
def _withdrawals_in_db():
    # Withdrawals in the DB to make the block reward calculation correct for the
    # test case for slot 6351700 - the validator receives withdrawals during a block
    # they propose.
    with session_scope() as session:
        w_addr = WithdrawalAddress(
            address="0xde12c3d2257fc9bb1c1a00d409f292eecd55ffaf",
        )
        session.add(w_addr)
        session.commit()

        for obj in (
            Withdrawal(
                slot=6351700,
                validator_index=560492,
                amount_gwei=12349752,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560493,
                amount_gwei=12399308,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560494,
                amount_gwei=12440436,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560495,
                amount_gwei=12430291,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560496,
                amount_gwei=45765335,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560497,
                amount_gwei=12429872,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560498,
                amount_gwei=12402116,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560499,
                amount_gwei=12430277,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560500,
                amount_gwei=12401852,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560501,
                amount_gwei=12430194,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560502,
                amount_gwei=12407985,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560503,
                amount_gwei=12370678,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560504,
                amount_gwei=12427523,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560505,
                amount_gwei=12452624,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560506,
                amount_gwei=12405165,
                withdrawal_address_id=w_addr.id,
            ),
            Withdrawal(
                slot=6351700,
                validator_index=560507,
                amount_gwei=12387543,
                withdrawal_address_id=w_addr.id,
            ),
        ):
            session.add(obj)


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
                block_hash="0x56a9bb0302da44b8c0b3df540781424684c3af04d0b7a38d72842b762076a664",
            ),
            45031378244766393234,
            False,
            None,
            None,
            id="First PoS block, no MEV, but high value transactions",
        ),
        pytest.param(
            SlotProposerData(
                slot=6191844,
                proposer_index=167227,
                fee_recipient="0xfFEE087852cb4898e6c3532E776e68BC68b1143B",
                block_number=17017509,
                block_hash="0x30d106a7c165d31c3eac81c29b953486a1603f8bf5651b8f937f70c1b6b03bf7",
            ),
            17545396683647876,
            False,
            None,
            None,
            id="Custom block extra data, no MEV",
        ),
        pytest.param(
            SlotProposerData(
                slot=6187369,
                proposer_index=482339,
                fee_recipient="0xBaF6dC2E647aeb6F510f9e318856A1BCd66C5e19",
                block_number=17013112,
                block_hash="0x601cab422c5a77cf9fb9760bf24fe9bf6fcaf412a0d9c218cd8c5380dbc4116c",
            ),
            35280360457476597,
            True,
            "0xd6bdd5c289a38ea7bbd57da9625dba60cee94879",
            34547692347953310,
            id="MEV recipient is forwarder contract => balance change 0 need to be corrected",
        ),
        pytest.param(
            SlotProposerData(
                slot=6192483,
                proposer_index=477975,
                fee_recipient="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
                block_number=17018135,
                block_hash="0x8fb07fa40d42dd7105ed3e43a3a40ee0a66cc21e4719276e6a5a13fda03045bf",
            ),
            58312857563956762,
            True,
            "0x6d2e03b7effeae98bd302a9f836d0d6ab0002766",
            61170542217540723,
            id="MEV transferred in last tx of block (no relay - beaverbuild)",
        ),
        pytest.param(
            SlotProposerData(
                slot=6193187,
                proposer_index=112734,
                fee_recipient="0x1f9090aaE28b8a3dCeaDf281B0F12828e676c326",
                block_number=17018818,
                block_hash="0x696e0338c9c307ba805cd93dbda3fda808a087b2d6a72213d3da47c105d71846",
            ),
            31309679814111626,
            True,
            "0x6ead79c8a48374a697f3d22f165d428f7491677d",
            125680445416592626,
            id="MEV transferred in last tx of block (no relay - rsync-builder)",
        ),
        pytest.param(
            SlotProposerData(
                slot=6193817,
                proposer_index=546279,
                fee_recipient="0x1f9090aaE28b8a3dCeaDf281B0F12828e676c326",
                block_number=17019435,
                block_hash="0x22c0a29bc7b8e373a5ab49cac12ab4ddc4b7fec43061032d030edb223568e9d5",
            ),
            75580509182964951,
            True,
            "0xd4e96ef8eee8678dbff4d535e033ed1a4f7605b7",
            72227182665166041,
            id="MEV transferred in last tx of block (no relay - rsync-builder), MEV less than tx fees",
        ),
        pytest.param(
            SlotProposerData(
                slot=6199691,
                proposer_index=89030,
                fee_recipient="0xf8636377b7a998B51a3Cf2BD711B870B3Ab0Ad56",
                block_number=17025199,
                block_hash="0x3e99060ebc408bd9efecaf7878a88b5d1788ce5e7fcd10f0f5676f7c1a380455",
            ),
            40_689_838_623_939_694,
            True,
            "0xf8636377b7a998B51a3Cf2BD711B870B3Ab0Ad56",
            41_069_778_624_567_694,
            id="MEV transferred in first tx of block (no relay but extra data says bloxroute) as part of smart contract call - internal tx",
        ),
        pytest.param(
            SlotProposerData(
                slot=5000001,
                proposer_index=5639,
                fee_recipient="0x9780713736db73d09b7fecba15c25679f55bd13e",
                block_number=15835293,
                block_hash="0x9bf7fa242acb81d00a1d9db763d6aeae64d47255a0be8722fe728b5446f5b8e7",
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
                block_hash="0x0d1b998bf0e99970b3d7d11de8d159e294d7c8308d12978e373540ebe5dc3347",
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
                block_hash="0xc65f374db17ecd46ddda8c10e5eb7a6f680e42f39f79e9e5b970c2bbebdf801a",
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
                block_hash="0x3a2b0df6ebf97a986d7808fce76762346d8666dcf5ed5096b54c541c76f03088",
            ),
            21431599381708251,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            55911493587517345,
            id="BloXroute normal tx in middle of block",
            # https://etherscan.io/tx/0x97d5acbf74e8488bb0477377114697283b2eb922706b6a2db4746341dc401971
            marks=pytest.mark.xfail(reason="nonstandard MEV transfer from bloxroute builder"
                                           ", looks like regular tx, no relay admits to it",
                                    raises=ManualInspectionRequired),
        ),
        pytest.param(
            SlotProposerData(
                slot=5161642,
                proposer_index=310877,
                fee_recipient="0x388c818ca8b9251b393131c08a736a67ccb19297",
                block_number=15996004,
                block_hash="0x9859536913ae80f6a3a7764831b2c2abacdabcd49a45c8b8b18b5081dadae68f",
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
                block_hash="0x051187c79b6be2692b04ad00bd25b8b4fc088dff7e5148e61c062946c914562f",
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
                block_hash="0x011bab4a3f24a8fca0b2b8485f4a2daf7ede4f0470d252560df12a062746c552",
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
                block_hash="0x0d07b428210a5dfc3816614b52211e9e3257ae1bb23f1b289defe7786bc1439a",
            ),
            72_741_750_891_599_650,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            293_457_340_971_917_571,
            id="Non-standard MEV payout in 3 separate transactions in the middle of a block",
            marks=pytest.mark.xfail(reason="nonstandard MEV transfer from bloxroute builder"
                                           ", looks like regular tx, no relay admits to it",
                                    raises=ManualInspectionRequired,),
        ),
        pytest.param(
            SlotProposerData(
                slot=4810472,
                proposer_index=266974,
                fee_recipient="0xd4e96ef8eee8678dbff4d535e033ed1a4f7605b7",
                block_number=15646882,
                block_hash="0xf072549594292b9e63bb9321cc0f048cecc5a5d55b960faf170a33ea3e0a692a",
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
                block_hash="0x1bf8955467e91352780ebb2f79dea9ce6ffdb10677838e3631f3d3113bbd2f94",
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
                block_hash="0xe1dde266322569bcb0bd6a82a012a4a9fb75c8dc9d67e84892b21afaf872f02d",
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
                block_hash="0xd1d0405544c3878dde1f3a55d656104fbe48fff1b24a84554c36016944ba2eb1",
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
                block_hash="0x2614a0348001a4b6c2fd9556be7feacf569132fc4bd6e9dfd66a024450add0e0",
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
                block_hash="0xc5013fe1abbda91f5ae110e8a06c06a06052960559c18a695c28b24b4c0b250e",
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
                block_hash="0xdc348a83aa89c04b87daa54f545bccd144697d8a35c2ca16a2ba7fb96bf13e25",
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
                block_hash="0x667cacc2d569412794cb5278da3ae8aeec482e4e801c7e4b2f0966c0cf249830",
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
                block_hash="0x19603ff5562ce0c179ba9af9f709deb8c334dcb07a4f75c88c29c785dff6e670",
            ),
            117646288386850207,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            0,
            id="huge but FAKE reward via Eden",
            marks=pytest.mark.xfail(reason="huge but FAKE reward via Eden",
                                    raises=ManualInspectionRequired),
        ),
        pytest.param(
            SlotProposerData(
                slot=4882764,
                proposer_index=337362,
                fee_recipient="0xa45ae232688be5b472c1d3fc83d55c63c7aa80e3",
                block_number=15718719,
                block_hash="0xcf897e289835afde4ecced7a9a0711277b720157c8858dac357a18a38323bfcd",
            ),
            66959833957515037,
            True,
            "0x388c818ca8b9251b393131c08a736a67ccb19297",
            0,
            id="MEV transfer tx ran out of gas",
            marks=pytest.mark.xfail(reason="huge but FAKE reward via Eden",
                                    raises=ManualInspectionRequired),
        ),
        pytest.param(
            SlotProposerData(
                slot=4882802,
                proposer_index=253184,
                fee_recipient="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
                block_number=15718756,
                block_hash="0x25570ea5ec964f72605e54d05cec312c9b88e0654303318e6a74c251774a2169",
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
                block_hash="0xe0164037d06b0c943f4471513972feea3e4c2ab47ddb72383df95b1d58af96e1",
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
                block_hash="0x9edb122a4f7aec425b37ea446f597d49c9e656cee41af0b9d009b96dd6047062",
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
                block_hash="0x33863f114273bdfae03dbc69c4ec7b2c25444bfd786716e7966e5855d1fa926e",
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
                block_hash="0xf32200f31ddb03521dab3527b77b4c5e493701d3534ca88349f61d05286dc03f",
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
                block_hash="0x93712f386b66bde4b41c0c9d04dd31992294c42063c4a70abc572374d877d6d5",
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
                block_hash="0x7b57c72ad3c96a5673fe40a7f2ec50771aacdf0e5aad89eb265e989954ddaec6",
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
                block_hash="0x54556b6c5e97ff5de92803ecfcc52ce43d79c544930596f508c1d878cfe5224b",
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
                block_hash="0x2fe650f0c29ead8ff77eb650e87fda1dea54e2f16185b568a3d26962d0fced2f",
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
                block_hash="0x8f5777a4941059933aed64abbdbf9d115d697aec3901c0b7aef35efa616fcf4c",
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
                block_hash="0xc3c808ba70efbfa5bb3545587754cf9911cb9209927936ff5ae91f9a3846a786",
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
                block_hash="0xe27cef1547da282c65f547b78ad73d679fd25833ab282b82ae2633fe3cc0e457",
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
                block_hash="0x114e43482cb20353b463481733ca698d8418fd815aad90293ab55ad8022ab26e",
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
                block_hash="0x55323e2dce48d56be1fc43777b7e1e987b1115d7bb1119090e1bd923ed3b5daf",
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
                block_hash="0xc91c4494a3bc4fdbef3596de2738b99af466b8807ff6c2a31855aa4bce9dc56d",
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
                block_hash="0xaf123b3740d21b475dde17a5b541fee3e4fbb172831048e21f49a22fe98f3d20",
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
                block_hash="0x4ea7b84dd8d03aea675bf5b7851779b9042c571068d4985511b429c40f072263",
            ),
            119237863664011794,
            True,
            "0x7cd1af7d5299c5bfd4a63291eb5aa57f0ce60024",
            12385111686554897,
            id="contract that forwards rewards to Kraken?",
        ),
        pytest.param(
            SlotProposerData(
                slot=5362004,
                proposer_index=442302,
                fee_recipient="0x0000000000000000000000000000000000000000",
                block_number=16195134,
                block_hash="0x93f86d6aafce2293541ad896649076bd79eeeb09657f0618b7b094f49a1bc35e",
            ),
            36417235491435301,
            False,
            None,
            None,
            id="fee recipient null address 0x00..00 while someone also sent something to the burn address",
        ),
        pytest.param(
            SlotProposerData(
                slot=5442676,
                proposer_index=469716,
                fee_recipient="0x00000000219ab540356cbb839cbe05303d7705fa",
                block_number=16275423,
                block_hash="0x88553fe383f6f32c566024be1c90793500ca9a996302e6b9620c275b61b0bb2c",
            ),
            36417235491435301,
            False,
            None,
            None,
            id="fee recipient is beacon deposit contract, during same block a deposit was made",
        ),
        pytest.param(
            SlotProposerData(
                slot=5573539,
                proposer_index=20707,
                fee_recipient="0xbaf6dc2e647aeb6f510f9e318856a1bcd66c5e19",
                block_number=16405641,
                block_hash="0x353e2f9cb9789ff4704b006202689577ce92a6123c7ea4f08acf477352ee1ae5",
            ),
            36417235491435301,
            True,
            "0xffee087852cb4898e6c3532e776e68bc68b1143b",
            42,
            id="fee recipient is beacon deposit contract, during same block a deposit was made",
        ),
        pytest.param(
            SlotProposerData(
                slot=6364511,
                proposer_index=27745,
                fee_recipient="0x690B9A9E9aa1C9dB991C7721a92d351Db4FaC990",
                block_number=17186880,
                block_hash="0xe95a33fb5f54e4cece77cc6a8db2bdc1bf8536a4107bc25a31c7b692f42e8e40",
            ),
            54227362614983699,
            True,
            "0x3aebb186370d77d305437dbc02af8b89cec27b8b",
            54677735662095469,
            id="MEV block without relay",
        ),
        pytest.param(
            SlotProposerData(
                slot=6351700,
                proposer_index=560924,
                fee_recipient="0xfeebabe6b0418ec13b30aadf129f5dcdd4f70cea",
                block_number=17174234,
                block_hash="0xcb2190a1d086b96bcdf9f2afcc97a5a6e9cc6b17f273f6105937710f99448b0b",
            ),
            30375880058298728,
            True,
            "0xde12c3d2257fc9bb1c1a00d409f292eecd55ffaf",
            29127481592378074,
            id="MEV reward recipient receives withdrawals during a block they propose",
        ),
    ],
)
@pytest.mark.asyncio
@pytest.mark.usefixtures("_withdrawals_in_db")
async def test_get_block_reward_value(
        slot_proposer_data, expected_priority_tx_fees, expected_contains_mev, expected_mev_reward_recipient, expected_mev_reward,
        execution_node, db_provider,
):
    block_reward_value = await get_block_reward_value(
        slot_proposer_data=slot_proposer_data,
        execution_node=execution_node,
        db_provider=db_provider,
    )
    assert block_reward_value.block_priority_tx_fees == expected_priority_tx_fees
    assert block_reward_value.contains_mev == expected_contains_mev
    assert block_reward_value.mev_recipient == expected_mev_reward_recipient
    assert block_reward_value.mev_recipient_balance_change == expected_mev_reward
