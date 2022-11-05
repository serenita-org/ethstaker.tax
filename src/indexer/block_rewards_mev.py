from enum import Enum
from typing import Optional
import logging

from providers.beacon_node import BlockRewardData
from providers.execution_node import ExecutionNode


EXECUTION_NODE = ExecutionNode()
logger = logging.getLogger(__name__)


class MevPayoutType(Enum):
    # MEV is the value of the last tx in the block (tx.from_ = builder, tx.to = proposer, MEV = tx.value)
    LAST_TX = "LAST_TX"
    # Builder does not "override" the fee recipient, MEV value is only comprised of block rewards.
    DIRECT = "DIRECT"
    # Builder does not "override" the fee recipient. MEV value is a combination of block reward and internal transactions
    # to fee recipient address.
    RELAYOOOR = "RELAYOOOR"


class MevBuilder:
    def __init__(self, name: str, fee_recipient_address: Optional[str], payout_type: MevPayoutType, contract_address: str = None):
        self.name = name
        self.fee_recipient_address = fee_recipient_address
        self.payout_type = payout_type
        self.contract_address = contract_address


MEV_BUILDERS = [
    MevBuilder(
        name="builder0x69",
        fee_recipient_address="0x690b9a9e9aa1c9db991c7721a92d351db4fac990",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="Flashbots builder",
        fee_recipient_address="0xdafea492d9c6733ae3d56b7ed1adb60692c98bc5",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="bloXroute maxprofit builder",
        fee_recipient_address="0xf2f5c73fa04406b1995e397b55c24ab1f3ea726c",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="bloxroute regulated builder",
        fee_recipient_address="0x199d5ed7f45f4ee35960cf22eade2076e95b253f",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="bloxroute ethical builder",
        fee_recipient_address="0xf573d99385c05c23b24ed33de616ad16a43a0919",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="Eden network builder",
        fee_recipient_address="0xaab27b150451726ec7738aa1d0a94505c8729bd1",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="?",
        fee_recipient_address="0x473780deaf4a2ac070bbba936b0cdefe7f267dfc",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="beaverbuild.org",
        fee_recipient_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        payout_type=MevPayoutType.LAST_TX,
    ),
    MevBuilder(
        name="Manifold",  # This should be equal to the block extra data field
        fee_recipient_address=None,
        payout_type=MevPayoutType.DIRECT,
    ),
    MevBuilder(
        name="Viva relayooor.wtf",  # This should be equal to the block extra data field
        fee_recipient_address=None,
        payout_type=MevPayoutType.RELAYOOOR,
        contract_address="0x4a137fd5e7a256ef08a7de531a17d0be0cc7b6b6",
    )
]


async def get_block_reward_value(block_reward_data: BlockRewardData) -> tuple[int, bool]:
    block_contains_mev = False

    # Most builders set themselves as fee recipient and send MEV to proposer in a tx
    if block_reward_data.fee_recipient in (
            b.fee_recipient_address for b in MEV_BUILDERS if b.payout_type == MevPayoutType.LAST_TX
    ):
        # Definitely MEV block
        tx_count = await EXECUTION_NODE.get_block_tx_count(block_number=block_reward_data.block_number)
        last_tx = await EXECUTION_NODE.get_tx_data(block_number=block_reward_data.block_number,
                                                   tx_index=tx_count - 1)
        assert last_tx.from_ == block_reward_data.fee_recipient
        proposer_reward = last_tx.value
        return proposer_reward, True

    # Fee recipient is not a known MEV builder
    # This could still be MEV but built by Manifold/other builders who do not override
    # the fee recipient and therefore don't have to make a transaction to pay out rewards
    miner_data = await EXECUTION_NODE.get_miner_data(block_number=block_reward_data.block_number)

    # Double check the coinbase is equal to the fee recipient for the block
    if miner_data.coinbase != block_reward_data.fee_recipient:
        raise ValueError(
            f"Coinbase {miner_data.coinbase} != fee recipient {block_reward_data.fee_recipient}, block number {block_reward_data.block_number}")

    # Process other types of MEV payout
    proposer_reward = 0
    if miner_data.extra_data in (b.name for b in MEV_BUILDERS if b.payout_type == MevPayoutType.DIRECT):
        block_contains_mev = True
    elif miner_data.extra_data in (b.name for b in MEV_BUILDERS if b.payout_type == MevPayoutType.RELAYOOOR):
        # Internal transactions need an archive node.
        # --> In order not to have to run one, I am simplifying a little here. Instead of checking the
        # internal transactions, I wanted to just check the balance change of the fee recipient between the previous block
        # and the current block.
        # This can lead to a wrong result (reward) in case the fee recipient also makes/receives a transfer
        # or interacts with a contract leading to a balance change within that same block.
        # There is no easy way of avoiding that completely without an archive node.
        # Anyway, the balance changes is also not available without an archive node (except for the last X blocks).
        # So using Infura archive node while indexing old blocks, once caught up, will switch back to my own node.
        # TODO switch back to local node after catching up
        fee_rec_bal_change = (
                                 await EXECUTION_NODE.get_balance(
                                     address=block_reward_data.fee_recipient,
                                     block_number=block_reward_data.block_number,
                                     use_infura=True,
                                 )
                             ) - (
                                await EXECUTION_NODE.get_balance(
                                    address=block_reward_data.fee_recipient,
                                    block_number=block_reward_data.block_number - 1,
                                    use_infura=True,
                                )
        )
        return fee_rec_bal_change, True

    burnt_tx_fees = await EXECUTION_NODE.get_burnt_tx_fees_for_block(block_number=block_reward_data.block_number)
    logger.debug(f"Proposer reward: {miner_data.tx_fee} - {burnt_tx_fees}")
    proposer_reward += miner_data.tx_fee - burnt_tx_fees

    return proposer_reward, block_contains_mev
