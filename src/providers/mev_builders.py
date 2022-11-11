from enum import Enum
from typing import Optional, Union


class MevPayoutType(Enum):
    # MEV is the value of the last tx in the block (tx.from_ = builder, tx.to = proposer, MEV = tx.value)
    # E.g. Flasbots/bloxRoute/...
    LAST_TX = "LAST_TX"
    # Builder does not "override" the fee recipient, MEV value is only comprised of block rewards.
    # (Also called the "coinbase" type, because it transfers the MEV to the block's beneficiary address,
    # the fee recipient, using the COINBASE opcode)
    # E.g. Manifest
    DIRECT = "DIRECT"
    # Builder does not "override" the fee recipient. MEV value is a combination of block rewards
    # and internal transactions to fee recipient address.
    # E.g. Relayooor.wtf builder
    CONTRACT_CALL_INTERNAL_TXS = "CONTRACT_CALL_INTERNAL_TXS"
    # Builder overrides the fee recipient, sets it to a distributor contract which distributes the reward
    # between the builder and proposer
    CONTRACT_DISTRIBUTOR = "CONTRACT_DISTRIBUTOR"


class MevBuilder:
    def __init__(
            self,
            name: str,
            fee_recipient_address: Optional[str],
            payout_type: MevPayoutType,
            extra_data_values: list[Union[str, None]],
    ):
        self.name = name
        self.fee_recipient_address = fee_recipient_address
        self.payout_type = payout_type
        self.extra_data_values = extra_data_values


MEV_BUILDERS = [
    MevBuilder(
        name="builder0x69",
        fee_recipient_address="0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "by builder0x69", "by @builder0x69", "@builder0x69", "builder0x69",
            "\u0603\x01\n\x17gethgo1.18.5linux",
        ],
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0xb64a30399f7f6b0c154c2e7af0a3ec7b0a5b131a",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Illuminate Dmocratize Dstribute"],
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x9d8e2dc5615c674f329d18786d52af10a65af08b",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Illuminate Dmocratize Dstribute"],
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x089780a88f35b58144aa8a9be654207a1afe7959",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Illuminate Dmocratize Dstribute"],
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0x1d0124fee8dbe21884ab97adccbf5c55d768886e",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Illuminate Dmocratize Dstribute"],
    ),
    MevBuilder(
        name="Flashbots builder",
        fee_recipient_address="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Illuminate Dmocratize Dstribute"],
    ),
    MevBuilder(
        name="bloXroute maxprofit builder",
        fee_recipient_address="0xf2f5c73fa04406b1995e397b55c24ab1f3ea726c",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="bloXroute regulated builder",
        fee_recipient_address="0x199d5ed7f45f4ee35960cf22eade2076e95b253f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="bloXroute ethical builder",
        fee_recipient_address="0xf573d99385c05c23b24ed33de616ad16a43a0919",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="bloXroute external builder",
        fee_recipient_address=None,
        payout_type=MevPayoutType.CONTRACT_CALL_INTERNAL_TXS,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="Eden network builder",
        fee_recipient_address="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            None,
            "\u0603\x01\n\x17gethgo1.18.6linux",
        ],
    ),
    MevBuilder(
        name="7dfc",
        fee_recipient_address="0x473780deaf4a2ac070bbba936b0cdefe7f267dfc",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\x0b\x00gethgo1.19.1linux",
            "\u0603\x01\n\x17gethgo1.19.1linux",
        ],
    ),
    MevBuilder(
        name="05b9",
        fee_recipient_address="0x8d5998a27b3cdf33479b65b18f075e20a7aa05b9",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["\u0603\x01\x0b\x00gethgo1.19.1linux"],
    ),
    MevBuilder(
        name="7128",
        fee_recipient_address="0xb646d87963da1fb9d192ddba775f24f33e857128",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\n\x17gethgo1.18.6linux",
            "\u0603\x01\n\x17gethgo1.18.7linux",
            "Buildoooooooooooooor",
        ],
    ),
    MevBuilder(
        name="466f",
        fee_recipient_address="0x25d88437df70730122b73ef35462435d187c466f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\x0b\x00gethgo1.18.2linux",
            "\u0603\x01\n\x17gethgo1.18.2linux",
        ],
    ),
    MevBuilder(
        name="0bf0",
        fee_recipient_address="0xc4b9beb1b7efb04deea31dc3b4c32a88ee210bf0",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="beaverbuild.org",
        fee_recipient_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "beaverbuild.org",
            "\"\"",
        ],
    ),
    MevBuilder(
        name="Manifold",
        fee_recipient_address=None,
        payout_type=MevPayoutType.DIRECT,
        extra_data_values=["Manifold"],
    ),
    MevBuilder(
        name="Blocknative",
        fee_recipient_address=None,
        payout_type=MevPayoutType.DIRECT,
        extra_data_values=["Made on the moon by Blocknative"],
    ),
    MevBuilder(
        name="Relayooor.wtf",
        fee_recipient_address=None,
        payout_type=MevPayoutType.CONTRACT_CALL_INTERNAL_TXS,
        extra_data_values=["Viva relayooor.wtf"],
    ),
    MevBuilder(
        name="eth-builder.com",
        fee_recipient_address="0xfeebabe6b0418ec13b30aadf129f5dcdd4f70cea",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["https://eth-builder.com"],
    ),
    MevBuilder(
        name="05b9",
        fee_recipient_address="0x8D5998A27b3CdF33479B65B18F075E20a7aa05b9",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="b649",
        fee_recipient_address="0x57af10ed3469b2351ae60175d3c9b3740e1bb649",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="79a1",
        fee_recipient_address="0xd1a0b5843f384f92a6759015c742fc12d1d579a1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="91ed",
        fee_recipient_address="0xae08c571e771f360c35f5715e36407ecc89d91ed",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="ohexanon",
        fee_recipient_address="0xbc178995898b0f611b4360df5ad653cdebe6de3f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["ohexanon"],
    ),
    MevBuilder(
        name="neoconstruction.eth",
        fee_recipient_address="0x09fa51ab5387fb563200494e09e3c19cc0993c85",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["𝙉eo𝘾onstruction✦"],
    ),
    MevBuilder(
        name="3cf1",
        fee_recipient_address="0xed7ce3de532213314bb07622d8bf606a4ba03cf1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="16c5",
        fee_recipient_address="0xc1612dc56c3e7e00d86c668df03904b7e59616c5",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\n\x17gethgo1.18.1linux",
            "\u0603\x01\n\x17gethgo1.18.2linux",
        ],
    ),
    MevBuilder(
        name="0d94",
        fee_recipient_address="0xa7fdca7aa0b69927a34ec48ddcfe3d4c66ff0d94",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\n\x17gethgo1.18.1linux",
        ],
    ),
    MevBuilder(
        name="2488",
        fee_recipient_address="0x001ee00bee25f81444e2d172773f37fe05ea2488",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\n\x17gethgo1.19.1linux",
        ],
    ),
    MevBuilder(
        name="abc 514b",
        fee_recipient_address="0x2cd54c2f60d94442ea38027df42663f1438e514b",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "abc",
            None,
        ],
    ),
    MevBuilder(
        name="miao?",
        fee_recipient_address="0x43dd22c94c1c1d46f4fcf664e2d7b11dee1d4154",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "miao?",
            "miao?01",
        ],
    ),
    MevBuilder(
        name="e210",
        fee_recipient_address="0xfee4446922f6e29834dea37d9e9192ccabf1e210",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            None,
        ],
    ),
    MevBuilder(
        name="I can haz block?",
        fee_recipient_address="0x229b8325bb9ac04602898b7e8989998710235d5f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "I can haz block?",
        ],
    ),
    # a2e1 - splits block reward to proposer and builder?
    # Disabled right now, since it's not clear if this is MEV reward distribution -> at the moment assuming no.
    # It was also not clear from the tx data input who is the builder/proposer...
    # MevBuilder(
    #     name="a2e1 contract distributor",
    #     fee_recipient_address="0x7d00a2bc1370b9005eb100004da500924600a2e1",
    #     payout_type=MevPayoutType.CONTRACT_DISTRIBUTOR,
    #     extra_data_values=[None],
    # ),
]


def extra_data_contains_common_substring(value: str) -> bool:
    return any(substring in value for substring in {"gethgo"} if value is not None)


BUILDER_FEE_RECIPIENTS = set()
for b in MEV_BUILDERS:
    if b.fee_recipient_address is not None:
        BUILDER_FEE_RECIPIENTS.add(b.fee_recipient_address)
