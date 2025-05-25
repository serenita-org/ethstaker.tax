import asyncio
import datetime
import logging
import os
from collections import namedtuple
from typing import Any

from providers.http_client_w_backoff import AsyncClientWithBackoff
from prometheus_client.metrics import Counter

logger = logging.getLogger(__name__)

EXEC_NODE_REQUEST_COUNT = Counter("exec_node_request_count",
                                  "Count of requests made to the execution node",
                                  labelnames=("endpoint", "function_name"))


MinerData = namedtuple("MinerData", ["tx_fee", "coinbase", "extra_data"])
TxData = namedtuple("TxData", ["from_", "to", "value"])


class ExecutionNode:
    HEADERS = {
        "Content-Type": "application/json"
    }
    MAX_BLOCK_RANGE = 500   # Alchemy supports up to a 500 block range.

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

    async def eth_call(self, params: list[dict], use_infura=True) -> Any:
        """
        If a block number is specified as part of params, the method will
        return the result as if all transactions in the given block have already
        been executed (e.g. using the state at the *end* of the block).
        Source: https://ethereum.stackexchange.com/a/147308
        """

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
        return_data = resp.json()
        if "result" in return_data:
            return return_data["result"]
        else:
            raise ValueError(f"No result in execution node response! Response: {return_data}")

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

    async def _get_logs(self, address: str | None, block_number_range: tuple[int, int], topics: list[str], use_infura: bool) -> list[dict]:
        from_block = block_number_range[0]
        to_block = block_number_range[1]
        assert from_block <= to_block
        assert to_block - from_block <= (self.MAX_BLOCK_RANGE - 1)

        url = self.BASE_URL
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
                        "address": address if address else None,
                        "fromBlock": hex(from_block),
                        "toBlock": hex(to_block),
                        "topics": topics,
                    }
                ],
                "id": 1
            }, headers=self.HEADERS)
        EXEC_NODE_REQUEST_COUNT.labels("eth_getLogs", "_get_logs").inc()

        resp_data = resp.json()
        if "error" in resp_data:
            if resp_data["error"]["code"] in (-32005, -32602):
                # -32005: query returned more than 10000 results.
                # -32602: >10K logs
                # --> need to split it up, call get_logs recursively with smaller block ranges
                logs = []

                try:
                    # If the response contains a suggested higher end of the block range
                    # use it
                    to_block_limited = int(resp_data["error"]["data"]["to"], 16)
                except KeyError:
                    # Otherwise split request into two halves
                    to_block_limited = to_block - ((to_block - from_block) // 2)

                logs.extend(await self._get_logs(
                    address=address,
                    block_number_range=(
                        from_block, to_block_limited
                    ),
                    topics=topics,
                    use_infura=use_infura,
                ))
                logs.extend(await self._get_logs(
                    address=address,
                    block_number_range=(
                        to_block_limited, to_block
                    ),
                    topics=topics,
                    use_infura=use_infura,
                ))
                return logs
            else:
                raise ValueError(
                    f"Unexpected error: {resp_data['error']} for in get_logs for {address} , {block_number_range}, {topics}, {use_infura}")

        return resp_data["result"]

    async def get_logs(self, address: str | None, block_number_range: tuple[int, int], topics: list[str], use_infura=True) -> list[dict]:
        all_logs = []

        from_block = block_number_range[0]
        to_block = block_number_range[1]

        # Split it up into 500 block ranges (max range for Alchemy RPC)
        for start_block_number in range(from_block, to_block + 1, self.MAX_BLOCK_RANGE):
            end_block_number = min(start_block_number + (self.MAX_BLOCK_RANGE - 1), to_block)

            all_logs.extend(await self._get_logs(
                address=address,
                block_number_range=(start_block_number, end_block_number),
                topics=topics,
                use_infura=use_infura,
            ))

        return all_logs

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
