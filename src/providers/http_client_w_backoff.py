import logging

from httpx import AsyncClient, Response, ConnectTimeout
import backoff

logger = logging.getLogger(__name__)


class RateLimited(Exception):
    pass


class NonOkStatusCode(Exception):
    pass


class AsyncClientWithBackoff(AsyncClient):
    @backoff.on_exception(backoff.expo, exception=ConnectTimeout, max_time=300, jitter=backoff.full_jitter)
    @backoff.on_exception(backoff.expo, exception=RateLimited, max_time=300, jitter=backoff.full_jitter)
    @backoff.on_exception(backoff.expo, exception=NonOkStatusCode, max_time=60, jitter=backoff.full_jitter)
    async def get_w_backoff(self, **kwargs) -> Response:
        resp = await self.get(**kwargs)

        if resp.status_code == 429:
            # Rate limited
            logger.warning(f"Rate limited while getting {kwargs}. "
                           f"Headers: {resp.headers}")
            raise RateLimited()
        elif resp.status_code == 404:
            # Resource not found at URL
            return resp
        elif resp.status_code != 200:
            # Other error, retry
            logger.warning(f"Non-200 status code while getting {kwargs}. "
                           f"Status code: {resp.status_code}\n"
                           f"Response: {resp.content.decode()}\n"
                           f"Headers: {resp.headers}")
            raise NonOkStatusCode()
        return resp
