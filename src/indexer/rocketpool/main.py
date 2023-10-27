import logging
from time import sleep

from prometheus_client import Counter, start_http_server

from indexer.rocketpool.minipools import index_minipools
from indexer.rocketpool.rewards_trees import index_rewards_trees
from shared.setup_logging import setup_logging

logger = logging.getLogger(__name__)

ROCKETPOOL_INDEXING_ERRORS = Counter(
    "rocketpool_reward_periods_indexing_errors",
    "Errors during Rocketpool reward period indexing",
)


def run():
    index_minipools()
    index_rewards_trees()


if __name__ == '__main__':
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    while True:
        try:
            run()
        except Exception as e:
            logger.error(f"Error occurred while indexing Rocketpool rewards: {e}")
            ROCKETPOOL_INDEXING_ERRORS.inc()
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(3600)
