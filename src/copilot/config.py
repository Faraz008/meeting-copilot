from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str | None = None
    groq_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    ollama_model: str | None = None


settings = Settings()
