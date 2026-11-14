from dataclasses import dataclass
from typing import Protocol


class LLMError(Exception): ...


class RateLimited(LLMError):
    def __init__(self, msg: str = "rate limited", retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


class TransientError(LLMError): ...  # 5xx, timeouts, network, malformed body


class EmptyResponse(TransientError): ...


class PermanentError(LLMError): ...  # bad key, bad model name, other 4xx


class CacheMiss(LLMError): ...


class AllProvidersFailed(LLMError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors) or "no providers available")
        self.errors = errors


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    latency_s: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    cached: bool = False


class Provider(Protocol):
    name: str
    model: str

    def complete(
        self,
        messages: list[dict],
        *,
        json_mode: bool = True,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> Completion: ...
