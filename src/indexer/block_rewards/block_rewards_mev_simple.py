import logging
import re
from collections import namedtuple

from providers.beacon_node import SlotProposerData
from providers.execution_node import ExecutionNode
from providers.mev_builders import BUILDER_FEE_RECIPIENTS
from indexer.block_rewards.mev_bots import SMART_CONTRACTS_MEV_BOTS
from indexer.block_rewards.smart_contract_fee_recipients import (
    _get_rocketpool_rewards_distribution_value, SMART_CONTRACTS_ROCKETPOOL,
    _get_lido_rewards_distribution_value, SMART_CONTRACT_LIDO_EXEC_LAYER_REWARDS_VAULT,
    _get_stakefish_rewards_distribution_value, SMART_CONTRACTS_STAKEFISH,
    _get_kraken_rewards_distribution_value, SMART_CONTRACTS_KRAKEN,
)

logger = logging.getLogger(__name__)

BlockRewardValue = namedtuple(
    "BlockRewardValue",
    ["block_priority_tx_fees", "contains_mev", "mev_recipient", "mev_recipient_balance_change"]
)


class ManualInspectionRequired(ValueError):
    pass


def _extra_data_indicates_mev(extra_data: str | None) -> bool:
    if extra_data is not None and any(s.match(extra_data) for s in (
            re.compile("^Manifold$"),
            re.compile("^Viva relayooor.wtf$"),
            re.compile("^Made on the moon by Blocknative$"),
            re.compile("^Powered by bloXroute$"),
    )):
        return True
    return False


async def _contains_call_to_mev_bot_contract(block_number: int, execution_node: ExecutionNode) -> bool:
    full_block = await execution_node.get_block(block_number, verbose=True)

    if any(tx["to"] in SMART_CONTRACTS_MEV_BOTS for tx in full_block["transactions"]):
        logger.warning(f"Found call to MEV Bot contract in {block_number}")
        return True
    return False


async def _contains_tx_from_builder_to_fee_recipient(block_number: int, fee_recipient: str, execution_node: ExecutionNode) -> bool:
    full_block = await execution_node.get_block(block_number, verbose=True)

    for tx in full_block["transactions"]:
        if tx["from"] in BUILDER_FEE_RECIPIENTS and tx["to"] == fee_recipient:
            logger.warning(f"Found tx from builder in {block_number} in unexpected location")
            return True
    return False


async def _get_balance_change_adjusted(address: str, block_number: int, block_priority_tx_fees: int, execution_node: ExecutionNode) -> int:
    balance_change = (
        await execution_node.get_balance(
            address=address,
            block_number=block_number,
            use_infura=True,
        )
    ) - (
        await execution_node.get_balance(
            address=address,
            block_number=block_number - 1,
            use_infura=True,
        )
    )

    # Account for frequently occurring fee recipient smart contract operations - reward distributions.
    # If during a block the smart contract fee recipient receives rewards AND distributes them,
    # the distributed rewards should be offset.
    if balance_change != block_priority_tx_fees:
        balance_change += await _get_fee_recipient_distribution_balance_change(address, block_number, execution_node=execution_node)

    # Account for outgoing transactions made by the address
    if balance_change != block_priority_tx_fees:
        full_block = await execution_node.get_block(block_number, verbose=True)
        for tx in full_block["transactions"]:
            tx_value = int(tx["value"], base=16)
            if tx["from"] == address:
                # Regular tx from fee recipient
                balance_change += (tx_value + await execution_node.get_tx_fee(tx["hash"]))

    return balance_change


async def _mev_return_value(block_number: int, mev_recipient: str, execution_node: ExecutionNode) -> BlockRewardValue:
    miner_data = await execution_node.get_miner_data(block_number=block_number)
    block_priority_tx_fees = await execution_node.get_block_priority_tx_fees(block_number, miner_data.tx_fee)

    # Check the MEV reward recipient's balance change to determine the MEV reward
    mev_recipient_balance_change = await _get_balance_change_adjusted(
        address=mev_recipient,
        block_number=block_number,
        block_priority_tx_fees=block_priority_tx_fees,
        execution_node=execution_node
    )

    if mev_recipient_balance_change == 0:
        raise ManualInspectionRequired(f"0 MEV recipient balance change in {block_number}")

    assert mev_recipient_balance_change >= 0, f"Negative MEV recipient balance change in {block_number}"

    return BlockRewardValue(
        block_priority_tx_fees=block_priority_tx_fees,
        contains_mev=True,
        mev_recipient=mev_recipient,
        mev_recipient_balance_change=mev_recipient_balance_change
    )


async def _get_fee_recipient_distribution_balance_change(fee_recipient: str, block_number: int, execution_node: ExecutionNode) -> int:
    # Account for frequently occurring fee recipient smart contract operations - reward distributions.
    # If the reward distribution occurs in a block that also pays out to this address,
    # the balance change will not match and the block reward may be off.
    if fee_recipient in SMART_CONTRACTS_ROCKETPOOL:
        return await _get_rocketpool_rewards_distribution_value(block_number, fee_recipient, execution_node=execution_node)
    elif fee_recipient == SMART_CONTRACT_LIDO_EXEC_LAYER_REWARDS_VAULT:
        return await _get_lido_rewards_distribution_value(block_number, execution_node=execution_node)
    elif fee_recipient in SMART_CONTRACTS_STAKEFISH:
        return await _get_stakefish_rewards_distribution_value(block_number, fee_recipient, execution_node=execution_node)
    elif fee_recipient in SMART_CONTRACTS_KRAKEN:
        return await _get_kraken_rewards_distribution_value(block_number, fee_recipient, execution_node=execution_node)
    else:
        return 0


async def get_block_reward_value(slot_proposer_data: SlotProposerData, execution_node: ExecutionNode) -> BlockRewardValue:
    """
    Returns the block's priority tx fees, a bool indicating whether the block contains MEV, the MEV reward recipient
    and the MEV reward value.
    """
    block_number = slot_proposer_data.block_number
    fee_recipient = slot_proposer_data.fee_recipient

    # Check for MEV distribution in last tx
    last_tx = None
    tx_count = await execution_node.get_block_tx_count(block_number=block_number)
    if tx_count > 0:
        last_tx = await execution_node.get_tx_data(block_number=block_number, tx_index=tx_count - 1)
    if fee_recipient in BUILDER_FEE_RECIPIENTS:
        # MEV reward recipient = recipient of last tx in block
        assert last_tx.from_ == fee_recipient, \
            f"Expected MEV distribution in last tx, but not found in block {block_number}"
        return await _mev_return_value(block_number=block_number, mev_recipient=last_tx.to, execution_node=execution_node)
    # If the sender of the last tx is the fee recipient, assume it's a MEV reward distribution
    elif last_tx is not None and last_tx.from_ == fee_recipient and last_tx.value > 0:
        logger.warning("Assuming MEV because of last tx in block.\n"
                       f"Block number: {block_number}, "
                       f"Fee recipient: {fee_recipient}")
        return await _mev_return_value(block_number=block_number, mev_recipient=last_tx.to, execution_node=execution_node)
    # Sometimes the MEV reward is not sent from the fee recipient address, but from one of these
    elif last_tx is not None and last_tx.from_ in (
        "0xc13ced137e90bc695cb77288962280516a2f9b8b",  # MevRefunder, e.g. block 15712761
    ):
        logger.warning(f"Last tx from {last_tx.from_} -> assuming MEV in block {block_number}")
        return await _mev_return_value(block_number=block_number, mev_recipient=last_tx.to, execution_node=execution_node)

    # Check for missed MEV distribution by comparing the fee recipient balance change
    # to the block priority tx fees
    miner_data = await execution_node.get_miner_data(block_number=block_number)
    block_extra_data_decoded = bytes.fromhex(miner_data.extra_data[2:]).decode(errors="ignore") if len(
        miner_data.extra_data) > 2 else None
    block_priority_tx_fees = await execution_node.get_block_priority_tx_fees(block_number, miner_data.tx_fee)
    fee_rec_bal_change = await _get_balance_change_adjusted(
        address=fee_recipient, block_number=block_number, block_priority_tx_fees=block_priority_tx_fees,
        execution_node=execution_node
    )

    if _extra_data_indicates_mev(block_extra_data_decoded):
        return await _mev_return_value(block_number=block_number, mev_recipient=fee_recipient, execution_node=execution_node)

    if fee_rec_bal_change != block_priority_tx_fees:
        if await _contains_call_to_mev_bot_contract(block_number=block_number, execution_node=execution_node):
            return await _mev_return_value(block_number=block_number, mev_recipient=fee_recipient, execution_node=execution_node)

        if await _contains_tx_from_builder_to_fee_recipient(block_number=block_number, fee_recipient=fee_recipient, execution_node=execution_node):
            return await _mev_return_value(block_number=block_number, mev_recipient=fee_recipient, execution_node=execution_node)

        if fee_recipient in (
                "0x7d00a2bc1370b9005eb100004da500924600a2e1",
        ) and last_tx.from_ == "0xac7ea48093b61f2e217b9d077d69d9d55ca1b106":
            # a2e1 smart contract, somehow distributes the earnings...
            # Right now I assume it contains MEV and the
            # contract is the MEV recipient
            return await _mev_return_value(block_number=block_number, mev_recipient=fee_recipient,
                                           execution_node=execution_node)

        raise ManualInspectionRequired(f"fee_rec_bal_change != block_priority_tx_fees in block {block_number}")

    # No MEV detected
    return BlockRewardValue(
        block_priority_tx_fees=block_priority_tx_fees,
        contains_mev=False,
        mev_recipient=None,
        mev_recipient_balance_change=None,
    )
