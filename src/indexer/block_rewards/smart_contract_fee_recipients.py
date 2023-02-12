import logging

from providers.execution_node import ExecutionNode


logger = logging.getLogger(__name__)


# Common smart contracts
# RocketNodeDistributor - I think there are actually many of these,
#   each operator can set up their own
SMART_CONTRACTS_ROCKETPOOL = (
    "0x83d18f201f7fa5d9602ff1a446b212a2d74f2a28",
    "0x34f4261360d0372176d1d521bf99bf803ced4f6b",
)
SMART_CONTRACT_LIDO_EXEC_LAYER_REWARDS_VAULT = "0x388c818ca8b9251b393131c08a736a67ccb19297"
SMART_CONTRACTS_STAKEFISH = (
    "0x54cd0e6771b6487c721ec620c4de1240d3b07696",
    "0xffee087852cb4898e6c3532e776e68bc68b1143b",
)
SMART_CONTRACTS_KRAKEN = (
    "0xdf50d17985f28c9396a2bc19c8784d838fac958f",
    "0xc9e30152fdb48b6535a1cd4cbbd78349b36afd21",
    "0x036d539e2f1ba71ef2e8dec66ca0ffeae9e15f17",
    "0xbd28c94ff48f9c9c1abbf2691b1c5523c5c7a7a8",
    "0x6b9c23e50d6d5c2854cff4d305f279ad4007ec1e",
    "0xdfa1119cbfd974810276d88ae3e5c2ff360b85e0",
)


async def _get_lido_rewards_distribution_value(block_number: int, execution_node: ExecutionNode) -> int:
    rewards_value = 0

    logs = await execution_node.get_logs("0xae7ab96520de3a18e5e111b5eaab095312d7fe84", block_number, topics=[
        "0xd27f9b0c98bdee27044afa149eadcd2047d6399cb6613a45c5b87e6aca76e6b5",
    ])

    for log_item in logs:
        if log_item["removed"] is True:
            continue
        rewards_value += int(log_item["data"], 16)
    return rewards_value


async def _get_stakefish_rewards_distribution_value(block_number: int, address: str, execution_node: ExecutionNode) -> int:
    rewards_value = 0
    logs = await execution_node.get_logs(address, block_number,
                                         topics=[
                                             "0x7916d844d976746a43b9efc42cf4339ebe50001364a8790d4aec7bbd9a2b599e",
                                         ])

    for log_item in logs:
        if log_item["removed"] is True:
            continue
        rewards_value += int(log_item["data"][66:130], 16)
    return rewards_value


async def _get_kraken_rewards_distribution_value(block_number: int, address: str, execution_node: ExecutionNode) -> int:
    rewards_value = 0
    logs = await execution_node.get_logs(address, block_number,
                                         topics=[
                                             "0x1bb9fb49058794ee4e0f88f3c95c10019922d0b1c6f27da1ee2a98ad19d9b308",
                                         ])

    for log_item in logs:
        if log_item["removed"] is True:
            continue
        rewards_value += int(log_item["data"], 16)
    return rewards_value


async def _get_rocketpool_rewards_distribution_value(block_number: int, address: str, execution_node: ExecutionNode) -> int:
    rewards_value = 0
    logs = await execution_node.get_logs(address, block_number,
                                         topics=[
                                             "0x4c41dd034da8150bccdeba2e484837eb447e0a3840b3e02a54e9bd6eb883210e",
                                         ])

    for log_item in logs:
        if log_item["removed"] is True:
            continue
        rewards_value += int(log_item["data"][66:130], 16)
        rewards_value += int(log_item["data"][130:194], 16)

    return rewards_value
