import logging

from providers.beacon_node import BlockRewardData
from providers.execution_node import ExecutionNode
from providers.mev_builders import MEV_BUILDERS, KNOWN_FEE_RECIPIENTS_MEV, KNOWN_EXTRA_DATA_FIELDS_MEV, MevPayoutType


EXECUTION_NODE = ExecutionNode()
logger = logging.getLogger(__name__)


async def get_block_reward_value(block_reward_data: BlockRewardData) -> tuple[int, bool]:
    block_contains_mev = False

    miner_data = await EXECUTION_NODE.get_miner_data(block_number=block_reward_data.block_number)
    # The coinbase should be equal to the fee recipient for the block
    assert miner_data.coinbase == block_reward_data.fee_recipient, \
        f"Coinbase {miner_data.coinbase} != fee recipient {block_reward_data.fee_recipient}, " \
        f"block number {block_reward_data.block_number}"

    try:
        block_extra_data_decoded = bytes.fromhex(miner_data.extra_data[2:]).decode(errors="ignore") if len(miner_data.extra_data) > 2 else None
    except UnicodeDecodeError:
        block_extra_data_decoded = None

    if block_reward_data.fee_recipient in KNOWN_FEE_RECIPIENTS_MEV and block_extra_data_decoded not in KNOWN_EXTRA_DATA_FIELDS_MEV:
        raise ValueError(f"MEV block with unexpected block extra data"
                         f" - {repr(block_extra_data_decoded)} - in {block_reward_data.block_number}")

    # Most builders set themselves as fee recipient and send MEV to proposer in a tx
    if block_reward_data.fee_recipient in (
            b.fee_recipient_address for b in MEV_BUILDERS if b.payout_type == MevPayoutType.LAST_TX
    ):
        # Definitely a block that contains MEV
        builder = next(b for b in MEV_BUILDERS if b.fee_recipient_address == block_reward_data.fee_recipient)
        tx_count = await EXECUTION_NODE.get_block_tx_count(block_number=block_reward_data.block_number)
        last_tx = await EXECUTION_NODE.get_tx_data(block_number=block_reward_data.block_number,
                                                   tx_index=tx_count - 1)

        assert last_tx.from_ == block_reward_data.fee_recipient
        assert block_extra_data_decoded in builder.extra_data_values,\
            f"Unexpected block extra data"\
            f" - {block_extra_data_decoded} for builder {builder.name} in {block_reward_data.block_number}"

        return last_tx.value, True

    # Fee recipient is not a known MEV builder
    # This could still be MEV but built by Manifold/other builders who do not override
    # the fee recipient and therefore don't have to make a transaction to pay out rewards

    # Check for possible Relayooor-type payout
    if block_extra_data_decoded in (extra_data for b in MEV_BUILDERS if b.payout_type == MevPayoutType.RELAYOOOR for extra_data in b.extra_data_values):
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

    # Process other types of MEV payout
    proposer_reward = 0

    if block_extra_data_decoded is not None and block_extra_data_decoded in (extra_data for b in MEV_BUILDERS if b.payout_type == MevPayoutType.DIRECT for extra_data in b.extra_data_values):
        block_contains_mev = True
    elif block_extra_data_decoded is not None and block_extra_data_decoded in KNOWN_EXTRA_DATA_FIELDS_MEV:
        raise ValueError(
            f"Known MEV extra data field {block_extra_data_decoded}, unknown fee recipient {block_reward_data.fee_recipient} "
            f"in block {block_reward_data.block_number}"
        )

    # TODO Check last tx, if from fee recipient to an address with non0 value, it may be a new builder
    # Check if we are missing a builder that uses the LAST_TX payout type
    tx_count = await EXECUTION_NODE.get_block_tx_count(block_number=block_reward_data.block_number)
    if tx_count > 0:
        last_tx = await EXECUTION_NODE.get_tx_data(block_number=block_reward_data.block_number,
                                                   tx_index=tx_count - 1)
        if last_tx.from_ == block_reward_data.fee_recipient and last_tx.value > 0:
            logger.warning("Missed a builder? Assuming MEV because of last tx in block.\n"
                           f"Block number: {block_reward_data.block_number}, "
                           f"Extra data: {repr(block_extra_data_decoded)}, "
                           f"Fee recipient: {block_reward_data.fee_recipient}")
            return last_tx.value, True

    burnt_tx_fees = await EXECUTION_NODE.get_burnt_tx_fees_for_block(block_number=block_reward_data.block_number)
    logger.debug(f"Proposer reward: {miner_data.tx_fee} - {burnt_tx_fees}")
    proposer_reward += miner_data.tx_fee - burnt_tx_fees

    return proposer_reward, block_contains_mev
