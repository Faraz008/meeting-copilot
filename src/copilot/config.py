from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API keys and model names for different providers
    groq_api_key: str | None = None
    groq_model: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    ollama_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None

    # Provider rate limits (requests per minute)
    groq_rpm: float = 21
    openrouter_rpm: float = 14
    ollama_rpm: float = 600
    gemini_rpm: float = 3

    # Provider selection priority
    provider_order: str = "groq,openrouter,ollama,gemini"

    # LLM response caching
    cache_mode: str = "live"  # off | live | replay
    cache_dir: str = "data/llm_cache"

    # API call logging
    calls_db: str = "data/calls.sqlite"

    notion_token: str | None = None
    notion_database_id: str | None = None
    notion_parent_page_id: str | None = None
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None
    jira_issue_type: str = "Task"
    jira_set_priority: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    slack_webhook_url: str | None = None
    public_url: str = "http://localhost:8501"
    roster_path: str = "config/roster.json"
    store_path: str = "data/copilot.sqlite"
    api_key: str | None = None
    hf_token: str | None = None
    demo_mode: bool = False


settings = Settings()
