from typing import List, Optional
import logging

from redis import Redis
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_plugins import depends_redis
from fastapi_limiter.depends import RateLimiter
from prometheus_client.metrics import Histogram

from providers.beacon_node import depends_beacon_node, BeaconNode
from api.api_v1.models import ErrorMessage

router = APIRouter()
logger = logging.getLogger(__name__)

VALIDATORS_PER_ETH1_ADDRESS = Histogram(
    "validators_per_eth1_address",
    "Amount of validator indexes returned for an ETH1 address",
    buckets=[0, 1, 2, 3, 4, 5, 10, 20, 50, 100, 1000, 10000, float("inf")],
)


@router.get(
    "/indexes_for_eth1_address",
    response_model=List[int],
    summary="Returns all validator indexes that an ETH1 address deposited funds to.",
)
async def indexes_for_eth1_address(
    eth1_address: str = Query(
        ...,
        description="The ETH1 address used to deposit funds.",
        min_length=42,
        max_length=42,
        regex="^0x[a-fA-F0-9]{40}$",
        example="0xc34eb7e3f34e54646d7cd140bb7c20a466b3e852",
    ),
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
):
    try:
        indexes = await beacon_node.indexes_for_eth1_address(eth1_address, cache)
        VALIDATORS_PER_ETH1_ADDRESS.observe(len(indexes))
        logger.debug(f"Returning indexes {indexes}")
        return indexes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/index_for_publickey",
    response_model=Optional[int],
    summary="Returns the validator index for a validator public key.",
    responses={404: {"model": ErrorMessage}},
)
async def index_for_publickey(
    publickey: str = Query(
        ...,
        description="The validator's public key.",
        min_length=98,
        max_length=98,
        regex="^0x[a-fA-F0-9]{96}$",
        example=r"0xa1d1ad0714035353258038e964ae9675dc0252ee22cea896825c01458e1807bfad2f9969338798548d9858a571f7425c",
    ),
    cache: Redis = Depends(depends_redis),
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, hours=1)),
):
    index = await beacon_node.index_for_publickey(publickey, cache)
    if index is None:
        raise HTTPException(
            status_code=404,
            detail=f"No validator index found for public key {publickey}.",
        )
    return index
