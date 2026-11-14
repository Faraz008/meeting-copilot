import uuid

from copilot.config import settings
from copilot.llm.cache import CachingProvider
from copilot.llm.calllog import CallLogger
from copilot.llm.openai_compat import OpenAICompatProvider
from copilot.llm.router import Router


def _specs() -> dict:
    s = settings
    return {
        "groq": ("https://api.groq.com/openai/v1", s.groq_api_key, s.groq_model, s.groq_rpm, 120),
        "gemini": (
            "https://generativelanguage.googleapis.com/v1beta/openai",
            s.gemini_api_key,
            s.gemini_model,
            s.gemini_rpm,
            120,
        ),
        "openrouter": (
            "https://openrouter.ai/api/v1",
            s.openrouter_api_key,
            s.openrouter_model,
            s.openrouter_rpm,
            120,
        ),
        "ollama": ("http://localhost:11434/v1", "ollama", s.ollama_model, s.ollama_rpm, 600),
    }


def build_router(
    order: list[str] | None = None,
    cache_mode: str | None = None,
    run_id: str | None = None,
    log: bool = True,
) -> Router:
    mode = cache_mode or settings.cache_mode
    names = order or [n.strip() for n in settings.provider_order.split(",") if n.strip()]
    providers = []
    for n in names:
        base, key, model, rpm, timeout = _specs()[n]
        if mode == "replay":
            key = key or "replay"  # CI has no real keys
        if not key or not model:
            continue
        p = OpenAICompatProvider(n, base, key, model, rpm=rpm, timeout=timeout)
        providers.append(p if mode == "off" else CachingProvider(p, settings.cache_dir, mode))
    if not providers:
        raise RuntimeError("No LLM providers configured. Fill .env (see .env.example).")
    return Router(
        providers,
        CallLogger(settings.calls_db) if log else None,
        run_id=run_id or uuid.uuid4().hex[:8],
    )
