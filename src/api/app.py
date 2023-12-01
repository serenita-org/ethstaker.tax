import os
import logging

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_plugins import redis_plugin, RedisSettings
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette_exporter import PrometheusMiddleware, handle_metrics

from shared.setup_logging import setup_logging
from providers.beacon_node import beacon_node_plugin
from providers.coin_gecko import coin_gecko_plugin
from providers.db_provider import db_plugin
from api.rate_limiting import rate_limit_per_path_identifier
from api.api_v1 import api_v1_router, openapi_tags_v1
from api.api_v2 import api_v2_router


app = FastAPI(
    title="ethstaker.tax API",
    description="The API that is used by the frontend. Feel free to use it, "
    "but the spec is not completely stable yet, there may still be breaking "
    "changes in the next few months while it is being stabilized. If you'd "
    "like to use it as part of a project, please get in touch for more details.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    openapi_tags=openapi_tags_v1,
)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],  # Allows all headers
    allow_origins=[
        "https://ethstaker.tax",
        "https://serenita.io",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
)
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
app.include_router(api_v2_router)


@app.get("/api/echo", include_in_schema=False)
async def echo(
    request: Request,
    rate_limiter: RateLimiter = Depends(RateLimiter(times=1, minutes=1)),
):
    return f"Headers: {request.headers}"


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging()

    await redis_plugin.init_app(app, config=RedisSettings(
        redis_host=os.getenv("REDIS_HOST"),
        redis_port=os.getenv("REDIS_PORT"),
    ))
    await redis_plugin.init()

    await beacon_node_plugin.init_app(app)
    await coin_gecko_plugin.init_app(app)
    await db_plugin.init_app(app)

    redis = await app.state.REDIS()
    await FastAPILimiter.init(
        redis, prefix="fastapi-limiter-api", identifier=rate_limit_per_path_identifier
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await redis_plugin.terminate()
