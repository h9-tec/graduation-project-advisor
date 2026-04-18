from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = "sqlite+aiosqlite:///./grad.db"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment_fast: str = "gpt-4o-mini"
    azure_openai_deployment_smart: str = "gpt-4o"
    llm_provider: Literal["azure", "ollama"] = "azure"

    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model_fast: str = "llama3.2:3b"
    ollama_model_smart: str = "aya:8b"

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    session_cookie_secret: str = Field(default="dev-only-secret-change-in-prod")
    session_cookie_name: str = "grad_sid"

    frontend_origin: str = "http://localhost:3000"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
