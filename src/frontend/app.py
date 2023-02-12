import os

from fastapi import FastAPI, Request, Depends
from fastapi_plugins import redis_plugin, RedisSettings, depends_redis
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette_exporter import PrometheusMiddleware, handle_metrics
from redis import Redis

from providers.coin_gecko import CoinGecko
from shared.setup_logging import setup_logging

app = FastAPI(openapi_url=None, docs_url=None)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")
app.mount("/dist", StaticFiles(directory="src/frontend/dist"), name="dist")
templates = Jinja2Templates(directory="src/frontend/templates")


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=1)),
):
    currencies = sorted(await CoinGecko.supported_vs_currencies(cache))

    return templates.TemplateResponse(
        "rewards.j2",
        {
            "request": request,
            "currencies": currencies,
            "title": "ethstaker.tax",
        },
    )


@app.on_event("startup")
async def on_startup() -> None:
    setup_logging()

    await redis_plugin.init_app(app, config=RedisSettings(
        redis_host=os.getenv("REDIS_HOST"),
        redis_port=os.getenv("REDIS_PORT"),
    ))
    await redis_plugin.init()
    redis = await app.state.REDIS()
    await FastAPILimiter.init(redis, prefix="fastapi-limiter-frontend")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await redis_plugin.terminate()
