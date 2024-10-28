from typing import Optional


class MevBuilder:
    def __init__(
            self,
            name: str,
            fee_recipient_address: Optional[str],
    ):
        self.name = name
        self.fee_recipient_address = fee_recipient_address


MEV_BUILDERS = [
    MevBuilder(
        name="builder0x69",
        fee_recipient_address="0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0xb64a30399f7f6b0c154c2e7af0a3ec7b0a5b131a",
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x9d8e2dc5615c674f329d18786d52af10a65af08b",
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x089780a88f35b58144aa8a9be654207a1afe7959",
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x1d0124fee8dbe21884ab97adccbf5c55d768886e",
    ),
    MevBuilder(
        name="Flashbots builder",
        fee_recipient_address="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
    ),
    MevBuilder(
        name="bloXroute maxprofit builder",
        fee_recipient_address="0xf2f5c73fa04406b1995e397b55c24ab1f3ea726c",
    ),
    MevBuilder(
        name="bloXroute regulated builder",
        fee_recipient_address="0x199d5ed7f45f4ee35960cf22eade2076e95b253f",
    ),
    MevBuilder(
        name="bloXroute ethical builder",
        fee_recipient_address="0xf573d99385c05c23b24ed33de616ad16a43a0919",
    ),
    MevBuilder(
        name="Eden network builder",
        fee_recipient_address="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
    ),
    MevBuilder(
        name="7dfc",
        fee_recipient_address="0x473780deaf4a2ac070bbba936b0cdefe7f267dfc",
    ),
    MevBuilder(
        name="05b9",
        fee_recipient_address="0x8d5998a27b3cdf33479b65b18f075e20a7aa05b9",
    ),
    MevBuilder(
        name="7128",
        fee_recipient_address="0xb646d87963da1fb9d192ddba775f24f33e857128",
    ),
    MevBuilder(
        name="466f",
        fee_recipient_address="0x25d88437df70730122b73ef35462435d187c466f",
    ),
    MevBuilder(
        name="0bf0",
        fee_recipient_address="0xc4b9beb1b7efb04deea31dc3b4c32a88ee210bf0",
    ),
    MevBuilder(
        name="beaverbuild.org",
        fee_recipient_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
    ),
    MevBuilder(
        name="rsync-builder",
        fee_recipient_address="0x1f9090aae28b8a3dceadf281b0f12828e676c326",
    ),
    MevBuilder(
        name="manta-builder",
        fee_recipient_address="0x5F927395213ee6b95dE97bDdCb1b2B1C0F16844F",
    ),
    MevBuilder(
        name="eth-builder.com",
        fee_recipient_address="0xfeebabe6b0418ec13b30aadf129f5dcdd4f70cea",
    ),
    MevBuilder(
        name="05b9",
        fee_recipient_address="0x8D5998A27b3CdF33479B65B18F075E20a7aa05b9",
    ),
    MevBuilder(
        name="b649",
        fee_recipient_address="0x57af10ed3469b2351ae60175d3c9b3740e1bb649",
    ),
    MevBuilder(
        name="79a1",
        fee_recipient_address="0xd1a0b5843f384f92a6759015c742fc12d1d579a1",
    ),
    MevBuilder(
        name="91ed",
        fee_recipient_address="0xae08c571e771f360c35f5715e36407ecc89d91ed",
    ),
    MevBuilder(
        name="ohexanon",
        fee_recipient_address="0xbc178995898b0f611b4360df5ad653cdebe6de3f",
    ),
    MevBuilder(
        name="neoconstruction.eth",
        fee_recipient_address="0x09fa51ab5387fb563200494e09e3c19cc0993c85",
    ),
    MevBuilder(
        name="3cf1",
        fee_recipient_address="0xed7ce3de532213314bb07622d8bf606a4ba03cf1",
    ),
    MevBuilder(
        name="16c5",
        fee_recipient_address="0xc1612dc56c3e7e00d86c668df03904b7e59616c5",
    ),
    MevBuilder(
        name="0d94",
        fee_recipient_address="0xa7fdca7aa0b69927a34ec48ddcfe3d4c66ff0d94",
    ),
    MevBuilder(
        name="2488",
        fee_recipient_address="0x001ee00bee25f81444e2d172773f37fe05ea2488",
    ),
    MevBuilder(
        name="abc 514b",
        fee_recipient_address="0x2cd54c2f60d94442ea38027df42663f1438e514b",
    ),
    MevBuilder(
        name="miao?",
        fee_recipient_address="0x43dd22c94c1c1d46f4fcf664e2d7b11dee1d4154",
    ),
    MevBuilder(
        name="e210",
        fee_recipient_address="0xfee4446922f6e29834dea37d9e9192ccabf1e210",
    ),
    MevBuilder(
        name="I can haz block?",
        fee_recipient_address="0x229b8325bb9ac04602898b7e8989998710235d5f",
    ),
    MevBuilder(
        name="16cf",
        fee_recipient_address="0x4460735849b78fd924cf0f21fca0ffc80c8b16cf",
    ),
    MevBuilder(
        name="c36a",
        fee_recipient_address="0x3c496df419762533607f30bb2143aff77bebc36a",
    ),
    MevBuilder(
        name="3b01",
        fee_recipient_address="0xbd3afb0bb76683ecb4225f9dbc91f998713c3b01",
    ),
    MevBuilder(
        name="82a1",
        fee_recipient_address="0x707fc1439cd11b34a984b989a18476c24a1182a1",
    ),
    MevBuilder(
        name="861c",
        fee_recipient_address="0xc08661e7d70f5a9f02e3e807e93cbef4747f861c",
    ),
    MevBuilder(
        name="0e3c",
        fee_recipient_address="0x4a55474eacb48cefe25d7656db1976aa7ae70e3c",
    ),
    MevBuilder(
        name="50e3",
        fee_recipient_address="0xeeee8db5fc7d505e99970945a9220ab7992050e3",
    ),
    MevBuilder(
        name="ded7",
        fee_recipient_address="0x1324c0fb6f45f3bf1aaa1fcdc08f17431f53ded7",
    ),
    MevBuilder(
        name="e365",
        fee_recipient_address="0xeeee755e55316154f4db6b9958f511a74e22e365",
    ),
    MevBuilder(
        name="5e19",
        fee_recipient_address="0xbaf6dc2e647aeb6f510f9e318856a1bcd66c5e19",
    ),
    MevBuilder(
        name="1fff",
        fee_recipient_address="0x3b7faec3181114a99c243608bc822c5436441fff",
    ),
    MevBuilder(
        name="titanbuilder.eth",
        fee_recipient_address="0x4838B106FCe9647Bdf1E7877BF73cE8B0BAD5f97",
    ),
    MevBuilder(
        name="tbuilder.xyz",
        fee_recipient_address="0xDccA982701a264e8d629A6E8CFBa9C1a27912623",
    ),
    MevBuilder(
        name="jetbldr.eth",
        fee_recipient_address="0x88c6C46EBf353A52Bdbab708c23D0c81dAA8134A",
    ),
]

BUILDER_FEE_RECIPIENTS = { b.fee_recipient_address.lower() for b in MEV_BUILDERS }
