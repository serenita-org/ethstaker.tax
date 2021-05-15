from fastapi import Request

from shared.setup_logging import setup_logging

logger = setup_logging(name=__file__)


async def rate_limit_per_path_identifier(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    path = request.url.path
    return f"{forwarded_for}{path}"
