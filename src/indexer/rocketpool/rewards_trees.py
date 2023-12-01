import logging

import requests
from prometheus_client import Gauge

from db.db_helpers import session_scope
from db.tables import RocketPoolReward, RocketPoolRewardPeriod

logger = logging.getLogger(__name__)

ROCKET_POOL_REWARD_PERIODS_INDEXED = Gauge(
    "rocket_pool_reward_periods_indexed",
    "Amount of Rocket Pool periods successfully indexed",
)


def index_rewards_trees():
    with session_scope() as session:
        already_indexed_periods = [
            period_idx for period_idx, in
            session.query(RocketPoolRewardPeriod.reward_period_index).all()
        ]
    ROCKET_POOL_REWARD_PERIODS_INDEXED.set(len(already_indexed_periods))

    if already_indexed_periods:
        period_to_index = max(already_indexed_periods) + 1
    else:
        period_to_index = 0

    logger.info(f"Indexing Rocket Pool rewards trees for period {period_to_index}")

    resp = requests.get(
        f"https://github.com/rocket-pool/rewards-trees/raw/main/mainnet/rp-rewards-mainnet-{period_to_index}.json")

    if resp.status_code == 404:
        logger.info(f"404 response for reward period {period_to_index} - returning early")
        return

    if resp.status_code != 200:
        raise ValueError(
            f"Unexpected status code received, {resp.status_code} for {resp.request.url}")

    data = resp.json()

    with session_scope() as session:
        session.add(RocketPoolRewardPeriod(
            reward_period_index=period_to_index,
            reward_period_end_time=data["endTime"],
            rewards=[
                RocketPoolReward(
                    node_address=node_address,
                    reward_collateral_rpl=node_rewards_data["collateralRpl"],
                    reward_smoothing_pool_wei=node_rewards_data["smoothingPoolEth"],
                )
                for node_address, node_rewards_data in data["nodeRewards"].items()
            ]
        ))
