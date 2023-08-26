from fastapi import APIRouter

from api.api_v2.endpoints import rewards

api_v2_router = APIRouter(prefix="/api/v2")
api_v2_router.include_router(rewards.router, tags=["rewards"])
