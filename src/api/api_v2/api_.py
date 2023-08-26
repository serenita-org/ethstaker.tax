from fastapi import APIRouter

from api.api_v2.endpoints import prices, rewards

api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(rewards.router, tags=["rewards"])
api_v2_router.include_router(prices.router, tags=["prices"])
