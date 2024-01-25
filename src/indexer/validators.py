import logging
import asyncio

from prometheus_client import start_http_server

from shared.setup_logging import setup_logging
from providers.beacon_node import BeaconNode
from db.tables import Validator
from db.db_helpers import session_scope

logger = logging.getLogger(__name__)


async def index_validators():
    beacon_node = BeaconNode()

    with session_scope() as session:
        logger.info(f"Indexing validators")
        validators = await beacon_node.get_validators()

        for v in validators:
            session.merge(Validator(
                validator_index=v["index"],
                pubkey=v["validator"]["pubkey"],
            ))


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(index_validators())
        except Exception as e:
            logger.error(f"Error occurred while indexing withdrawals: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(3600)
