import logging
import os
from typing import Dict, List, Any, Optional
import datetime
import json

import starlette.requests
from fastapi import FastAPI
from httpx import BasicAuth
from aioredis import Redis
import pytz

from db.tables import Balance
from providers.http_client_w_backoff import AsyncClientWithBackoff
from prometheus_client.metrics import Counter

GENESIS_DATETIME = datetime.datetime.fromtimestamp(1606824023, tz=pytz.utc)
SLOT_TIME = 12
SLOTS_PER_EPOCH = 32

logger = logging.getLogger(__name__)

BEACONCHAIN_REQUEST_COUNT = Counter("beaconchain_request_count",
                                    "Count of requests to beaconcha.in")
BEACON_NODE_REQUEST_COUNT = Counter("beacon_node_request_count",
                                    "Count of requests made to the beacon node",
                                    labelnames=("path",))


class BeaconNode:
    async def __call__(self) -> Any:
        return self

    @staticmethod
    def _use_infura() -> bool:
        return os.getenv("BEACON_NODE_USE_INFURA", "false") == "true"

    def _get_http_client(self) -> AsyncClientWithBackoff:
        auth = None
        if self._use_infura():
            auth = BasicAuth(username=os.getenv("INFURA_PROJECT_ID"),
                             password=os.getenv("INFURA_SECRET"))
        return AsyncClientWithBackoff(
            auth=auth,
            timeout=int(os.getenv("BEACON_NODE_RESPONSE_TIMEOUT")),
        )

    def _get_base_url(self) -> str:
        if self._use_infura():
            return "https://eth2-beacon-mainnet.infura.io"
        else:
            return f"http://{os.getenv('BEACON_NODE_HOST')}:{os.getenv('BEACON_NODE_PORT')}"

    def __init__(self) -> None:
        self.BASE_URL = self._get_base_url()
        self.client = self._get_http_client()

    async def init_app(self, app: FastAPI) -> None:
        self.BASE_URL = self._get_base_url()
        self.client = self._get_http_client()

        app.state.BEACON_NODE = self

    @staticmethod
    async def slot_for_datetime(dt: datetime.datetime) -> int:
        # Datetime must be localized
        if dt.tzinfo is None:
            raise ValueError("Datetime must be localized")

        utc_dt = dt.astimezone(pytz.utc)

        # Return the genesis slot value if dt is before genesis
        utc_dt = max(utc_dt, GENESIS_DATETIME)

        slot = int((utc_dt - GENESIS_DATETIME).total_seconds() // SLOT_TIME)

        logger.debug(f"Returning slot {slot} for datetime {dt}")

        return slot

    @staticmethod
    async def datetime_for_slot(slot: int, timezone: pytz.timezone) -> datetime.datetime:
        utc_dt = GENESIS_DATETIME + datetime.timedelta(seconds=slot * SLOT_TIME)
        localized_dt = utc_dt.astimezone(timezone)

        logger.debug(f"Returning {localized_dt} for slot {slot}")

        return localized_dt

    @staticmethod
    async def head_slot() -> int:
        now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        head_slot = int((now - GENESIS_DATETIME).total_seconds() // SLOT_TIME)
        return head_slot

    async def indexes_for_eth1_address(self, addr: str, cache: Redis) -> List[int]:
        cache_key = f"indexes_eth1_{addr}"

        # Try to get indexes from cache first
        indexes_from_cache = await cache.get(cache_key)
        if indexes_from_cache:
            logger.debug(f"Got indexes for ETH1 address {addr} from cache")
            return json.loads(indexes_from_cache)

        url = f"https://beaconcha.in/api/v1/validator/eth1/{addr}"
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACONCHAIN_REQUEST_COUNT.inc()

        if resp.status_code != 200:
            raise Exception(
                f"Error while fetching data from beaconcha.in: {resp.content.decode()}"
            )

        data = resp.json()["data"]
        if isinstance(data, list):
            indexes = [validator_data["validatorindex"] for validator_data in data if validator_data["validatorindex"] is not None]
        elif isinstance(data, dict):
            indexes = [data["validatorindex"]]
        else:
            raise ValueError(f"Unexpected data received from beaconcha.in: {data}")

        # Remove duplicates
        indexes = list(set(indexes))

        # Cache indexes for a limited amount of time
        # (person may deposit again)
        await cache.set(cache_key, json.dumps(indexes), expire=1800)

        return indexes

    async def index_for_publickey(self, publickey: str, cache: Redis) -> Optional[int]:
        cache_key = f"index_pubkey_{publickey}"

        # Try to get index from cache first
        index_from_cache = await cache.get(cache_key)
        if index_from_cache:
            logger.debug(f"Got validator index for publickey {publickey} from cache")
            return json.loads(index_from_cache)

        url = f"{self.BASE_URL}/eth/v1/beacon/states/head/validators/{publickey}"
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACON_NODE_REQUEST_COUNT.labels("index_for_publickey").inc()

        if resp.status_code == 404:
            return None

        data = resp.json()["data"]
        index = data["index"]

        # Cache index
        await cache.set(cache_key, index)

        return index

    async def activation_slots_for_validators(self, validator_indexes: List[int], cache: Redis) -> Dict[int, Optional[int]]:
        url = f"{self.BASE_URL}/eth/v1/beacon/states/head/validators"
        params = {"id": ",".join([str(vi) for vi in validator_indexes])}
        logger.debug(f"Getting activation slots for {len(validator_indexes)} indexes")
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url, params=params)
        BEACON_NODE_REQUEST_COUNT.labels("activation_slot_for_validator").inc()

        try:
            data = resp.json()["data"]
        except KeyError:
            raise ValueError(f"Beacon node returned an error while requesting activation_slots")

        activation_slots = {}
        for validator_data in data:
            activation_epoch = int(validator_data["validator"]["activation_epoch"])
            if activation_epoch == (2**64-1):
                # Pending validator
                activation_slots[int(validator_data["index"])] = None
            else:
                activation_slots[int(validator_data["index"])] = int(validator_data["validator"]["activation_epoch"]) * SLOTS_PER_EPOCH

        logger.debug(f"Got activation slots {activation_slots}")

        return activation_slots

    async def is_slot_finalized(self, slot: int) -> bool:
        url = f"{self.BASE_URL}/eth/v1/beacon/states/head/finality_checkpoints"
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACON_NODE_REQUEST_COUNT.labels("is_slot_finalized").inc()

        data = resp.json()["data"]
        finalized_epoch = int(data["finalized"]["epoch"])

        if finalized_epoch * SLOTS_PER_EPOCH < slot:
            return False

        return True

    async def balances_for_slot(self,
                                slot: int,
                                validator_indexes: List[int] = None,
                                ) -> List[Balance]:
        url = f"{self.BASE_URL}/eth/v1/beacon/states/{slot}/validator_balances"
        params = None
        if validator_indexes:
            params = {"id": ",".join([str(v) for v in validator_indexes])}
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url, params=params)
        BEACON_NODE_REQUEST_COUNT.labels("balances_for_slot").inc()

        try:
            data = resp.json()["data"]
        except KeyError:
            # No data available for this slot yet (node may not be synced yet)
            logger.warning("Returning empty balances because of missing data")
            return []

        balances = []
        for d in data:
            balances.append(
                Balance(
                    slot=slot,
                    validator_index=int(d["index"]),
                    balance=int(d["balance"]) / 1_000_000_000,
                )
            )

        return balances


beacon_node_plugin = BeaconNode()


async def depends_beacon_node(request: starlette.requests.Request) -> BeaconNode:
    return await request.app.state.BEACON_NODE()
