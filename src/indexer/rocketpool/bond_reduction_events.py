import datetime
import logging

import pytz

from db.db_helpers import session_scope
from db.tables import RocketPoolBondReduction
from providers.execution_node import ExecutionNode

logger = logging.getLogger(__name__)


async def index_bond_reductions():
    logger.info(f"Indexing bond reductions")
    execution_node = ExecutionNode()

    logs = await execution_node.get_logs(
        address="0xf7aB34C74c02407ed653Ac9128731947187575C0", # RocketMinipoolBondReducer
        block_number_range=(0, await execution_node.get_block_number()),
        topics=["0x9a11f5c1e0617339b2a27c685f7ca5f185506e417a97a849142c8b3c37f325b6"],
    )

    with session_scope() as session:
        now = datetime.datetime.now(tz=pytz.UTC)
        for log_item in logs:
            if log_item["removed"]:
                continue

            bond_reduced_timestamp = datetime.datetime.fromtimestamp(int(log_item['data'][66:], 16), tz=pytz.UTC)
            minipool_address = "0x" + log_item["topics"][1][26:]

            # Check if bond reduction ended up being cancelled
            # Only check within a short timeframe (14 days) after the bond reduction was initiated
            # (that should be the only time the oracles can vote to have the bond reduction cancelled)
            if (now - bond_reduced_timestamp).total_seconds() < 14 * 24 * 3600:
                if await execution_node.rocket_pool_get_reduce_bond_cancelled(minipool_address=minipool_address):
                    bond_reduction_in_db = session.get(RocketPoolBondReduction, (bond_reduced_timestamp, minipool_address))
                    if bond_reduction_in_db:
                        session.delete(bond_reduction_in_db)
                    continue

            # new_bond_value = int(log_item['data'][:66], 16)

            # Check if we already have this bond reduction in DB
            if session.get(RocketPoolBondReduction, (bond_reduced_timestamp, minipool_address)):
                continue

            block_number = int(log_item["blockNumber"], 16)

            prev_node_fee = await execution_node.rocket_pool_get_last_bond_reduction_prev_node_fee(
                minipool_address=minipool_address,
                block_number=block_number,
            )
            if prev_node_fee == 0:
                # Bond reduction not complete yet?
                continue
            prev_bond_value = await execution_node.rocket_pool_get_last_bond_reduction_prev_bond_value(
                minipool_address=minipool_address,
                block_number=block_number + 1,
            )
            if prev_bond_value == 0:
                # Bond reduction not complete yet?
                continue

            session.add(RocketPoolBondReduction(
                minipool_address=minipool_address,
                timestamp=bond_reduced_timestamp,
                prev_node_fee=prev_node_fee,
                prev_bond_value=prev_bond_value,
            ))
