from fastapi import FastAPI, Request, Depends
from fastapi_plugins import redis_plugin, RedisSettings, depends_redis
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from starlette_exporter import PrometheusMiddleware, handle_metrics
from aioredis import Redis
from pytz import common_timezones

from providers.coin_gecko import CoinGecko
from shared.config import config
from shared.setup_logging import setup_logging

app = FastAPI(openapi_url=None, docs_url=None)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", handle_metrics)

app.mount("/static", StaticFiles(directory="src/frontend/static"), name="static")
templates = Jinja2Templates(directory="src/frontend/templates")
logger = setup_logging(name=__file__)
redis_settings = RedisSettings(
    redis_host=config["redis"]["host"],
    redis_port=config["redis"]["port"],
)


@app.get("/", response_class=HTMLResponse)
async def read_root(
    request: Request,
    cache: Redis = Depends(depends_redis),
    rate_limiter: RateLimiter = Depends(RateLimiter(times=5, seconds=1)),
):
    logger.debug(request.headers)
    currencies = sorted(await CoinGecko.supported_vs_currencies(cache))

    return templates.TemplateResponse(
        "root.html",
        {
            "request": request,
            "common_timezones": common_timezones,
            "currencies": currencies,
        },
    )


@app.on_event("startup")
async def on_startup() -> None:
    await redis_plugin.init_app(app, config=redis_settings)
    await redis_plugin.init()
    redis = await app.state.REDIS()
    FastAPILimiter.init(redis, prefix="fastapi-limiter-frontend")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await redis_plugin.terminate()
