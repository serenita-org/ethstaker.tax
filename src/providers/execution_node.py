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


class ExecutionNode:
    def _get_http_client(self) -> AsyncClientWithBackoff:
        return AsyncClientWithBackoff(
            timeout=int(os.getenv("EXECUTION_NODE_RESPONSE_TIMEOUT")),
        )

    def _get_base_url(self) -> str:
        return f"http://{os.getenv('EXECUTION_NODE_HOST')}:{os.getenv('EXECUTION_NODE_PORT')}"

    def __init__(self) -> None:
        self.BASE_URL = self._get_base_url()
        self.client = self._get_http_client()

    async def get_block_tx_count(self, block_number: int) -> int:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockTransactionCountByNumber",
                "params": [hex(block_number), True],
                "id": 1
            })
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBlockTransactionCountByNumber", "get_block_tx_count").inc()

        return int(resp.json()["result"], base=16)

    async def get_balance(self, address: str, block_number: int, use_infura=False) -> int:
        url = f"{self.BASE_URL}"
        # Use Infura while checking balances in old blocks! (Archive node required)
        if use_infura:
            url = os.getenv("EXECUTION_NODE_INFURA_ARCHIVE_URL")
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [address, hex(block_number)],
                "id": 1
            })
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBalance", "get_balance").inc()
        result = resp.json()["result"]
        return int(result, base=16)

    async def get_block(self, block_number: int, verbose=False) -> dict:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), verbose],
                "id": 1
            })
        EXEC_NODE_REQUEST_COUNT.labels("eth_getBlockByNumber", "get_block").inc()

        return resp.json()["result"]

    async def get_burnt_tx_fees_for_block(self, block_number: int) -> int:
        data = await self.get_block(block_number=block_number)
        base_fee = int(data["baseFeePerGas"], base=16)
        gas_used = int(data["gasUsed"], base=16)
        return base_fee * gas_used

    async def get_tx_data(self, block_number: int, tx_index: int) -> TxData:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByBlockNumberAndIndex",
                "params": [hex(block_number), hex(tx_index)],
                "id": 1
            })
        EXEC_NODE_REQUEST_COUNT.labels("eth_getTransactionByBlockNumberAndIndex", "get_tx_data").inc()

        result = resp.json()["result"]

        return TxData(
            from_=result["from"],
            to=result["to"],
            value=int(result["value"], base=16),
        )

    async def get_miner_data(self, block_number: int) -> MinerData:
        url = f"{self.BASE_URL}"
        async with self._get_http_client() as client:
            resp = await client.post_w_backoff(url=url, json={
                "jsonrpc": "2.0",
                "method": "eth_getMinerDataByBlockNumber",
                "params": [hex(block_number), True],
                "id": 1
            })
        EXEC_NODE_REQUEST_COUNT.labels("eth_getMinerDataByBlockNumber", "get_miner_data").inc()

        data = resp.json()["result"]
        return MinerData(
            tx_fee=int(data["transactionFee"], base=16),
            coinbase=data["coinbase"],
            extra_data=data["extraData"],
        )
