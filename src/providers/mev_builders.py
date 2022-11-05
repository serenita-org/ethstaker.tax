from enum import Enum
from typing import Optional, Union


class MevPayoutType(Enum):
    # MEV is the value of the last tx in the block (tx.from_ = builder, tx.to = proposer, MEV = tx.value)
    LAST_TX = "LAST_TX"
    # Builder does not "override" the fee recipient, MEV value is only comprised of block rewards.
    DIRECT = "DIRECT"
    # Builder does not "override" the fee recipient. MEV value is a combination of block rewards
    # and internal transactions to fee recipient address.
    RELAYOOOR = "RELAYOOOR"


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
        extra_data_values=["by builder0x69", "by @builder0x69", "@builder0x69"],
    ),
    MevBuilder(
        name="Flashbots builder - inactive now?",
        fee_recipient_address="0xb64a30399f7f6b0c154c2e7af0a3ec7b0a5b131a",
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
        name="bloxroute regulated builder",
        fee_recipient_address="0x199d5ed7f45f4ee35960cf22eade2076e95b253f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="bloxroute ethical builder",
        fee_recipient_address="0xf573d99385c05c23b24ed33de616ad16a43a0919",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["Powered by bloXroute"],
    ),
    MevBuilder(
        name="Eden network builder",
        fee_recipient_address="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x473780deaf4a2ac070bbba936b0cdefe7f267dfc",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["\u0603\x01\x0b\x00gethgo1.19.1linux"],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x8d5998a27b3cdf33479b65b18f075e20a7aa05b9",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["\u0603\x01\x0b\x00gethgo1.19.1linux"],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x25d88437df70730122b73ef35462435d187c466f",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[
            "\u0603\x01\x0b\x00gethgo1.18.2linux",
            "\u0603\x01\n\x17gethgo1.18.2linux",
        ],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0xc4b9beb1b7efb04deea31dc3b4c32a88ee210bf0",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="beaverbuild.org",
        fee_recipient_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["beaverbuild.org"],
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
        name="Viva relayooor.wtf",
        fee_recipient_address=None,
        payout_type=MevPayoutType.RELAYOOOR,
        extra_data_values=["Viva relayooor.wtf"],
    ),
    MevBuilder(
        name="eth-builder.com",
        fee_recipient_address="0xfeebabe6b0418ec13b30aadf129f5dcdd4f70cea",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=["https://eth-builder.com"],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x8D5998A27b3CdF33479B65B18F075E20a7aa05b9",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x57af10ed3469b2351ae60175d3c9b3740e1bb649",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0xd1a0b5843f384f92a6759015c742fc12d1d579a1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
    MevBuilder(
        name="?",
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
        name="?",
        fee_recipient_address="0xed7ce3de532213314bb07622d8bf606a4ba03cf1",
        payout_type=MevPayoutType.LAST_TX,
        extra_data_values=[None],
    ),
]
KNOWN_EXTRA_DATA_FIELDS_MEV = set()
KNOWN_FEE_RECIPIENTS_MEV = set()
for b in MEV_BUILDERS:
    if b.fee_recipient_address is not None:
        KNOWN_FEE_RECIPIENTS_MEV.add(b.fee_recipient_address)
    for extra_data_value in b.extra_data_values:
        KNOWN_EXTRA_DATA_FIELDS_MEV.add(extra_data_value)
