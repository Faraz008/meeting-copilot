import json

import httpx
import pytest

from copilot.llm.base import (
    AllProvidersFailed,
    CacheMiss,
    EmptyResponse,
    PermanentError,
    RateLimited,
    TransientError,
)
from copilot.llm.cache import CachingProvider
from copilot.llm.openai_compat import OpenAICompatProvider
from copilot.llm.ratelimit import TokenBucket
from copilot.llm.retry import with_retries
from copilot.llm.router import Router
from tests.fakes import FakeProvider

MSG = [{"role": "user", "content": "hi"}]


def body(text='{"a":1}', finish="stop"):
    return {
        "choices": [{"message": {"content": text}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }


def make(handler, **kw):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAICompatProvider("t", "http://x", "k", "m", rpm=60000, client=client, **kw)


def test_ok_and_usage():
    c = make(lambda r: httpx.Response(200, json=body())).complete(MSG)
    assert c.text == '{"a":1}' and c.prompt_tokens == 5 and c.finish_reason == "stop"


def test_429_carries_retry_after():
    p = make(lambda r: httpx.Response(429, headers={"retry-after": "7"}))
    with pytest.raises(RateLimited) as e:
        p.complete(MSG)
    assert e.value.retry_after == 7


def test_5xx_transient_and_401_permanent():
    with pytest.raises(TransientError):
        make(lambda r: httpx.Response(503)).complete(MSG)
    with pytest.raises(PermanentError):
        make(lambda r: httpx.Response(401, text="bad key")).complete(MSG)


def test_empty_and_think_tags():
    with pytest.raises(EmptyResponse):
        make(lambda r: httpx.Response(200, json=body(""))).complete(MSG)
    c = make(lambda r: httpx.Response(200, json=body("<think>hmm</think>{}"))).complete(MSG)
    assert c.text == "{}"


def test_json_mode_fallback():
    def handler(req):
        return (
            httpx.Response(400)
            if "response_format" in json.loads(req.content)
            else httpx.Response(200, json=body())
        )

    p = make(handler)
    assert p.complete(MSG).text and p.json_mode is False


def test_retries_then_ok():
    state, sleeps = {"n": 0}, []

    def fn():
        state["n"] += 1
        if state["n"] < 3:
            raise TransientError("x")
        return "ok"

    assert with_retries(fn, sleep=sleeps.append) == "ok" and len(sleeps) == 2


def test_quota_exhaustion_not_waited_out():
    def fn():
        raise RateLimited(retry_after=3600)

    sleeps = []
    with pytest.raises(RateLimited):
        with_retries(fn, sleep=sleeps.append)
    assert sleeps == []


def test_token_bucket_spacing():
    t = [0.0]
    b = TokenBucket(rpm=60, clock=lambda: t[0], sleep=lambda s: t.__setitem__(0, t[0] + s))
    assert b.acquire() == 0
    assert b.acquire() == pytest.approx(1.0)


def test_router_fallback_and_cooldown():
    a = FakeProvider("a", [RateLimited()] * 4)
    b = FakeProvider("b", ['{"ok":1}'])
    r = Router([a, b], sleep=lambda s: None)
    assert r.complete(MSG).provider == "b"
    assert [p.name for p in r.available()] == ["b"]


def test_router_all_fail():
    r = Router([FakeProvider("a", [PermanentError("bad key")])], sleep=lambda s: None)
    with pytest.raises(AllProvidersFailed):
        r.complete(MSG)


def test_cache_roundtrip_and_replay_miss(tmp_path):
    inner = FakeProvider("a", ['{"x":1}'])
    live = CachingProvider(inner, str(tmp_path), "live")
    assert live.complete(MSG).cached is False
    assert live.complete(MSG).cached is True and len(inner.calls) == 1
    with pytest.raises(CacheMiss):
        CachingProvider(FakeProvider("a", []), str(tmp_path / "empty"), "replay").complete(MSG)
