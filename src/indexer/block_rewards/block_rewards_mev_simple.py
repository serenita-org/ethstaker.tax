import asyncio
import logging
import re
from collections import namedtuple
from typing import Optional

from providers.beacon_node import SlotProposerData
from providers.db_provider import DbProvider
from providers.execution_node import ExecutionNode
from providers.http_client_w_backoff import NonOkStatusCode
from providers.mev_builders import BUILDER_FEE_RECIPIENTS
from providers.mev_relay import MevRelay
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

# Smart contract forwarder contracts - they immediately forward the reward to another address
# -> cannot compare values
SMART_CONTRACT_FORWARDER_RECIPIENTS = {
    addr.lower() for addr in (
        "0xd6bdD5c289a38ea7bBd57Da9625dba60CeE94879",
        "0x7cd1af7d5299c5bfd4a63291eb5aa57f0ce60024", # Kraken
        "0x6386eD8A268Ce332Db01b992402430968760C86d", # Kraken
    )
}

# Relayooor.wtf relay is down -> cannot get delivered payloads
RELAYOOOR_SLOTS = {
    5246635,
    5954337,
    6021316,
    6071117,
    6126366,
    6130893,
}


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


async def _get_balance_change_adjusted(
        address: str, block_number: int, slot: int,
        block_priority_tx_fees: int, execution_node: ExecutionNode, db_provider: DbProvider
) -> int:
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
    full_block = await execution_node.get_block(block_number, verbose=True)
    if balance_change != block_priority_tx_fees:
        for tx in full_block["transactions"]:
            tx_value = int(tx["value"], base=16)
            if tx["from"] == address:
                # Regular tx from fee recipient
                balance_change += (tx_value + await execution_node.get_tx_fee(tx["hash"]))

    # Account for withdrawal state change
    # (the address may receive withdrawals from the beacon chain)
    balance_change -= sum(1_000_000_000 * w.amount_gwei for w in db_provider.withdrawals_to_address(address, slot=slot) if w.slot == slot)

    # Discard spammy 1 wei transactions
    for tx in full_block["transactions"]:
        _spam_sender_addresses = (
            "0x994e092C13aa50d312643B5caa0273317B664f5d",
            "0x7b9d4D8772b8705dDc7456Daf821c3022DDa0504",
            "0xd840d5f2b38662d8acde3b2beae6ff664f584843",
            "0xc5c9f6dda68422984a06a66a3d1aebd7d979a158",
            "0x35432a10EF42cc7FbF1aFf2e5F3508cb6ff61e44",
            "0x2f448caad2fc3994bd2de4f59114c86fea9ae68f",
            "0x3511f837687Ff7272A39a231Cac1452Ad71141Fa",
            "0x459BbF3c1e0f3829bf91eF4f6d0D865d60ab6B87",
            "0x451D118dBB2AbF9d83cfC04FbdbF3640Fd18d1d3",
            "0x06d9ca334a8a74474e9b6ee31280c494321ae759",
            "0x2f448caad2fc3994bd2de4f59114c86fea9ae68f",
            "0x248475c0e9810a4f558bce4c718ae50a989dd55e",
        )
        tx_value = int(tx["value"], base=16)
        if tx_value != 1:
            continue
        if tx["to"] is None or tx["to"].lower() != address.lower():
            continue
        if tx["from"].lower() in (a.lower() for a in _spam_sender_addresses):
            balance_change -= tx_value

    return balance_change


async def _mev_return_value(
        block_number: int,
        slot: int,
        mev_recipient: str,
        execution_node: ExecutionNode,
        db_provider: DbProvider,
        expected_value: Optional[int],
) -> BlockRewardValue:
    miner_data = await execution_node.get_miner_data(block_number=block_number)
    block_priority_tx_fees = await execution_node.get_block_priority_tx_fees(block_number, miner_data.tx_fee)

    # Check the MEV reward recipient's balance change to determine the MEV reward
    mev_recipient_balance_change = await _get_balance_change_adjusted(
        address=mev_recipient,
        block_number=block_number,
        slot=slot,
        block_priority_tx_fees=block_priority_tx_fees,
        execution_node=execution_node,
        db_provider=db_provider,
    )

    if mev_recipient.lower() in SMART_CONTRACT_FORWARDER_RECIPIENTS:
        # Skip verification - may need to implement logic for every forwarder contract...
        mev_recipient_balance_change = expected_value

    if expected_value is not None:
        # Check if the expected payload value matches what the proposer got
        if mev_recipient_balance_change != expected_value and mev_recipient_balance_change != expected_value + block_priority_tx_fees:
            raise ManualInspectionRequired(f"Proposer balance change {mev_recipient_balance_change} != expected value {expected_value}")

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


async def get_block_reward_value(
        slot_proposer_data: SlotProposerData,
        execution_node: ExecutionNode,
        db_provider: DbProvider,
) -> BlockRewardValue:
    """
    Returns the block's priority tx fees, a bool indicating whether the block contains MEV, the MEV reward recipient
    and the MEV reward value.
    """
    block_number = slot_proposer_data.block_number
    fee_recipient = slot_proposer_data.fee_recipient

    # Check MEV relays for the block
    relays: list[MevRelay] = [
        MevRelay(api_url=api_url)
        for api_url in [
            # see https://ethstaker.cc/mev-relay-list/
            "https://boost-relay.flashbots.net",
            "https://relay-analytics.ultrasound.money",
            "https://agnostic-relay.net",
            "https://bloxroute.max-profit.blxrbdn.com",
            "https://bloxroute.regulated.blxrbdn.com",
            "https://mainnet-relay.securerpc.com",
            "https://relay.wenmerge.com",
            "https://aestus.live",
            "https://titanrelay.xyz",
        ]
    ]

    relay_fetch_payload_tasks = [
        asyncio.create_task(relay.get_payload(block_hash=slot_proposer_data.block_hash)) for relay in relays
    ]

    for coro in asyncio.as_completed(relay_fetch_payload_tasks):
        try:
            payload = await coro
        except NonOkStatusCode as e:
            logger.exception(e)
            continue
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            raise e
        else:
            if payload is not None:
                # MEV! Block hash matches with payload delivered by MEV relay
                for task in relay_fetch_payload_tasks:
                    task.cancel()

                logger.info(f"MEV found in {slot_proposer_data.slot}")
                return await _mev_return_value(
                    block_number=block_number,
                    slot=slot_proposer_data.slot,
                    mev_recipient=payload.proposer_fee_recipient.lower(),
                    execution_node=execution_node,
                    db_provider=db_provider,
                    expected_value=payload.value,
                )

    # No MEV detected based on relays
    miner_data = await execution_node.get_miner_data(block_number=block_number)
    block_extra_data_decoded = bytes.fromhex(miner_data.extra_data[2:]).decode(
        errors="ignore") if len(
        miner_data.extra_data) > 2 else None
    block_priority_tx_fees = await execution_node.get_block_priority_tx_fees(
        block_number, miner_data.tx_fee)

    # Relayooor.wtf relay is down - cannot get data about it, identify based on
    # block extra data
    if block_extra_data_decoded in ("Viva relayooor.wtf",) or slot_proposer_data.slot in RELAYOOOR_SLOTS:
        return await _mev_return_value(
            block_number=block_number,
            slot=slot_proposer_data.slot,
            mev_recipient=fee_recipient,
            execution_node=execution_node,
            db_provider=db_provider,
            expected_value=None,
        )

    # Check if fee recipient's balance change is equal to tx fees
    # -> should be the case when there is no MEV transferred in a tx
    fee_rec_bal_change = await _get_balance_change_adjusted(
        address=fee_recipient, block_number=block_number, slot=slot_proposer_data.slot,
        block_priority_tx_fees=block_priority_tx_fees,
        execution_node=execution_node,
        db_provider=db_provider,
    )
    if fee_rec_bal_change != block_priority_tx_fees or fee_recipient.lower() in BUILDER_FEE_RECIPIENTS:
        # Check for MEV transfer tx in last tx in block (from fee recipient)
        tx_count = await execution_node.get_block_tx_count(block_number=block_number)

        if tx_count > 0:
            last_tx = await execution_node.get_tx_data(block_number=block_number,
                                                       tx_index=tx_count - 1)
            if fee_recipient.lower() in BUILDER_FEE_RECIPIENTS:
                # MEV reward recipient = recipient of last tx in block
                assert last_tx.from_.lower() == fee_recipient.lower(), \
                    f"Expected MEV distribution in last tx, but not found in slot {slot_proposer_data.slot}"

                logger.info(f"MEV found in {slot_proposer_data.slot} - last tx from {last_tx.from_}")
                return await _mev_return_value(block_number=block_number,
                                               slot=slot_proposer_data.slot,
                                               mev_recipient=last_tx.to,
                                               execution_node=execution_node,
                                               db_provider=db_provider,
                                               expected_value=last_tx.value)

            full_block = await execution_node.get_block(block_number, verbose=True)
            if any(
                    tx["to"].lower() in SMART_CONTRACTS_MEV_BOTS for tx in full_block["transactions"] if tx["to"] is not None
            ) and fee_rec_bal_change > block_priority_tx_fees:
                logger.info(f"Fee recipient's balance change > tx fees."
                            f" MEV Bot contract call found in slot {slot_proposer_data.slot}")
                return await _mev_return_value(
                    block_number=block_number,
                    slot=slot_proposer_data.slot,
                    mev_recipient=fee_recipient,
                    execution_node=execution_node,
                    db_provider=db_provider,
                    expected_value=fee_rec_bal_change,
                )

        raise ManualInspectionRequired(
            f"No MEV but fee recipient's balance change ({fee_rec_bal_change})"
            f" not equal to tx fees ({block_priority_tx_fees}) - MEV in {slot_proposer_data.slot}?"
        )

    logger.info(f"No MEV found in {slot_proposer_data.slot}")
    return BlockRewardValue(
        block_priority_tx_fees=block_priority_tx_fees,
        contains_mev=False,
        mev_recipient=None,
        mev_recipient_balance_change=None,
    )

    # TODO remove below
    #  (the old, too expensive and complicated, way of calculation below this line)

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
