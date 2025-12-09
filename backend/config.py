"""Конфигурация приложения."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    # Neo4j / Graphiti
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""  # Должен быть установлен через NEO4J_PASSWORD env

    # Redis
    redis_url: str = "redis://redis:6379"

    # OpenAI
    openai_api_key: str = ""
    llm_model: str = "gpt-5-mini"  # Переключено с nano на mini
    llm_requests_per_minute: int = 60

    # User identity
    user_id: str = "sergey"
    user_name: str = "Сергей"
    agent_name: str = "Марк"

    # Memory settings
    l0_max_size: int = 500
    l1_ttl_days: int = 30
    consolidation_threshold: float = 0.8


@lru_cache
def get_settings() -> Settings:
    return Settings()
