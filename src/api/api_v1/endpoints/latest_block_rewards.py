import datetime
import json
import logging

import pytz
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from fastapi_plugins import depends_redis
from pydantic import parse_raw_as
from pydantic.json import pydantic_encoder
from redis import Redis

from api.api_v1.models import ExecLayerBlockReward
from providers.beacon_node import BeaconNode, depends_beacon_node
from providers.db_provider import DbProvider, depends_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/latest_block_rewards",
    response_model=list[ExecLayerBlockReward],
    summary="Returns the most recent block rewards from the database.",
)
async def latest_block_rewards(
    cache: Redis = Depends(depends_redis),
    db_provider: DbProvider = Depends(depends_db),
    beacon_node: BeaconNode = Depends(depends_beacon_node),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=100, minutes=1)),
):
    cache_key = "latest_block_rewards"

    # Try to get data from cache first
    data_cache = await cache.get(cache_key)
    if data_cache:
        return parse_raw_as(list[ExecLayerBlockReward], data_cache)

    max_slot = beacon_node.slot_for_datetime(datetime.datetime.now(tz=pytz.UTC))

    block_rewards = db_provider.block_rewards(min_slot=0, max_slot=max_slot, proposer_indexes=[], limit=50)

    exec_layer_block_rewards = []
    for br in block_rewards:
        if br.proposer_index is None:
            continue

        reward_value = br.mev_reward_value_wei if br.mev else br.priority_fees_wei
        br_reward_eth = int(reward_value) / 1e18

        exec_layer_block_rewards.append(
            ExecLayerBlockReward(
                date=beacon_node.datetime_for_slot(br.slot, pytz.UTC),
                reward=br_reward_eth,
                slot=br.slot,
                mev=br.mev,
            )
        )

    await cache.set(cache_key, json.dumps(exec_layer_block_rewards, default=pydantic_encoder), ex=60)

    return exec_layer_block_rewards
