from decimal import Decimal
from enum import Enum
from typing import Any, List
import datetime
from collections import namedtuple
import json
import logging

import starlette.requests
from fastapi import FastAPI
from redis.asyncio import Redis

from providers.http_client_w_backoff import AsyncClientWithBackoff
from prometheus_client import Counter

Price = namedtuple("Price", ["currency", "price"])
logger = logging.getLogger(__name__)
COIN_GECKO_REQUEST_COUNT = Counter("coin_gecko_request_count",
                                   "Count of requests to coingecko.com",
                                   labelnames=("path",))
class SupportedToken(Enum):
    ETH = "ethereum"
    ROCKET_POOL = "rocket-pool"


class CoinGecko:
    BASE_URL = "https://api.coingecko.com/api/v3"
    RESPONSE_TIMEOUT = 120

    async def __call__(self) -> Any:
        return self

    async def init_app(self, app: FastAPI) -> None:
        app.state.COIN_GECKO = self

    @staticmethod
    async def supported_vs_currencies(cache: Redis) -> List[str]:
        cache_key = f"currencies"

        # Try to get price from cache first
        currencies_from_cache = await cache.get(cache_key)
        if currencies_from_cache:
            logger.debug(f"Got supported currencies from cache")
            return json.loads(currencies_from_cache)

        url = f"{CoinGecko.BASE_URL}/simple/supported_vs_currencies"
        resp = await AsyncClientWithBackoff(timeout=CoinGecko.RESPONSE_TIMEOUT).get_w_backoff(url=url)
        COIN_GECKO_REQUEST_COUNT.labels("/simple/supported_vs_currencies").inc()

        data = resp.json()
        currencies = [d.upper() for d in data]

        # Cache them for 7 days
        await cache.set(cache_key, json.dumps(currencies), ex=7*86400)

        return currencies

    @staticmethod
    async def token_prices_for_date(token: SupportedToken, date: datetime.date) -> dict[str, Decimal]:
        # Gets the "close" price for the given date.
        # Coingecko returns open price for day,
        # we need to get the close price (=open price for next day)
        # -> we use the history endpoint

        # Add 1 day interval to date to get close price
        # for the date
        close_date = date + datetime.timedelta(days=1)
        close_date_str = close_date.strftime("%d-%m-%Y")

        url = f"{CoinGecko.BASE_URL}/coins/{token.value}/history"
        params = {
            "date": close_date_str,
            "localization": "false",
        }
        resp = await AsyncClientWithBackoff(
            timeout=CoinGecko.RESPONSE_TIMEOUT).get_w_backoff(url=url, params=params)
        COIN_GECKO_REQUEST_COUNT.labels(f"/coins/{token.value}/history").inc()

        data = resp.json()

        # Historical price data may not be available for that date
        if "market_data" not in data.keys():
            raise Exception(
                f"CoinGecko returned no market data for {close_date}: {data},"
                f"not trying current price")

        token_prices = {}
        for currency, price in data["market_data"]["current_price"].items():
            token_prices[currency] = Decimal(price)
        return token_prices


coin_gecko_plugin = CoinGecko()


async def depends_coin_gecko(request: starlette.requests.Request) -> CoinGecko:
    return await request.app.state.COIN_GECKO()
