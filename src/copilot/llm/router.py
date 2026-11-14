import math
import time

from copilot.llm.base import (
    AllProvidersFailed,
    Completion,
    LLMError,
    PermanentError,
    RateLimited,
    TransientError,
)
from copilot.llm.calllog import CallLogger, prompt_hash
from copilot.llm.retry import with_retries


class Router:
    def __init__(
        self,
        providers: list,
        logger: CallLogger | None = None,
        *,
        run_id: str = "adhoc",
        cooldown_s: float = 60.0,
        sleep=time.sleep,
        clock=time.monotonic,
    ):
        self.providers, self.logger, self.run_id = providers, logger, run_id
        self.cooldown_s, self.sleep, self.clock = cooldown_s, sleep, clock
        self._until: dict[str, float] = {}

    def available(self) -> list:
        now = self.clock()
        return [p for p in self.providers if self._until.get(p.name, 0) <= now]

    def wait_until_available(self, max_wait: float = 90.0) -> bool:
        soonest = min((self._until.get(p.name, 0) for p in self.providers), default=math.inf)
        wait = soonest - self.clock()
        if wait <= 0:
            return True
        if wait > max_wait:
            return False
        self.sleep(wait)
        return True

    def _log(
        self,
        p,
        messages,
        purpose,
        attempt,
        outcome,
        error=None,
        comp: Completion | None = None,
    ):
        if not self.logger:
            return
        self.logger.log(
            run_id=self.run_id,
            purpose=purpose,
            provider=p.name,
            model=p.model,
            prompt_hash=prompt_hash(messages),
            attempt=attempt,
            outcome=outcome,
            error=error,
            latency_s=comp.latency_s if comp else None,
            prompt_tokens=comp.prompt_tokens if comp else None,
            completion_tokens=comp.completion_tokens if comp else None,
            cached=int(bool(comp and comp.cached)),
        )

    def call(self, provider, messages, *, purpose: str = "extract", **kw) -> Completion:
        state = {"n": 0}

        def once() -> Completion:
            state["n"] += 1
            try:
                comp = provider.complete(messages, **kw)
            except LLMError as e:
                self._log(provider, messages, purpose, state["n"], type(e).__name__, str(e)[:200])
                raise
            self._log(provider, messages, purpose, state["n"], "ok", comp=comp)
            return comp

        try:
            return with_retries(once, sleep=self.sleep)
        except RateLimited as e:
            self._until[provider.name] = self.clock() + (e.retry_after or self.cooldown_s)
            raise
        except TransientError:
            self._until[provider.name] = self.clock() + self.cooldown_s
            raise
        except PermanentError:
            self._until[provider.name] = math.inf  # bad key / bad model: dead for this run
            raise

    def complete(self, messages, **kw) -> Completion:
        errors: list[str] = []
        for p in self.available():
            try:
                return self.call(p, messages, **kw)
            except LLMError as e:
                errors.append(f"{p.name}: {type(e).__name__}: {e}")
        raise AllProvidersFailed(errors)
