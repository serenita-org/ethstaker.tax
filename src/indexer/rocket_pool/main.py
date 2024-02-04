import asyncio
import logging
from time import sleep

from prometheus_client import Counter, Gauge, start_http_server

from db.db_helpers import session_scope
from db.tables import RocketPoolRewardPeriod, RocketPoolReward, RocketPoolNode, \
    RocketPoolMinipool, RocketPoolBondReduction
from providers.execution_node import ExecutionNode
from providers.rocket_pool import RocketPoolDataProvider
from shared.setup_logging import setup_logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

ROCKETPOOL_INDEXING_ERRORS = Counter(
    "rocket_pool_indexing_errors",
    "Errors during Rocket Pool data indexing",
)
ROCKET_POOL_LAST_REWARD_PERIOD_INDEXED = Gauge(
    "rocket_pool_last_reward_period_indexed",
    "Last Rocket Pool reward period that was successfully indexed",
)
ROCKET_POOL_NODES = Gauge(
    "rocket_pool_nodes",
    "Number of indexed RP nodes",
)
ROCKET_POOL_MINIPOOLS = Gauge(
    "rocket_pool_minipools",
    "Number of indexed RP minipools",
)
ROCKET_POOL_BOND_REDUCTIONS = Gauge(
    "rocket_pool_bond_reductions",
    "Number of indexed RP bond reductions",
)


LAST_BLOCK_NUMBER_INDEXED = 0


async def run():
    global LAST_BLOCK_NUMBER_INDEXED

    execution_node = ExecutionNode()
    rocket_pool_data = RocketPoolDataProvider(execution_node=execution_node)

    current_exec_block_number = await execution_node.get_block_number()

    with session_scope() as session:
        logger.info("Indexing nodes")
        # Nodes and their respective fee distributor contract addresses
        known_node_addresses = [a for a, in session.query(RocketPoolNode.node_address).all()]
        rp_nodes = await rocket_pool_data.get_nodes(known_node_addresses=known_node_addresses, block_number=current_exec_block_number)
        for node_address, fee_distributor in rp_nodes:
            if node_address in known_node_addresses:
                continue
            session.add(
                RocketPoolNode(
                    node_address=node_address,
                    fee_distributor=fee_distributor,
                )
            )
            known_node_addresses.append(node_address)
        session.commit()
        ROCKET_POOL_NODES.set(len(rp_nodes))

        # Minipools
        # Skip indexing minipools we already have indexed
        indexed_mp_addresses = [a for a, in session.query(RocketPoolMinipool.minipool_address).all()]
        ROCKET_POOL_MINIPOOLS.set(len(indexed_mp_addresses))

        logger.info("Indexing minipools")
        for node_address, minipool_list in (await rocket_pool_data.get_minipools(
            known_node_addresses=known_node_addresses,
            known_minipool_addresses=indexed_mp_addresses,
            block_number=current_exec_block_number
        )).items():
            for minipool_address, pubkey, initial_bond_value, initial_fee_value in minipool_list:
                indexed_mp_addresses.append(minipool_address)
                session.add(
                    RocketPoolMinipool(
                        minipool_address=minipool_address,
                        validator_pubkey=pubkey,
                        initial_bond_value=initial_bond_value,
                        initial_fee_value=initial_fee_value,
                        node_address=node_address,
                    )
                )
        session.commit()

        # Index bond reduction events for every minipool
        logger.info("Indexing bond reductions")
        bond_reductions = await rocket_pool_data.get_bond_reductions(
            from_block_number=LAST_BLOCK_NUMBER_INDEXED,
            to_block_number=current_exec_block_number
        )
        for minipool_address, br_event_datetime, new_bond_amount, new_fee in bond_reductions:
            # TODO tmp remove this check
            if minipool_address not in indexed_mp_addresses:
                continue
            session.merge(
                RocketPoolBondReduction(
                    minipool_address=minipool_address,
                    timestamp=br_event_datetime,
                    new_bond_amount=new_bond_amount,
                    new_fee=new_fee
                )
            )
        session.commit()
        ROCKET_POOL_BOND_REDUCTIONS.set(len(bond_reductions))

        # Rewards trees
        last_indexed_reward_period, = session.query(func.max(RocketPoolRewardPeriod.reward_period_index)).one_or_none()
        if last_indexed_reward_period is not None:
            ROCKET_POOL_LAST_REWARD_PERIOD_INDEXED.set(last_indexed_reward_period)

        logger.info("Indexing reward snapshots")
        new_reward_trees = await rocket_pool_data.get_reward_snapshots(start_at_period=last_indexed_reward_period+1 if last_indexed_reward_period else 0)
        for reward_period_index, node_rewards, period_end_time in new_reward_trees:
            session.add(RocketPoolRewardPeriod(
                reward_period_index=reward_period_index,
                reward_period_end_time=period_end_time,
                rewards=[
                    RocketPoolReward(
                        node_address=node_address,
                        reward_collateral_rpl=node_rewards_data["collateralRpl"],
                        reward_smoothing_pool_wei=node_rewards_data["smoothingPoolEth"],
                    )
                    for node_address, node_rewards_data in node_rewards.items()
                ]
            ))
        session.commit()

    LAST_BLOCK_NUMBER_INDEXED = current_exec_block_number


if __name__ == '__main__':
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    while True:
        try:
            asyncio.run(run())
        except Exception as e:
            logger.error(f"Error occurred while indexing Rocket Pool data: {e}")
            ROCKETPOOL_INDEXING_ERRORS.inc()
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(3600)
