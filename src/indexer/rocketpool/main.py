import logging
from time import sleep

import requests
from prometheus_client import Counter, Gauge, start_http_server

from db.db_helpers import session_scope
from db.tables import RocketpoolReward, RocketpoolRewardPeriod
from shared.setup_logging import setup_logging

logger = logging.getLogger(__name__)


ROCKETPOOL_REWARD_PERIODS_INDEXED = Gauge(
    "rocketpool_reward_periods_indexed",
    "Amount of Rocketpool periods successfully indexed",
)

ROCKETPOOL_REWARD_PERIODS_INDEXING_ERRORS = Counter(
    "rocketpool_reward_periods_indexing_errors",
    "Errors during Rocketpool reward period indexing",
)


def run():
    with session_scope() as session:
        already_indexed_periods = [
            period_idx for period_idx, in session.query(RocketpoolRewardPeriod.reward_period_index).all()
        ]
    ROCKETPOOL_REWARD_PERIODS_INDEXED.set(len(already_indexed_periods))

    if already_indexed_periods:
        period_to_index = max(already_indexed_periods) + 1
    else:
        period_to_index = 0

    logger.info(f"Indexing Rocketpool rewards for period {period_to_index}")

    resp = requests.get(f"https://github.com/rocket-pool/rewards-trees/raw/main/mainnet/rp-rewards-mainnet-{period_to_index}.json")

    if resp.status_code == 404:
        logger.info(f"404 response for {period_to_index} - returning early")
        return

    if resp.status_code != 200:
        raise ValueError(f"Unexpected status code received, {resp.status_code} for {resp.request.url}")

    data = resp.json()

    with session_scope() as session:
        for node_address, node_rewards_data in data["nodeRewards"].items():
            session.add(RocketpoolReward(
                node_address=node_address,
                reward_period_index=period_to_index,
                reward_collateral_rpl=node_rewards_data["collateralRpl"],
                reward_smoothing_pool_eth=node_rewards_data["smoothingPoolEth"],
            ))
        session.add(RocketpoolRewardPeriod(
            reward_period_index=period_to_index,
            reward_period_end_time=data["endTime"],
        ))


if __name__ == '__main__':
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    while True:
        try:
            run()
        except Exception as e:
            logger.error(f"Error occurred while indexing Rocketpool rewards: {e}")
            ROCKETPOOL_REWARD_PERIODS_INDEXING_ERRORS.inc()
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(600)
