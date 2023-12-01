from typing import Any, List
import datetime
from collections import namedtuple
import json
import logging

import starlette.requests
from fastapi import FastAPI
from redis import Redis

from providers.http_client_w_backoff import AsyncClientWithBackoff
from prometheus_client import Counter

Price = namedtuple("Price", ["currency", "price"])
logger = logging.getLogger(__name__)
COIN_GECKO_REQUEST_COUNT = Counter("coin_gecko_request_count",
                                   "Count of requests to coingecko.com",
                                   labelnames=("path",))


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
    async def price_for_date(date: datetime.date, token: str, currency_fiat: str, cache: Redis) -> float:
        # Gets the "close" price for the given date.
        # Coingecko returns open price for day,
        # we need to get the close price (=open price for next day)

        # Add 1 day interval to date to get close price
        # for the date
        close_date = date + datetime.timedelta(days=1)

        close_date_str = close_date.strftime("%d-%m-%Y")
        currency_fiat = currency_fiat.lower()

        cache_key = f"prices_{token}_{close_date}"

        # Try to get price from cache first
        price_from_cache = await cache.get(cache_key)
        if price_from_cache:
            logger.debug(f"Got prices for date {close_date_str} from cache")
            prices = json.loads(price_from_cache)
            for c, p in prices:
                if c != currency_fiat:
                    continue
                return p

        # Try to get close price
        url = f"{CoinGecko.BASE_URL}/coins/{token}/history"
        params = {
            "date": close_date_str,
            "localization": "false",
        }
        resp = await AsyncClientWithBackoff(timeout=CoinGecko.RESPONSE_TIMEOUT).get_w_backoff(url=url, params=params)
        COIN_GECKO_REQUEST_COUNT.labels("/coins/ethereum/history").inc()

        data = resp.json()
        prices = []

        # Historical price data may not be available for that date
        if "market_data" not in data.keys():
            raise Exception(
                f"CoinGecko returned no market data for {close_date}: {data},"
                f"not trying current price")

        for c, p in data["market_data"]["current_price"].items():
            prices.append(Price(
                currency=c,
                price=p
            ))

        # Cache prices
        await cache.set(cache_key, json.dumps(prices))

        # Return currency-specific price
        for c, p in prices:
            if c != currency_fiat:
                continue
            return p
        raise Exception(f"Failed to fetch price for {date} in {currency_fiat}")


coin_gecko_plugin = CoinGecko()


async def depends_coin_gecko(request: starlette.requests.Request) -> CoinGecko:
    return await request.app.state.COIN_GECKO()
