from fastapi import APIRouter

from api.api_v1.endpoints import indexes, merge, rewards

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(indexes.router, tags=["indexes"])
api_v1_router.include_router(merge.router, tags=["merge"])
api_v1_router.include_router(rewards.router, tags=["rewards"])
