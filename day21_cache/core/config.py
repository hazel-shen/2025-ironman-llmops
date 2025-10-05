from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Cache
    CACHE_TTL: int = 3600

    # Embedding Cache
    ENABLE_EMBED_CACHE: bool = True
    EMBED_CACHE_DIM: int = 1536  # 對應 text-embedding-3-small 維度
    EMBED_SIM_THRESHOLD: float = 0.92

    # LLM (OpenAI)
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str | None = None  # 需要走自架 proxy 可設
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    OPENAI_TIMEOUT_SECONDS: int = 60

    # Cost (per 1K tokens / vectors) — 預設值僅供 Demo，請依實際價格調整
    # 你也可設定到 .env 以便不同模型切換
    PROMPT_COST_PER_1K: float = 0.003  # USD / 1K prompt tokens
    COMPLETION_COST_PER_1K: float = 0.006  # USD / 1K completion tokens
    EMBED_COST_PER_1K_TOKENS: float = 0.00002  # USD / 1K tokens for embeddings (估算)

    # Metrics
    METRICS_NAMESPACE: str = "day21_cache"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
