import datetime
import json
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Any

import pytz
import requests
import zstandard as zstd

from providers.execution_node import ExecutionNode

logger = logging.getLogger(__name__)


_MINIPOOL_MANAGER_ADDRESSES = [
    {
        # v1 deployed on Nov-02-2021
        "address": "0x6293b8abc1f36afb22406be5f96d893072a8cf3a",
    },
    {
        # v2 deployed on Aug-14-2022
        "address": "0x84D11B65E026F7aA08F5497dd3593fb083410B71",
    },
    {
        # v3 deployed on Apr-08-2023
        "address": "0x6d010C43d4e96D74C422f2e27370AF48711B49bF",
    },
    {
        # v4 deployed on Jun-04-2024
        "address": "0x09fbce43e4021a3f69c4599ff00362b83eda501e",
    },
]
_NODE_MANAGER_ADDRESS = "0x89f478e6cc24f052103628f36598d4c14da3d287"
_MINIPOOL_BOND_REDUCER_ADDRESS = "0xf7ab34c74c02407ed653ac9128731947187575c0"
_NODE_DISTRIBUTOR_FACTORY_ADDRESS = "0xe228017f77b3e0785e794e4c0a8a6b935bb4037c"
_STORAGE_ADDRESS = "0x1d8f8f00cfa6758d7bE78336684788Fb0ee0Fa46"
_STORAGE_ROCKET_NODE_MANAGER_KEY = "af00be55c9fb8f543c04e0aa0d70351b880c1bfafffd15b60065a4a50c85ec94"
SMOOTHING_POOL_ADDRESS = "0xd4e96ef8eee8678dbff4d535e033ed1a4f7605b7"


class RocketPoolDataProvider:
    def __init__(self, execution_node: ExecutionNode) -> None:
        self.execution_node = execution_node

    async def get_minipool_node_fee(
            self,
            minipool_address: str,
            block_number: int = None
    ) -> int:
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": minipool_address,
                    "data": "0xe7150134",  # getNodeFee()
                },
                hex(block_number) if block_number else "latest",
            ],
            use_infura=True,
        )
        return int(result, base=16)

    async def get_minipool_bond(
        self,
        minipool_address: str,
        block_number: int = None
    ) -> int:
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": minipool_address,
                    "data": "0x74ca6bf2",  # getNodeDepositBalance()
                },
                hex(block_number) if block_number else "latest",
            ],
            use_infura=True,
        )
        return int(result, base=16)

    async def get_minipool_validator_pubkey(
        self,
        minipool_manager_address: str,
        minipool_address: str,
    ) -> str:
        # getMinipoolPubkey(address _minipoolAddress)
        resp = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": minipool_manager_address,
                    "data": f"0x3eb535e9000000000000000000000000{minipool_address[2:]}",
                },
                "latest"
            ],
            use_infura=True,
        )
        pubkey = resp[130:130 + 96]
        return f"0x{pubkey}"

    async def get_rocket_storage_value(self, key: str, block_number: int = None) -> Any:
        raw = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": _STORAGE_ADDRESS,
                    "data": f"0x21f8a721{key}",  # getAddress(bytes32)
                },
                hex(block_number) if block_number else "latest",
            ],
            use_infura=True,
        )
        return f"0x{raw[26:]}"

    async def get_node_manager_for_block(self, block_number: int):
        # TODO we could hardcode these for block ranges to save some RPC calls, at least for the
        # no-longer-active contract addresses
        return await self.get_rocket_storage_value(key=_STORAGE_ROCKET_NODE_MANAGER_KEY,
                                                   block_number=block_number)

    async def get_node_average_fee(
        self,
        node_address: str,
        block_number: int = None
    ) -> Decimal:
        # Step 1 - get node manager address for current block number
        node_manager_address = await self.get_node_manager_for_block(block_number)

        # Step 2 - get average fee from node manager address
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": node_manager_address,
                    "data": f"0x414dd1d2000000000000000000000000{node_address[2:]}",  # getAverageNodeFee(address)
                },
                hex(block_number) if block_number else "latest",
            ],
            use_infura=True,
        )
        return Decimal(int(result, base=16))

    async def get_node_eth_collateralization_ratio(
        self,
        node_address: str,
        block_number: int = None
    ) -> int:
        # Step 1 - get node staking contract address for current block number
        node_staking_address = await self.get_node_staking_for_block(block_number)

        print(f"Getting collateralization ratio using {node_staking_address}")

        # Step 2 - get collateralization ratio from node staking contract
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": node_staking_address,
                    "data": f"0x97be2143000000000000000000000000{node_address[2:]}",  # getNodeETHCollateralisationRatio(address)
                },
                hex(block_number) if block_number else "latest",
            ],
            use_infura=True,
        )
        return int(result, base=16)

    async def get_node_fee_distributor_share(
        self,
        node_fee_distributor_address: str,
        block_number: int
    ) -> Decimal:
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": node_fee_distributor_address,
                    "data": "0x372d054b",  # getNodeShare()
                },
                hex(block_number)
            ],
            use_infura=True,
        )
        return Decimal(int(result, base=16))

    async def get_minipool_node_deposit_balance(
        self,
        minipool_address: str,
        block_number: int = None
    ) -> Decimal:
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": minipool_address,
                    "data": "0x74ca6bf2",  # getNodeDepositBalance()
                },
                hex(block_number),
            ],
            use_infura=True,
        )
        return Decimal(int(result, base=16))

    async def get_minipool_user_deposit_balance(
        self,
        minipool_address: str,
        block_number: int = None
    ) -> Decimal:
        result = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": minipool_address,
                    "data": "0xe7e04aba",  # getUserDepositBalance()
                },
                hex(block_number),
            ],
            use_infura=True,
        )
        return Decimal(int(result, base=16))

    async def get_reward_snapshots(self, start_at_period: int) -> list:
        reward_snapshots = []
        # RewardSnapshot (
        #   index_topic_1 uint256 rewardIndex,
        #   tuple submission,
        #   uint256 intervalStartTime,
        #   uint256 intervalEndTime,
        #   uint256 time
        # )
        logs = await self.execution_node.get_logs(
            address=None,
            block_number_range=(0, await self.execution_node.get_block_number()),
            topics=[
                "0x61caab0be2a0f10d869a5f437dab4535eb8e9c868b8c1fc68f3e5c10d0cd8f66"],
            use_infura=True,
        )

        for log_item in logs:
            cid = bytes.fromhex(log_item['data'][2+1024:2+1024+128]).rstrip(b"\x00").decode()
            reward_period_index = int(log_item['topics'][1][2:], base=16)

            if reward_period_index < start_at_period:
                continue

            # -> IPFS URL
            ipfs_url = f"https://ipfs.io/ipfs/{cid}/rp-rewards-mainnet-{reward_period_index}.json.zst"
            resp = requests.get(ipfs_url)

            if resp.status_code == 200:
                data = json.loads(zstd.decompress(resp.content).decode())
            else:
                # IPFS request failed... try falling back to GitHub
                logger.warning(f"Received unexpected status code {resp.status_code} for {ipfs_url} - reward index {reward_period_index} ({resp.text})")

                github_url = f"https://github.com/rocket-pool/rewards-trees/raw/main/mainnet/rp-rewards-mainnet-{reward_period_index}.json"
                resp = requests.get(github_url)
                if resp.status_code != 200:
                    raise ValueError(f"Received unexpected status code {resp.status_code} for {github_url} - reward index {reward_period_index} ({resp.text})")
                data = resp.json()

            reward_snapshots.append(
                (reward_period_index, data["nodeRewards"], data["endTime"])
            )

        return reward_snapshots

    async def get_bond_reductions(
        self,
        from_block_number: int,
        to_block_number: int,
    ) -> list:
        logs = await self.execution_node.get_logs(
            address=None,
            block_number_range=(from_block_number, to_block_number),
            topics=["0x90e131460b9acb17565f1719b9ebc49998aec6b07a4743a09b1b700545769eb6"], # BondReduced
            use_infura=True,
        )

        bond_reductions = []
        for log_item in logs:
            minipool_address = log_item["address"]

            prev_bond_amount = int(log_item["data"][2:2+64], base=16)  # don't really need this I guess?
            new_bond_amount = int(log_item["data"][2+64:2+64*2], base=16)
            timestamp = int(log_item["data"][2+64*2:2+64*3], base=16)
            br_event_datetime = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)

            # Fee could have changed too - get new minipool fee
            # new_minipool_fee = await self.get_minipool_node_fee(
            #     minipool_address=minipool_address,
            #     block_number=int(log_item["blockNumber"], base=16)
            # )
            # TODO unhardcode, get dynamically? would be better if this were ever to change
            # but this currently saves a lot of RPC calls when running the RP indexer "freshly"
            # also there should be no other fee possible right now
            new_minipool_fee = 14*1e16  # hardcoded for now

            bond_reductions.append(
                (minipool_address, br_event_datetime, new_bond_amount, new_minipool_fee)
            )

        return bond_reductions

    async def get_minipools(
        self,
        known_node_addresses: list[str],
        known_minipool_addresses: list[str],
        from_block_number: int,
        to_block_number: int,
    ) -> dict[str, list[tuple[str, str, int, int]]]:
        minipools_per_node = defaultdict(list)

        for minipool_manager in _MINIPOOL_MANAGER_ADDRESSES:
            # Get all emitted "MinipoolCreated" events
            events = await self.execution_node.get_logs(
                address=minipool_manager["address"],
                block_number_range=(from_block_number, to_block_number),
                topics=[
                    "0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4"  # MinipoolCreated
                ],
                use_infura=True,
            )

            logger.info(f"Processing {len(events)} events for minipools")
            for minipool_creation_event in events:
                minipool_address = f"0x{minipool_creation_event['topics'][1][26:]}"
                node_address = f"0x{minipool_creation_event['topics'][2][26:]}"

                if minipool_address in known_minipool_addresses:
                    logger.debug(f"Skipping {minipool_address}, already known")
                    continue

                if node_address not in known_node_addresses:
                    logger.warning(f"Skipping {minipool_address}, its node address {node_address} is not known yet")
                    continue

                logger.info(f"Processing minipool {minipool_address}")

                try:
                    # Get the minipool's initial bond and fee values
                    initial_bond_value = await self.get_minipool_bond(
                        minipool_address=minipool_address,
                        block_number=int(minipool_creation_event["blockNumber"],
                                         base=16))

                    if initial_bond_value == 32 * 1e18:
                        # Full Deposit Type - temporary option where NOs opted to provide the full
                        # 32ETH for a minipool when there was no ETH in the deposit pool.
                        # The NO would later get the 2nd 16ETH refunded.
                        # This deposit type is not used at the moment of writing.
                        # For the purposes of ethstaker.tax we can consider this the same way as if the
                        # bond was 16ETH from the beginning, since the NO only earned full rewards
                        # on 16ETH, on the rest they earned only commission-based rewards.
                        # Source - Discord, knoshua: "The latter, full on 16 plus commission, from the point of creation"
                        initial_bond_value = 16 * 1e18

                    initial_fee_value = await self.get_minipool_node_fee(
                        minipool_address=minipool_address,
                        block_number=int(minipool_creation_event["blockNumber"],
                                         base=16))

                    assert initial_fee_value > 0

                    # Get the minipool's associated validator public key
                    pubkey = await self.get_minipool_validator_pubkey(
                        minipool_manager_address=minipool_manager["address"],
                        minipool_address=minipool_address
                    )

                    minipools_per_node[node_address].append((minipool_address, pubkey,
                                                             initial_bond_value,
                                                             initial_fee_value))

                except Exception as e:
                    logger.error(f"Error processing minipool {minipool_address}! Exception: {e}")
        return minipools_per_node

    async def get_nodes(self, known_node_addresses: list[str], block_number: int) -> list[tuple[str, str]]:
        nodes = []

        resp = await self.execution_node.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": _NODE_MANAGER_ADDRESS,
                    "data": f"0x2d7f21d000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
                },
                hex(block_number)
            ],
            use_infura=False,
        )
        node_addresses_string = resp[130:]
        n = 64
        node_addresses = [f"0x{node_addresses_string[i+24:i+n]}" for i in range(0, len(node_addresses_string), n)]

        # Get node fee distributor contract (collects EL rewards)
        for node_address in node_addresses:
            if node_address in known_node_addresses:
                continue

            res = await self.execution_node.eth_call(
                params=[
                    {
                        "from": "0x0000000000000000000000000000000000000000",
                        "to": _NODE_DISTRIBUTOR_FACTORY_ADDRESS,
                        "data": f"0xfa2a5b01000000000000000000000000{node_address[2:]}",
                    },
                    "latest"
                ],
                use_infura=False,
            )
            fee_distributor_address = f"0x{res[26:]}"
            nodes.append((node_address, fee_distributor_address))
        return nodes
