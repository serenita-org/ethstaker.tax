import logging
import os
from typing import Dict, List, Any, Optional, Iterable
import datetime
import json
from collections import namedtuple

import starlette.requests
from fastapi import FastAPI
from httpx import BasicAuth
from redis import Redis
from sqlalchemy import select
import pytz

from db.tables import Balance, Withdrawal, WithdrawalAddress
from db.db_helpers import session_scope
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
                                    labelnames=("endpoint", "function_name"))


SlotProposerData = namedtuple("SlotProposerData", ["slot", "proposer_index", "fee_recipient", "block_number", "block_hash"])


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
    def slot_for_datetime(dt: datetime.datetime) -> int:
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
    def datetime_for_slot(slot: int, timezone: pytz.timezone) -> datetime.datetime:
        utc_dt = GENESIS_DATETIME + datetime.timedelta(seconds=slot * SLOT_TIME)
        localized_dt = utc_dt.astimezone(timezone)

        logger.debug(f"Returning {localized_dt} for slot {slot}")

        return localized_dt

    @staticmethod
    def head_slot() -> int:
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
        await cache.set(cache_key, json.dumps(indexes), ex=1800)

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
        BEACON_NODE_REQUEST_COUNT.labels("/eth/v1/beacon/states/{state_id}/validators/{validator_id}", "index_for_publickey").inc()

        if resp.status_code == 404:
            return None

        data = resp.json()["data"]
        index = data["index"]

        # Cache index
        await cache.set(cache_key, index)

        return index

    async def get_slot_proposer_data(self, slot: int) -> SlotProposerData:
        url = f"{self.BASE_URL}/eth/v2/beacon/blocks/{slot}"

        logger.debug(f"Getting proposer index and fee recipient for slot {slot}")
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACON_NODE_REQUEST_COUNT.labels("/eth/v2/beacon/blocks/{block_id}", "get_slot_proposer_data").inc()

        data = resp.json()
        if "data" not in data.keys():
            # Missed proposals return like this
            if data.get("code") == 404:
                return SlotProposerData(
                    slot=slot,
                    proposer_index=None,
                    fee_recipient=None,
                    block_number=None,
                    block_hash=None,
                )
            else:
                raise ValueError(f"Beacon node returned an error while requesting block for slot {slot}")

        proposer_idx = data["data"]["message"]["proposer_index"]
        fee_recipient = data["data"]["message"]["body"]["execution_payload"]["fee_recipient"]
        block_number = int(data["data"]["message"]["body"]["execution_payload"]["block_number"])
        block_hash = data["data"]["message"]["body"]["execution_payload"]["block_hash"]

        return SlotProposerData(
            slot=slot,
            proposer_index=proposer_idx,
            fee_recipient=fee_recipient,
            block_number=block_number,
            block_hash=block_hash,
        )

    async def activation_slots_for_validators(self, validator_indexes: List[int], cache: Redis) -> Dict[int, Optional[int]]:
        cache_key = f"activation_slots_{validator_indexes}"

        # Try to get activation slots from cache first
        slots_from_cache = await cache.get(cache_key)
        if slots_from_cache:
            logger.debug(f"Got activation slots from cache")
            return {int(k): v for k, v in json.loads(slots_from_cache).items()}

        url = f"{self.BASE_URL}/eth/v1/beacon/states/head/validators"
        params = {"id": ",".join([str(vi) for vi in validator_indexes])}
        logger.debug(f"Getting activation slots for {len(validator_indexes)} indexes")
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url, params=params)
        BEACON_NODE_REQUEST_COUNT.labels("/eth/v1/beacon/states/{state_id}/validators", "activation_slot_for_validator").inc()

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

        # Cache slots for a limited amount of time
        # (validator may become active)
        await cache.set(cache_key, json.dumps(activation_slots), ex=600)

        return activation_slots

    async def head_finalized(self) -> int:
        """Returns the last slot that is finalized"""
        url = f"{self.BASE_URL}/eth/v1/beacon/states/head/finality_checkpoints"
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACON_NODE_REQUEST_COUNT.labels(
            "/eth/v1/beacon/states/head/finality_checkpoint", "head_finalized").inc()

        data = resp.json()["data"]
        finalized_epoch = int(data["finalized"]["epoch"])

        return finalized_epoch * SLOTS_PER_EPOCH + SLOTS_PER_EPOCH - 1

    async def is_slot_finalized(self, slot: int) -> bool:
        if slot <= await self.head_finalized():
            return True
        return False

    async def balances_for_slot(self,
                                slot: int,
                                validator_indexes: Iterable[int] = None,
                                ) -> List[Balance]:
        url = f"{self.BASE_URL}/eth/v1/beacon/states/{slot}/validator_balances"
        params = None
        if validator_indexes:
            params = {"id": ",".join([str(v) for v in validator_indexes])}
        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url, params=params)
        BEACON_NODE_REQUEST_COUNT.labels("/eth/v1/beacon/states/{state_id}/validator_balances", "balances_for_slot").inc()

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

    async def withdrawals_for_slot(self, slot: int) -> list[Withdrawal]:
        url = f"{self.BASE_URL}/eth/v2/beacon/blocks/{slot}"

        async with self._get_http_client() as client:
            resp = await client.get_w_backoff(url=url)
        BEACON_NODE_REQUEST_COUNT.labels(
            "/eth/v2/beacon/blocks/{state_id}",
            "withdrawals_for_slot").inc()

        if resp.status_code == 404:
            # Block not found - missed
            return []

        data = resp.json()["data"]

        withdrawals = []
        with session_scope() as session:
            for w in data["message"]["body"]["execution_payload"]["withdrawals"]:
                address = w["address"]

                # Check if the address is already in DB
                address_in_db = session.execute(
                    select(WithdrawalAddress).where(WithdrawalAddress.address == address)
                ).scalar()
                if address_in_db is None:
                    address_in_db = WithdrawalAddress(address=address)
                    session.add(address_in_db)
                    session.commit()

                w = Withdrawal(
                    slot=slot,
                    validator_index=int(w["validator_index"]),
                    amount_gwei=int(w["amount"]),
                    withdrawal_address_id=address_in_db.id,
                )
                withdrawals.append(w)

        return withdrawals

    async def get_full_state(self, state_id: str) -> dict:
        # Use proxy - add extra 0 to change port to 50510
        url = f"{self.BASE_URL}/eth/v2/debug/beacon/states/{state_id}"

        status_code = None
        while status_code != 200:
            async with self._get_http_client() as client:
                resp = await client.get_w_backoff(url=url)
                status_code = resp.status_code
                if status_code != 200:
                    from time import sleep
                    logger.warning(f"Status code {status_code} received for {state_id} in get_full_state")
                    sleep(1)

        BEACON_NODE_REQUEST_COUNT.labels("/eth/v2/debug/beacon/states/{state_id}", "get_full_state").inc()

        data = resp.json()["data"]

        # Get rid of data that's big and not interesting right now
        keys_to_delete = set(data.keys())
        for ktd in keys_to_delete:
            if ktd not in ("previous_epoch_participation", "current_epoch_participation"):
                data.pop(ktd)

        return data

    async def get_validator_inclusion_global(self, epoch: int) -> dict:
        url = f"{self.BASE_URL}/teku/v1/validator_inclusion/{epoch}/global"

        status_code = None
        while status_code != 200:
            async with self._get_http_client() as client:
                resp = await client.get_w_backoff(url=url)
                status_code = resp.status_code
                if status_code != 200:
                    logger.warning(f"Status code {status_code} received for {epoch} in get_validator_inclusion_global")
        BEACON_NODE_REQUEST_COUNT.labels("/teku/v1/validator_inclusion/{epoch}/global", "get_validator_inclusion_global").inc()

        data = resp.json()["data"]
        return data


beacon_node_plugin = BeaconNode()


async def depends_beacon_node(request: starlette.requests.Request) -> BeaconNode:
    return await request.app.state.BEACON_NODE()
