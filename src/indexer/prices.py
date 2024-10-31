"""
Indexes close prices for ETH and RPL.
"""
import datetime
import logging
import asyncio

import pytz
from prometheus_client import start_http_server, Gauge
from sqlalchemy import func

from shared.setup_logging import setup_logging
from providers.coin_gecko import CoinGecko, SupportedToken
from db.tables import Price
from db.db_helpers import session_scope

logger = logging.getLogger(__name__)


LATEST_PRICE_DATA_TIMESTAMP = Gauge(
    "latest_price_data_timestamp",
    "The timestamp of the latest price data",
    labelnames=["token"],
)


async def index_prices():
    today = datetime.date.today()
    with session_scope() as session:
        for token in (SupportedToken.ETH, SupportedToken.ROCKET_POOL):
        # Check for which date we have price data and continue from there
            last_date_with_price_data: datetime.datetime = session.query(
                func.max(Price.timestamp)
            ).filter(Price.token == token.value).one_or_none()[0]

            # Index missing price data
            date_being_processed = last_date_with_price_data.date() + datetime.timedelta(days=1)
            while date_being_processed < today:
                price_timestamp = datetime.datetime.combine(date_being_processed,
                                                            datetime.time(hour=23,
                                                                          minute=59,
                                                                          second=59,
                                                                          tzinfo=pytz.UTC),
                                                            tzinfo=pytz.UTC)
                token_prices = await CoinGecko.token_prices_for_date(
                    token=token,
                    date=date_being_processed,
                )
                for currency, price in token_prices.items():
                    session.add(Price(
                        token=token.value,
                        currency=currency,
                        timestamp=price_timestamp,
                        value=price
                    ))
                session.commit()
                LATEST_PRICE_DATA_TIMESTAMP.labels(token=token.value).set(price_timestamp.timestamp())

                date_being_processed += datetime.timedelta(days=1)


if __name__ == "__main__":
    # Start metrics server
    start_http_server(8000)

    setup_logging()

    from time import sleep

    while True:
        try:
            asyncio.run(index_prices())
        except Exception as e:
            logger.error(f"Error occurred while indexing prices: {e}")
            logger.exception(e)
        logger.info("Sleeping for a while now")
        sleep(600)
