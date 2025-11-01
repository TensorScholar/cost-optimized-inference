from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379"

    # Models
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Batching
    batch_min_size: int = 4
    batch_max_size: int = 64
    batch_max_wait_ms: int = 50

    # Caching
    semantic_cache_enabled: bool = True
    cache_similarity_threshold: float = 0.90

    # Routing
    routing_strategy: str = "cost_optimal"
    cost_weight: float = 0.7

    class Config:
        env_file = ".env"


settings = Settings()


