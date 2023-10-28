import datetime
import logging

import pytz
import requests

from db.db_helpers import session_scope
from db.tables import RocketPoolMinipool

logger = logging.getLogger(__name__)


def index_minipools():
    logger.info(f"Indexing minipools")

    resp = requests.get("https://rocketscan.io/api/mainnet/minipools/all")

    data = resp.json()

    with session_scope() as session:
        for minipool_data in data:
            minipool_index = minipool_data["index"]

            validator_data = minipool_data.get("validator")
            if validator_data is None:
                # Minipool not yet linked to a validator
                continue

            bond_reduced = minipool_data.get("bondReduced") is not None

            session.merge(RocketPoolMinipool(
                minipool_index=minipool_index,
                validator_index=validator_data["index"],
                node_address=minipool_data["nodeAddress"],
                node_deposit_balance=minipool_data["nodeDepositBalance"],
                fee=minipool_data["fee"],
                bond_reduced_timestamp=datetime.datetime.fromtimestamp(minipool_data["bondReduced"]["timestamp"], tz=pytz.UTC) if bond_reduced else None,
                bond_pre_reduction_value_wei=minipool_data["bondReduction"]["prevValue"] if bond_reduced else None,
            ))
