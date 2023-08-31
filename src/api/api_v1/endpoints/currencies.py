import json
import logging

from pydantic import parse_raw_as
from pydantic.json import pydantic_encoder
from redis import Redis
from fastapi import APIRouter, Depends
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter

from providers.coin_gecko import CoinGecko

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/supported_currencies",
    response_model=list[str],
    summary="Returns all supported currencies",
)
async def supported_currencies(
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
):
    cache_key = "supported_currencies"

    # Try to get data from cache first
    data_cache = await cache.get(cache_key)
    if data_cache:
        return parse_raw_as(list[str], data_cache)

    supported_currencies = sorted(await CoinGecko.supported_vs_currencies(cache))

    await cache.set(cache_key, json.dumps(supported_currencies, default=pydantic_encoder), ex=86_400)

    return supported_currencies
