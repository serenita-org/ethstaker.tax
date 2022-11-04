import json
import logging

from aioredis import Redis
from fastapi import APIRouter, Depends
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter


from api.api_v1.models import IndexedMergeData, ValidatorInclusionData
from indexer.merge import CACHE_KEY_ATTESTATION_DATA, CACHE_KEY_BLOCK_NUMBER, CACHE_KEY_TOTAL_DIFFICULTY, CACHE_KEY_VALIDATOR_INCLUSION


router = APIRouter(prefix="/merge")
logger = logging.getLogger(__name__)


@router.get(
    "/attestation_data",
    response_model=IndexedMergeData,
)
async def attestation_data(
    cache: Redis = Depends(depends_redis),
#    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, seconds=10))
):
    cache_data = await cache.get(CACHE_KEY_ATTESTATION_DATA)
    if cache_data is None:
        return {}
    return json.loads(cache_data)


@router.get(
    "/total_difficulty",
    response_model=int,
)
async def total_difficulty(
    cache: Redis = Depends(depends_redis),
#    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, seconds=5))
):
    return await cache.get(CACHE_KEY_TOTAL_DIFFICULTY)


@router.get(
    "/block_number",
    response_model=int,
)
async def block_number(
    cache: Redis = Depends(depends_redis),
#    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, seconds=5))
):
    return await cache.get(CACHE_KEY_BLOCK_NUMBER)


@router.get(
    "/validator_inclusion",
    response_model=ValidatorInclusionData,
)
async def validator_inclusion(
    cache: Redis = Depends(depends_redis),
#    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, seconds=10))
):
    cache_data = await cache.get(CACHE_KEY_VALIDATOR_INCLUSION)
    if cache_data is None:
        return {}
    return json.loads(cache_data)
