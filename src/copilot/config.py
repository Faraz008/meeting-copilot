from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API keys and model names for different providers
    groq_api_key: str | None = None
    groq_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    ollama_model: str | None = None

    # Provider rate limits (requests per minute)
    groq_rpm: float = 21
    gemini_rpm: float = 3
    openrouter_rpm: float = 14
    ollama_rpm: float = 600

    # Provider selection priority
    provider_order: str = "groq,gemini,openrouter,ollama"

    # LLM response caching
    cache_mode: str = "live"  # off | live | replay
    cache_dir: str = "data/llm_cache"

    # API call logging
    calls_db: str = "data/calls.sqlite"


settings = Settings()
