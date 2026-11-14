import random
import time

from copilot.llm.base import PermanentError, RateLimited, TransientError


def with_retries(
    fn,
    *,
    max_attempts: int = 4,
    base: float = 1.0,
    cap: float = 30.0,
    max_wait: float = 60.0,
    sleep=time.sleep,
    on_retry=None,
):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except PermanentError:
            raise
        except (RateLimited, TransientError) as e:
            if attempt == max_attempts:
                raise
            if isinstance(e, RateLimited) and e.retry_after is not None:
                if e.retry_after > max_wait:
                    raise  # daily quota exhausted: let the router fall back
                delay = e.retry_after + random.uniform(0, 0.5)
            else:
                d = min(cap, base * 2 ** (attempt - 1))
                delay = d / 2 + random.uniform(0, d / 2)  # "equal jitter"
            if on_retry:
                on_retry(attempt, e, delay)
            sleep(delay)
