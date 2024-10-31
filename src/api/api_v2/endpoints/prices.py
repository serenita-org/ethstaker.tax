import datetime
import logging

import pytz
from redis import Redis
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter

from api.api_v2.models import PricesResponse, PriceForDate
from providers.beacon_node import GENESIS_DATETIME
from providers.coin_gecko import CoinGecko, depends_coin_gecko, SupportedToken
from providers.db_provider import DbProvider, depends_db

router = APIRouter()
logger = logging.getLogger(__name__)


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
    db_provider: DbProvider = Depends(depends_db),
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
        try:
            response.prices.append(
                PriceForDate(
                    date=date,
                    price=db_provider.close_price_for_date(
                        token=token,
                        currency=currency,
                        date=date,
                    )
                )
            )
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=500,
                                detail=f"Failed to get price for {date}")

    return response
