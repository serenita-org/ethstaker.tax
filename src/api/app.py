from aioredis import Redis
from fastapi import FastAPI, Depends, Request, Response
from fastapi_plugins import redis_plugin, RedisSettings, depends_redis
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette_exporter import PrometheusMiddleware, handle_metrics

from shared.config import config
from shared.setup_logging import setup_logging
from providers.beacon_node import beacon_node_plugin
from providers.coin_gecko import coin_gecko_plugin
from providers.db_provider import db_plugin
from api.rate_limiting import rate_limit_per_path_identifier
from api.api_v1 import api_v1_router, openapi_tags_v1


app = FastAPI(
    title="ETH2.tax API",
    description="The API that is used by the frontend. Feel free to use it, "
    "but the spec is not completely stable yet, there may still be breaking "
    "changes in the next few months while it is being stabilized. If you'd "
    "like to use it as part of a project, please get in touch for more details.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    openapi_tags=openapi_tags_v1,
)
logger = setup_logging(name=__file__)
app.add_middleware(
    PrometheusMiddleware,
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2.5,
        5,
        10,
        30,
        60,
        120,
        180,
        300,
        float("inf"),
    ],
)
app.add_route("/metrics", handle_metrics)

app.include_router(api_v1_router)

redis_settings = RedisSettings(
    redis_host=config["redis"]["host"],
    redis_port=config["redis"]["port"],
)
db_settings = config["db"]
beacon_node_settings = config["beacon_node"]


@app.get("/api/echo", include_in_schema=False)
async def echo(
    request: Request,
    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, minutes=1)),
):
    return f"Headers: {request.headers}"


@app.get("/api/flush_cache", include_in_schema=False)
async def flush_cache(
    request: Request,
    cache: Redis = Depends(depends_redis),
):
    req_flush_cache_key = request.headers.get("X-Flush-Cache-Key")

    if config["api"]["flush_cache_key"] == req_flush_cache_key:
        await cache.flushall()
        return "OK"
    return Response("Incorrect header value", status_code=403)


@app.on_event("startup")
async def on_startup() -> None:
    await redis_plugin.init_app(app, config=redis_settings)
    await redis_plugin.init()
    await beacon_node_plugin.init_app(app, config=beacon_node_settings)
    await coin_gecko_plugin.init_app(app)
    await db_plugin.init_app(app, config=db_settings)

    redis = await app.state.REDIS()
    FastAPILimiter.init(
        redis, prefix="fastapi-limiter-api", identifier=rate_limit_per_path_identifier
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await redis_plugin.terminate()
