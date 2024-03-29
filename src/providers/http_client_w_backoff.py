import logging
import time

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
    @backoff.on_exception(backoff.expo, exception=NonOkStatusCode, max_time=30, jitter=backoff.full_jitter)
    async def get_w_backoff(self, **kwargs) -> Response:
        resp = await self.get(**kwargs)

        if resp.status_code == 429:
            # Rate limited
            logger.warning(f"Rate limited while getting {kwargs}. "
                           f"Headers: {resp.headers}")

            retry_after = resp.headers.get("retry-after")
            if retry_after:
                logger.warning(f"Rate limit retry-after {retry_after} -> sleeping")
                time.sleep(float(retry_after) + 1)

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

    @backoff.on_exception(backoff.expo, exception=ConnectTimeout, max_time=300, jitter=backoff.full_jitter)
    @backoff.on_exception(backoff.expo, exception=RateLimited, max_time=300, jitter=backoff.full_jitter)
    @backoff.on_exception(backoff.expo, exception=NonOkStatusCode, max_time=300, jitter=backoff.full_jitter)
    async def post_w_backoff(self, **kwargs) -> Response:
        resp = await self.post(**kwargs)

        if resp.status_code == 429:
            # Rate limited
            logger.warning(f"Rate limited while getting {kwargs}. "
                           f"Headers: {resp.headers}\n"
                           f"Body: {resp.text}")

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
