import re
import time

import httpx

from copilot.llm.base import Completion, EmptyResponse, PermanentError, RateLimited, TransientError
from copilot.llm.ratelimit import TokenBucket

THINK = re.compile(r"<think>.*?</think>", re.S)


def _retry_after(r: httpx.Response) -> float | None:
    try:
        return float(r.headers.get("retry-after", ""))
    except ValueError:
        return None


class OpenAICompatProvider:
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        model: str,
        *,
        rpm: float,
        client: httpx.Client | None = None,
        json_mode: bool = True,
        timeout: float = 120.0,
        limiter: TokenBucket | None = None,
    ):
        self.name, self.model = name, model
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.json_mode = json_mode
        self.client = client or httpx.Client(timeout=timeout)
        self.limiter = limiter or TokenBucket(rpm)

    def _payload(self, messages, use_json, temperature, max_tokens) -> dict:
        p = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if use_json:
            p["response_format"] = {"type": "json_object"}
        return p

    def _post(self, payload: dict) -> httpx.Response:
        self.limiter.acquire()
        try:
            return self.client.post(
                f"{self.base_url}/chat/completions", json=payload, headers=self.headers
            )
        except httpx.TimeoutException as e:
            raise TransientError("timeout") from e
        except httpx.TransportError as e:
            raise TransientError(f"network: {type(e).__name__}") from e

    @staticmethod
    def _raise_for_status(r: httpx.Response) -> None:
        if r.status_code == 429:
            raise RateLimited(retry_after=_retry_after(r))
        if r.status_code in (408, 409, 425) or r.status_code >= 500:
            raise TransientError(f"http {r.status_code}")
        if r.status_code >= 400:
            raise PermanentError(f"http {r.status_code}: {r.text[:200]}")

    def complete(self, messages, *, json_mode=True, temperature=0.0, max_tokens=2048) -> Completion:
        use_json = json_mode and self.json_mode
        t0 = time.perf_counter()
        r = self._post(self._payload(messages, use_json, temperature, max_tokens))
        if use_json and r.status_code in (400, 422):
            # some models reject response_format; retry once without it
            r2 = self._post(self._payload(messages, False, temperature, max_tokens))
            if r2.status_code < 400:
                self.json_mode = False
                r = r2
        self._raise_for_status(r)
        try:
            data = r.json()
            if "choices" not in data and "error" in data:  # OpenRouter-style 200 + error body
                code = (
                    (data["error"] or {}).get("code") if isinstance(data["error"], dict) else None
                )
                if code == 429:
                    raise RateLimited(retry_after=None)
                raise TransientError(f"provider error body: {str(data['error'])[:200]}")
            choice = data["choices"][0]
            text = choice["message"].get("content") or ""
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
            raise TransientError("malformed response body") from e
        text = THINK.sub("", text).strip()  # reasoning models leak <think> blocks
        if not text:
            raise EmptyResponse("empty content")
        usage = data.get("usage") or {}
        return Completion(
            text=text,
            provider=self.name,
            model=self.model,
            latency_s=time.perf_counter() - t0,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            finish_reason=choice.get("finish_reason"),
        )
