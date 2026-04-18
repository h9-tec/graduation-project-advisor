from __future__ import annotations

import os
from typing import Iterator

import pytest


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in [
        "ENVIRONMENT", "LOG_LEVEL",
        "DATABASE_URL", "REDIS_URL", "QDRANT_URL", "QDRANT_API_KEY",
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT_FAST", "AZURE_OPENAI_DEPLOYMENT_SMART",
        "LLM_PROVIDER", "EMBEDDING_MODEL",
        "OLLAMA_URL", "OLLAMA_MODEL_FAST", "OLLAMA_MODEL_SMART",
        "SESSION_COOKIE_SECRET", "SESSION_COOKIE_NAME",
        "FRONTEND_ORIGIN",
    ]:
        monkeypatch.delenv(key, raising=False)
    yield


def test_defaults_are_local(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.settings import Settings

    s = Settings(_env_file=None)

    assert s.environment == "local"
    assert s.is_local is True
    assert s.log_level == "INFO"
    assert s.llm_provider == "azure"
    assert s.embedding_model.endswith("paraphrase-multilingual-MiniLM-L12-v2")


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")
    monkeypatch.setenv("REDIS_URL", "redis://r:6379/1")
    monkeypatch.setenv("SESSION_COOKIE_SECRET", "s" * 32)

    from core.settings import Settings
    s = Settings(_env_file=None)

    assert s.environment == "production"
    assert s.is_local is False
    assert s.log_level == "WARNING"
    assert str(s.database_url).startswith("postgresql+asyncpg://")
    assert s.session_cookie_secret == "s" * 32


def test_azure_fields_default_to_empty_strings(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.settings import Settings
    s = Settings(_env_file=None)

    assert s.azure_openai_endpoint == ""
    assert s.azure_openai_api_key == ""
    assert s.azure_openai_deployment_fast == "gpt-4o-mini"
    assert s.azure_openai_deployment_smart == "gpt-4o"
