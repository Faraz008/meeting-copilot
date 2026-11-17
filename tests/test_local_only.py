import pytest

from copilot.config import settings
from copilot.llm.factory import build_router, is_local


def test_local_only_keeps_only_localhost_providers(monkeypatch):
    for k, v in dict(groq_api_key="k", groq_model="m", ollama_model="qwen").items():
        monkeypatch.setattr(settings, k, v)
    r = build_router(cache_mode="off", local_only=True, log=False)
    assert [p.name for p in r.providers] == ["ollama"]
    assert all(is_local(p.base_url) for p in r.providers)


def test_local_only_without_ollama_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "ollama_model", None)
    monkeypatch.setattr(settings, "groq_api_key", "k")
    monkeypatch.setattr(settings, "groq_model", "m")
    with pytest.raises(RuntimeError, match="Ollama"):
        build_router(cache_mode="off", local_only=True, log=False)
