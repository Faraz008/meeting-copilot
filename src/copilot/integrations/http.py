import time

import httpx

from copilot.llm.base import PermanentError, RateLimited, TransientError
from copilot.llm.openai_compat import _retry_after
from copilot.llm.ratelimit import TokenBucket
from copilot.llm.retry import with_retries


class NotFound(PermanentError): ...


class AuthError(PermanentError): ...


class BadRequest(PermanentError):
    def __init__(self, msg: str, body: str | None = None):
        super().__init__(msg)
        self.body = body or ""


class ApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        headers: dict | None = None,
        auth=None,
        rpm: float = 120,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
        sleep=time.sleep,
    ):
        self.base, self.headers, self.auth, self.sleep = (
            base_url.rstrip("/"),
            headers or {},
            auth,
            sleep,
        )
        self.client = client or httpx.Client(timeout=timeout)
        self.limiter = TokenBucket(rpm, sleep=sleep)

    def request(self, method: str, path: str, *, json=None, params=None) -> httpx.Response:
        def once() -> httpx.Response:
            self.limiter.acquire()
            try:
                r = self.client.request(
                    method,
                    f"{self.base}{path}",
                    json=json,
                    params=params,
                    headers=self.headers,
                    auth=self.auth,
                )
            except httpx.TimeoutException as e:
                raise TransientError("timeout") from e
            except httpx.TransportError as e:
                raise TransientError(f"network: {type(e).__name__}") from e
            sc = r.status_code
            if sc == 429:
                raise RateLimited(retry_after=_retry_after(r))
            if sc >= 500:
                raise TransientError(f"http {sc}")
            if sc in (401, 403):
                raise AuthError(
                    f"http {sc}: check the credentials and the permissions or sharing settings"
                )
            if sc == 404:
                raise NotFound("http 404")
            if sc >= 400:
                raise BadRequest(f"http {sc}", r.text[:1500])
            return r

        return with_retries(once, sleep=self.sleep)
