import uuid
from urllib.parse import urlparse

from copilot.config import settings
from copilot.llm.cache import CachingProvider
from copilot.llm.calllog import CallLogger
from copilot.llm.openai_compat import OpenAICompatProvider
from copilot.llm.router import Router

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def is_local(base_url: str) -> bool:
    return urlparse(base_url).hostname in LOCAL_HOSTS


def _specs() -> dict:
    s = settings

    return {
        "groq": {
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": s.groq_api_key,
            "model": s.groq_model,
            "rpm": s.groq_rpm,
            "timeout": 120,
            "extra_body": {
                "reasoning_effort": "low",
            },
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": s.openrouter_api_key,
            "model": s.openrouter_model,
            "rpm": s.openrouter_rpm,
            "timeout": 120,
            "extra_body": {
                "reasoning": {"effort": "low"},
            },
        },
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama",
            "model": s.ollama_model,
            "rpm": s.ollama_rpm,
            "timeout": 600,
            "extra_body": {"reasoning_effort": "none"},
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "api_key": s.gemini_api_key,
            "model": s.gemini_model,
            "rpm": s.gemini_rpm,
            "timeout": 120,
            "extra_body": {"reasoning_effort": "low"},
        },
    }


def build_router(
    order: list[str] | None = None,
    cache_mode: str | None = None,
    run_id: str | None = None,
    log: bool = True,
    cache_dir: str | None = None,
    max_attempts: int = 4,
    local_only: bool = False,
) -> Router:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    mode = cache_mode or settings.cache_mode

    names = order or [n.strip() for n in settings.provider_order.split(",") if n.strip()]

    specs = _specs()

    # Restrict provider selection to local endpoints when requested.
    if local_only:
        if not settings.ollama_model:
            raise RuntimeError("Ollama is not configured. Set OLLAMA_MODEL and run `ollama serve`.")

        names = ["ollama"]

    providers = []

    for name in names:
        if name not in specs:
            raise ValueError(f"Unknown LLM provider: {name}")

        spec = specs[name]

        key = spec["api_key"]

        if mode == "replay":
            key = key or "replay"

        if not key or not spec["model"]:
            continue

        provider = OpenAICompatProvider(
            name=name,
            base_url=spec["base_url"],
            api_key=key,
            model=spec["model"],
            rpm=spec["rpm"],
            timeout=spec["timeout"],
            extra_body=spec["extra_body"],
        )

        providers.append(
            provider
            if mode == "off"
            else CachingProvider(
                provider,
                cache_dir or settings.cache_dir,
                mode,
            )
        )

    if not providers:
        raise RuntimeError("No LLM providers configured. Fill .env (see .env.example).")

    return Router(
        providers,
        CallLogger(settings.calls_db) if log else None,
        run_id=run_id or uuid.uuid4().hex[:8],
        max_attempts=max_attempts,
    )
