import asyncio
import datetime
import logging
import os
from collections import namedtuple

from providers.http_client_w_backoff import AsyncClientWithBackoff
from prometheus_client.metrics import Counter

logger = logging.getLogger(__name__)

EXEC_NODE_REQUEST_COUNT = Counter("exec_node_request_count",
                                  "Count of requests made to the execution node",
                                  labelnames=("endpoint", "function_name"))


MinerData = namedtuple("MinerData", ["tx_fee", "coinbase", "extra_data"])
TxData = namedtuple("TxData", ["from_", "to", "value"])


_ROCKETPOOL_BOND_REDUCER_ADDRESS = "0xf7aB34C74c02407ed653Ac9128731947187575C0"


class ExecutionNode:
    HEADERS = {
        "Content-Type": "application/json"
    }

    def _get_http_client(self) -> AsyncClientWithBackoff:
        return AsyncClientWithBackoff(
            timeout=int(os.getenv("EXECUTION_NODE_RESPONSE_TIMEOUT")),
        )

    def _get_base_url(self) -> str:
        return f"http://{os.getenv('EXECUTION_NODE_HOST')}:{os.getenv('EXECUTION_NODE_PORT')}"

    async def _wait_for_infura_rate_limiter(self) -> None:
        return
        # Archive node = 1req/s
        time_since_last_req = (datetime.datetime.now() - self._last_infura_request_dt).total_seconds()
        if time_since_last_req < 1:
            await asyncio.sleep(1 - time_since_last_req)
        self._last_infura_request_dt = datetime.datetime.now()

    def __init__(self) -> None:
        self.BASE_URL = self._get_base_url()
        self.client = self._get_http_client()
        self._last_infura_request_dt = datetime.datetime.now()
        self._get_miner_data_rpc_supported = True

    async def get_block_number(self) -> int:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_blockNumber", "get_block_number").inc()

        return int(resp.json()["result"], base=16)

    async def eth_call(self, params: list[dict], use_infura=True) -> int:
        url = f"{self.BASE_URL}"

        if use_infura:
            await self._wait_for_infura_rate_limiter()
            url = os.getenv("EXECUTION_NODE_INFURA_ARCHIVE_URL")

        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": params,
                "id": 1
            }, headers=self.HEADERS)

        EXEC_NODE_REQUEST_COUNT.labels("eth_call", "eth_call").inc()
        return int(resp.json()["result"], base=16)

    async def rocket_pool_get_last_bond_reduction_prev_node_fee(
        self,
        minipool_address: str,
        block_number: int
    ):
        return await self.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": _ROCKETPOOL_BOND_REDUCER_ADDRESS,
                    "data": f"0x179e5279000000000000000000000000{minipool_address[2:]}",
                    "block": hex(block_number),
                }
            ]
        )

    async def rocket_pool_get_last_bond_reduction_prev_bond_value(
        self,
        minipool_address: str,
        block_number: int
    ):
        return await self.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": _ROCKETPOOL_BOND_REDUCER_ADDRESS,
                    "data": f"0x81037f20000000000000000000000000{minipool_address[2:]}",
                    "block": hex(block_number),
                }
            ]
        )

    async def rocket_pool_get_reduce_bond_cancelled(
        self,
        minipool_address: str,
        block_number: int = None
    ):
        return await self.eth_call(
            params=[
                {
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": _ROCKETPOOL_BOND_REDUCER_ADDRESS,
                    "data": f"0x46505530000000000000000000000000{minipool_address[2:]}",
                    "block": hex(block_number) if block_number else "latest",
                }
            ]
        )

    async def get_block_tx_count(self, block_number: int) -> int:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockTransactionCountByNumber",
                "params": [hex(block_number)],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBlockTransactionCountByNumber", "get_block_tx_count").inc()

        return int(resp.json()["result"], base=16)

    async def get_balance(self, address: str, block_number: int, use_infura=False) -> int:
        url = f"{self.BASE_URL}"
        # Use Infura while checking balances in old blocks! (Archive node required)
        if use_infura:
            await self._wait_for_infura_rate_limiter()
            url = os.getenv("EXECUTION_NODE_INFURA_ARCHIVE_URL")
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, hex(block_number)],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBalance", "get_balance").inc()
        result = resp.json()["result"]
        return int(result, base=16)

    async def get_block(self, block_number: int, verbose=False) -> dict:
        """
        verbose - If True it returns the full transaction objects, if False only the hashes of the transactions.
        """
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), verbose],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBlockByNumber", "get_block").inc()

        if resp.json()["result"] is None:
            raise ValueError(f"Received null block for {block_number}")

        return resp.json()["result"]

    async def get_burnt_tx_fees_for_block(self, block_number: int) -> int:
        data = await self.get_block(block_number=block_number)
        base_fee = int(data["baseFeePerGas"], base=16)
        gas_used = int(data["gasUsed"], base=16)
        return base_fee * gas_used

    async def get_block_priority_tx_fees(self, block_number: int, tx_fees_total: int) -> int:
        burnt_tx_fees = await self.get_burnt_tx_fees_for_block(block_number=block_number)
        return tx_fees_total - burnt_tx_fees

    async def get_tx_receipts(self, tx_ids: list[str]) -> list[dict]:
        url = f"{self.BASE_URL}"
        receipts: list[dict] = []

        # There can be a lot of transactions in a block -> divide them into batches
        def batch(iterable, n=1):
            l = len(iterable)
            for idx in range(0, l, n):
                yield iterable[idx:min(idx + n, l)]

        async with self._get_http_client() as client:
            for tx_id_batch in batch(tx_ids, n=50):
                resp = await client.post_w_backoff(url=url, json=[{
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_id],
                    "id": 1
                } for tx_id in tx_id_batch], headers=self.HEADERS)

                if resp.status_code != 200:
                    raise ValueError(f"Non-200 status code - {resp.text}"
                                     f" for tx_id_batch: {tx_id_batch}")
                receipts.extend([data["result"] for data in resp.json()])
                EXEC_NODE_REQUEST_COUNT.labels("eth_getTransactionReceipt", "get_tx_receipt").inc()

        return receipts

    async def get_tx_fee(self, tx_hash: str) -> int:
        tx_receipt = (await self.get_tx_receipts([tx_hash]))[0]
        return int(tx_receipt["gasUsed"], base=16) * int(tx_receipt["effectiveGasPrice"], base=16)

    async def get_logs(self, address: str, block_number_range: tuple[int, int], topics: list[str], use_infura=True) -> list[dict]:
        url = f"{self.BASE_URL}"
        # Use Infura while checking balances in old blocks! (Archive node required)
        if use_infura:
            await self._wait_for_infura_rate_limiter()
            url = os.getenv("EXECUTION_NODE_INFURA_ARCHIVE_URL")
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [
                    {
                        "address": address,
                        "fromBlock": hex(block_number_range[0]),
                        "toBlock": hex(block_number_range[1]),
                        "topics": topics,
                    }
                ],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getLogs", "get_logs").inc()

        return resp.json()["result"]

    async def get_tx_data(self, block_number: int, tx_index: int) -> TxData:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByBlockNumberAndIndex",
                "params": [hex(block_number), hex(tx_index)],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getTransactionByBlockNumberAndIndex", "get_tx_data").inc()

        result = resp.json()["result"]

        return TxData(
            from_=result["from"],
            to=result["to"],
            value=int(result["value"], base=16),
        )

    async def get_miner_data(self, block_number: int) -> MinerData:
        """
        Note - this RPC method is only available in Besu. That sucks, can we work around that somehow?

        -> extra data and coinbase(miner) is returned by eth_getBlockByHash / eth_getBlockByNumber
        -> transactionFee = in Wei, is sum of upfront cost - refund amount for all transactions.
        ---> use cumulativeGasUsed as returned by block's last tx receipt
        """
        url = f"{self.BASE_URL}"
        if self._get_miner_data_rpc_supported:
            async with self._get_http_client() as client:
                resp = await client.post_w_backoff(url=url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getMinerDataByBlockNumber",
                    "params": [hex(block_number)],
                    "id": 1
                }, headers=self.HEADERS)
            if "the method eth_getMinerDataByBlockNumber does not exist" in resp.text:
                self._get_miner_data_rpc_supported = False
            else:
                EXEC_NODE_REQUEST_COUNT.labels("eth_getMinerDataByBlockNumber", "get_miner_data").inc()

                data = resp.json()["result"]
                return MinerData(
                    tx_fee=int(data["transactionFee"], base=16),
                    coinbase=data["coinbase"],
                    extra_data=data["extraData"],
                )
        # Execution client doesn't support this RPC method (only Besu does)...
        # Retrieve the data separately
        # extra data and coinbase
        self._get_miner_data_rpc_supported = False
        block = await self.get_block(block_number=block_number)
        # gas actually used during block execution
        tx_fee = 0
        tx_count = len(block["transactions"])
        if tx_count > 0:
            tx_receipts = await self.get_tx_receipts(block["transactions"])
            for receipt in tx_receipts:
                tx_fee += int(receipt["gasUsed"], base=16) * int(receipt["effectiveGasPrice"], base=16)
        return MinerData(
            tx_fee=tx_fee,
            coinbase=block["miner"],
            extra_data=block["extraData"],
        )
