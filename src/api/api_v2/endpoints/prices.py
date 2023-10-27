import datetime
import logging
from enum import Enum

import pytz
from redis import Redis
from fastapi import APIRouter, Depends, Query
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter

from api.api_v2.models import PricesResponse, PriceForDate
from providers.beacon_node import GENESIS_DATETIME
from providers.coin_gecko import CoinGecko, depends_coin_gecko

router = APIRouter()
logger = logging.getLogger(__name__)


class SupportedToken(Enum):
    ETH = "ethereum"
    ROCKET_POOL = "rocket-pool"


@router.get(
    "/prices/{token}",
    response_model=PricesResponse,
)
async def prices(
    token: SupportedToken,
    start_date: datetime.date,
    end_date: datetime.date,
    currency: str = Query(
        ...,
        description="One of the currencies supported by CoinGecko - one of "
        '<a href="https://api.coingecko.com/api/v3/simple/supported_vs_currencies">these</a>.',
        min_length=3,
        max_length=4,
        example="EUR",
    ),
    coin_gecko: CoinGecko = Depends(depends_coin_gecko),
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
):
    # Cap start_date - no sense to have dates before genesis
    start_date = max(start_date, GENESIS_DATETIME.date())

    # Cap end_date - close prices only available until "yesterday"
    today = datetime.datetime.now(tz=pytz.UTC).date()
    end_date = min(end_date, today - datetime.timedelta(days=1))

    range_day_count = (end_date - start_date).days + 1

    response = PricesResponse(
        currency=currency,
        prices=[]
    )
    for day_idx in range(range_day_count):
        date = start_date + datetime.timedelta(days=day_idx)
        response.prices.append(PriceForDate(
            date=date,
            price=round(await coin_gecko.price_for_date(date=date, token=token.value, currency_fiat=currency, cache=cache), 2)
        ))

    return response
