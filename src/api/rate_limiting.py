import logging

from fastapi import Request

logger = logging.getLogger(__name__)


async def rate_limit_per_path_identifier(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    path = request.url.path
    return f"{forwarded_for}{path}"
