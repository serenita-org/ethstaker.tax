from enum import Enum


class MevPayoutType(Enum):
    LAST_TX = "LAST_TX"
    COINBASE = "COINBASE"


class MevProvider:
    def __init__(self, name: str, fee_recipient_address: str, payout_type: MevPayoutType):
        self.name = name
        self.fee_recipient_address = fee_recipient_address
        self.payout_type = payout_type


MEV_BUILDERS = [
    MevProvider(
        name="builder0x69",
        fee_recipient_address="0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="Flashbots builder",
        fee_recipient_address="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="bloXroute maxprofit builder",
        fee_recipient_address="0xf2f5c73fa04406b1995e397b55c24ab1f3ea726c",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="bloxroute regulated builder",
        fee_recipient_address="0x199d5ed7f45f4ee35960cf22eade2076e95b253f",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="bloxroute ethical builder",
        fee_recipient_address="0xf573d99385c05c23b24ed33de616ad16a43a0919",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="Eden network builder",
        fee_recipient_address="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="?",
        fee_recipient_address="0x473780deaf4a2ac070bbba936b0cdefe7f267dfc",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevProvider(
        name="beaverbuild.org",
        fee_recipient_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        payout_type=MevPayoutType.LAST_TX,
    ),
]
MEV_BUILDERS = {b.fee_recipient_address: b for b in MEV_BUILDERS}
