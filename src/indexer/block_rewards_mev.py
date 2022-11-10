import logging
from typing import Optional

from providers.beacon_node import SlotProposerData
from providers.execution_node import ExecutionNode
from providers.mev_builders import MEV_BUILDERS, BUILDER_FEE_RECIPIENTS, extra_data_contains_common_substring, MevPayoutType


EXECUTION_NODE = ExecutionNode()
logger = logging.getLogger(__name__)


async def _get_balance_change(address: str, block_number: int) -> int:
    return (
        await EXECUTION_NODE.get_balance(
            address=address,
            block_number=block_number,
            use_infura=True,
        )
    ) - (
        await EXECUTION_NODE.get_balance(
            address=address,
            block_number=block_number - 1,
            use_infura=True,
        )
    )


async def _get_block_priority_tx_fees(block_number: int, tx_fee: int) -> int:
    burnt_tx_fees = await EXECUTION_NODE.get_burnt_tx_fees_for_block(block_number=block_number)
    logger.debug(f"Proposer reward: {tx_fee} - {burnt_tx_fees}")
    return tx_fee - burnt_tx_fees


async def get_block_reward_value(slot_proposer_data: SlotProposerData) -> tuple[int, bool, Optional[str], Optional[int]]:
    """
    Returns the fee recipient's block reward, a bool indicating whether the block contains MEV, the MEV reward recipient
    and the MEV reward value.
    """
    block_number, fee_recipient = slot_proposer_data.block_number, slot_proposer_data.fee_recipient

    miner_data = await EXECUTION_NODE.get_miner_data(block_number=block_number)
    # The coinbase should be equal to the fee recipient for the block in PoS
    assert miner_data.coinbase == fee_recipient, \
        f"Coinbase {miner_data.coinbase} != fee recipient {fee_recipient}, " \
        f"block number {block_number}"

    block_priority_fees_reward = await _get_block_priority_tx_fees(block_number, miner_data.tx_fee)
    _NO_MEV_RETURN_VALUE = block_priority_fees_reward, False, None, None

    # Decode extra data in block
    block_extra_data_decoded = bytes.fromhex(miner_data.extra_data[2:]).decode(errors="ignore") if len(miner_data.extra_data) > 2 else None

    # Most builders set themselves as fee recipient and send MEV to proposer in the last tx of the block.
    last_tx = None
    tx_count = await EXECUTION_NODE.get_block_tx_count(block_number=block_number)
    if tx_count > 0:
        last_tx = await EXECUTION_NODE.get_tx_data(block_number=block_number,
                                                   tx_index=tx_count - 1)
    if fee_recipient in BUILDER_FEE_RECIPIENTS:
        builders_w_fee_recip = [b for b in MEV_BUILDERS if b.fee_recipient_address == fee_recipient]
        assert len(builders_w_fee_recip) == 1
        builder = builders_w_fee_recip[0]

        assert block_extra_data_decoded in builder.extra_data_values, \
            f"MEV block with unexpected extra data value" \
            f" - {repr(block_extra_data_decoded)} - in {block_number}"

        if builder.payout_type == MevPayoutType.LAST_TX:
            # Most builders send the MEV to the proposer in the last tx of the block
            assert last_tx.from_ == fee_recipient, \
                f"Builder did not transfer MEV in last tx - " \
                f"{builder.name} in block {block_number}"
            assert block_extra_data_decoded in builder.extra_data_values, \
                f"Unexpected block extra data value" \
                f" - {block_extra_data_decoded} for builder {builder.name} in {block_number}"
            return block_priority_fees_reward, True, last_tx.to, last_tx.value
        elif builder.payout_type == MevPayoutType.CONTRACT_DISTRIBUTOR:
            raise NotImplementedError(builder.payout_type)

    elif last_tx is not None and last_tx.from_ == fee_recipient and last_tx.value > 0:
        # We may not know all builders. If the last tx originates from the fee recipient,
        # we assume it's the transfer of the proposer reward.
        if last_tx.value > 0:
            logger.warning("New builder? Assuming MEV because of last tx in block.\n"
                           f"Block number: {block_number}, "
                           f"Extra data: {repr(block_extra_data_decoded)}, "
                           f"Fee recipient: {fee_recipient}")
            return block_priority_fees_reward, True, last_tx.to, last_tx.value
        else:
            # Tx value is 0, weird?
            raise ValueError(f"Last tx in block from fee recipient with 0 value, weird in {block_number}?")

    # Fee recipient is not a known MEV builder

    # We still consider these blocks to contain MEV if:
    # 1) The block extra data contains some kind of "unique" builder identifier
    extra_data_mev_identifiers = (
        extra_data_value
        for b in MEV_BUILDERS
        for extra_data_value in b.extra_data_values
        if extra_data_value is not None and not extra_data_contains_common_substring(extra_data_value)
    )
    if block_extra_data_decoded in extra_data_mev_identifiers:
        # (Multiple builders may use the same identifier, like the multiple bloXroute builders all use the same one)

        # Check the balance change for the fee recipient between the previous and current block
        # (There are a few different ways the builder could transfer the proposer reward, this captures all of them
        # at a small cost of an unhandled edge case - if the proposer would happen to make/receive a transfer
        # during the same block that they proposed, this would be included...)
        # TODO think if we can avoid the edge case elegantly
        # TODO switch back to local node after catching up
        fee_rec_bal_change = await _get_balance_change(address=fee_recipient, block_number=block_number)

        # If the proposer happened to make a transfer larger than the reward value, the fee recipient's balance
        # change could be negative... this assertion makes sure at least in those cases we check it
        assert fee_rec_bal_change > 0, f"Fee recipient balance change negative in {block_number}"

        return block_priority_fees_reward, True, fee_recipient, fee_rec_bal_change
    elif block_extra_data_decoded is not None and not extra_data_contains_common_substring(block_extra_data_decoded):
        raise ValueError(f"New uncommon extra data value, new builder?\t"
                         f"{block_extra_data_decoded} in {block_number}")

    # If no MEV, the fee recipient's balance change should be equal to the earned tx fees
    fee_rec_bal_change = await _get_balance_change(address=fee_recipient,
                                                   block_number=block_number)

    if fee_rec_bal_change != block_priority_fees_reward:
        # Mismatch, it's either MEV reward transferred via coinbase / internal transactions
        # or the fee recipient made/received a transfer

        # Check all transactions in the block for transfers made/received by the fee recipient
        block = await EXECUTION_NODE.get_block(block_number=block_number, verbose=True)
        transfer_balance_change = 0
        for tx in block["transactions"]:
            tx_value = int(tx["value"], base=16)
            if tx["from"] == fee_recipient:
                tx_receipt = await EXECUTION_NODE.get_tx_receipt(tx["hash"])

                fee = int(tx_receipt["gasUsed"], base=16) * int(tx_receipt["effectiveGasPrice"], base=16)
                transfer_balance_change -= fee + tx_value
            elif tx["to"] == fee_recipient:
                # Check for known fee recipient contract distributors
                # Only if it is the last tx in the block
                tx_count = await EXECUTION_NODE.get_block_tx_count(block_number)
                if int(tx["transactionIndex"], 16) != tx_count - 1:
                    continue

                # Ignore a2e1 contract for now
                if fee_recipient in (
                        "0x7d00a2bc1370b9005eb100004da500924600a2e1",
                ):
                    return _NO_MEV_RETURN_VALUE

                builders = [b for b in MEV_BUILDERS if b.fee_recipient_address == fee_recipient]
                if len(builders) > 0:
                    assert len(builders) == 1
                    builder = builders[0]
                    proposer_address, proposer_reward = builder.proposer_handler(tx=tx, block_number=block_number)
                    # Some verification checks
                    proposer_balance_change = await _get_balance_change(proposer_address, block_number)

                    assert proposer_reward == proposer_balance_change, \
                        f"Proposer reward ({proposer_reward}) != his balance change ({proposer_balance_change})"

                    assert proposer_balance_change < block_priority_fees_reward, \
                        f"Proposer got more ({proposer_balance_change}) than priority fees ({block_priority_fees_reward})?" \
                        f" Block {block_number}"

                    return block_priority_fees_reward, True, proposer_address, proposer_balance_change

                # This could also be a contract interaction if the fee recip is a contract!
                # transfer_balance_change += tx_value
                raise ValueError(f"Tx to fee recipient in block - MEV in block {block_number}?")

        if block_priority_fees_reward + transfer_balance_change != fee_rec_bal_change:
            # If there is still a mismatch, it must be because of internal transactions.

            # Check for interactions with known MEV contracts
            for tx in block["transactions"]:
                if tx["to"] in (
                        "0x7f9a1c279e8bdbb326e453aebb3abba140458362",
                        "0x4083d4ef32631ed3394cc1b11efb03ceebcd2f6c",
                        "0x2f1d79860cf6ea3f4b3b734153b52815773c0638",
                        "0xe3d1b3643ea20e44a09f3d0e57b6c5fef1dfdd2c",
                ):
                    # Someone called one of the MEV contracts, assume MEV
                    # and fee recipient balance change = MEV reward is correct if > 0
                    assert fee_rec_bal_change > 0, \
                        f"MEV contract called, fee recipient balance change < 0 in block {block_number}"
                    return block_priority_fees_reward, True, fee_recipient, fee_rec_bal_change
                elif fee_recipient == "0x388c818ca8b9251b393131c08a736a67ccb19297" and tx["to"] in (
                    "0x442af784a788a5bd6f42a01ebe9f287a871243fb",
                ):
                    # Lido oracle contract - distributes funds from the rewards vault once a day
                    # Check stETH token balance change
                    distributed_rewards_value = 0
                    logs = await EXECUTION_NODE.get_logs("0xae7ab96520de3a18e5e111b5eaab095312d7fe84", block_number, topics=[
                        "0xd27f9b0c98bdee27044afa149eadcd2047d6399cb6613a45c5b87e6aca76e6b5",
                    ])

                    for log_item in logs:
                        if log_item["removed"] is True:
                            continue
                        distributed_rewards_value += int(log_item['data'], 16)
                    assert block_priority_fees_reward == distributed_rewards_value + fee_rec_bal_change, \
                        f"Lido mismatch in {block_number}, MEV?"
                    return _NO_MEV_RETURN_VALUE

            # -> MEV distributor contracts?
            logger.warning(
                f"Fee recipient balance change ({fee_rec_bal_change / 1e18} ETH) is not equal to "
                f"priority fees ({block_priority_fees_reward / 1e18} ETH) "
                f"in block {block_number}"
            )
            raise ValueError(f"MEV in block {block_number}?")

    # No MEV detected
    return _NO_MEV_RETURN_VALUE
