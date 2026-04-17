# Phase 0 — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold a bootable monorepo that `docker compose up` brings online with Postgres, Qdrant, Redis, a FastAPI skeleton exposing `/healthz` + `/metrics`, a Next.js 15 app serving `/en` and `/ar` with RTL, and a green CI pipeline — unblocking every subsequent phase.

**Architecture:** Single-repo layout with `backend/` (FastAPI + Celery, SQLAlchemy async, Pydantic settings, Loguru structured logs) and `frontend/` (Next.js 15 App Router, next-intl, Tailwind v4 + RTL plugin, shadcn primitives). Docker Compose orchestrates everything for local dev. Alembic starts with an empty initial migration so later phases can add schema with `upgrade head`. GitHub Actions runs lint + typecheck + unit tests for both backend and frontend on PR.

**Tech Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.x async · Alembic · Pydantic v2 · Pydantic-Settings · Loguru · Celery 5 · Redis · Qdrant 1.16 client · pytest + pytest-asyncio · ruff · mypy · Node 22 · Next.js 15 · React 19 · TypeScript strict · Tailwind v4 · next-intl · Biome · Vitest · Docker Compose.

**Spec reference:** `docs/superpowers/specs/2026-04-17-graduation-project-advisor-design.md` — this plan implements Phase 0 from §12.

---

## File structure at the end of this plan

```
graduation_project/
├── .gitignore
├── .env.example
├── README.md
├── docker-compose.yml
├── .github/workflows/
│   ├── backend-ci.yml
│   └── frontend-ci.yml
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_empty_initial.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── logging.py
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── celery_app.py
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── unit/
│           ├── __init__.py
│           ├── test_settings.py
│           ├── test_logging.py
│           └── test_health.py
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── postcss.config.mjs
    ├── biome.json
    ├── middleware.ts
    ├── i18n.ts
    ├── messages/
    │   ├── ar.json
    │   └── en.json
    ├── app/
    │   ├── [locale]/
    │   │   ├── layout.tsx
    │   │   └── page.tsx
    │   └── globals.css
    ├── components/
    │   └── atmospheric-bg.tsx
    ├── lib/
    │   └── fonts.ts
    ├── tests/
    │   └── home.test.tsx
    └── public/.gitkeep
```

Each file has exactly one responsibility. `backend/core/` holds cross-cutting infrastructure. `backend/api/` is the HTTP surface only. `backend/ingestion/` holds the Celery app shell (Phase 1 will populate it). The frontend mirrors that shape: `app/` is pages, `components/` is reusable pieces, `lib/` is infrastructure.

---

## Task 1: Repo skeleton, .gitignore, .env.example

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `backend/__init__.py` (empty package marker — actually skipped; backend is not a package)
- Create: `backend/api/__init__.py`
- Create: `backend/core/__init__.py`
- Create: `backend/ingestion/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/alembic/versions/.gitkeep`
- Create: `frontend/public/.gitkeep`

- [ ] **Step 1.1: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
coverage.xml
htmlcov/
dist/
build/

# Node
node_modules/
.next/
out/
.turbo/
*.tsbuildinfo

# Env
.env
.env.local
.env.*.local
!.env.example

# OS / editors
.DS_Store
.idea/
.vscode/
*.swp

# Docker volumes (kept out of repo)
postgres-data/
qdrant-storage/
redis-data/

# Logs
*.log
logs/
```

- [ ] **Step 1.2: Write `.env.example`**

```env
# ---------- backend ----------
ENVIRONMENT=local
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://grad:grad@postgres:5432/grad
# Dev-only alternative if running FastAPI outside docker:
# DATABASE_URL=sqlite+aiosqlite:///./grad.db

REDIS_URL=redis://redis:6379/0

QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

# Azure OpenAI (left blank for dev; set in .env.local when needed)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_SMART=gpt-4o
LLM_PROVIDER=azure

# Embedding model (local, downloaded at first use)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Session cookie
SESSION_COOKIE_SECRET=change-me-to-a-long-random-string
SESSION_COOKIE_NAME=grad_sid

# CORS
FRONTEND_ORIGIN=http://localhost:3000

# ---------- frontend ----------
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 1.3: Create empty package markers and gitkeeps**

```bash
mkdir -p backend/api backend/core backend/ingestion backend/tests/unit backend/alembic/versions
touch backend/api/__init__.py backend/core/__init__.py backend/ingestion/__init__.py
touch backend/tests/__init__.py backend/tests/unit/__init__.py
touch backend/alembic/versions/.gitkeep
mkdir -p frontend/public
touch frontend/public/.gitkeep
```

- [ ] **Step 1.4: Verify the tree**

Run:
```bash
find . -maxdepth 3 -type f \( -name '.gitignore' -o -name '.env.example' -o -name '__init__.py' -o -name '.gitkeep' \) | sort
```

Expected output contains:
```
./.env.example
./.gitignore
./backend/alembic/versions/.gitkeep
./backend/api/__init__.py
./backend/core/__init__.py
./backend/ingestion/__init__.py
./backend/tests/__init__.py
./backend/tests/unit/__init__.py
./frontend/public/.gitkeep
```

- [ ] **Step 1.5: Commit**

```bash
git add .gitignore .env.example backend/ frontend/public/
git commit -m "chore(scaffold): add repo skeleton, .gitignore, .env.example"
```

---

## Task 2: Backend pyproject.toml with pinned dependencies

**Files:**
- Create: `backend/pyproject.toml`

- [ ] **Step 2.1: Write `backend/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "grad-backend"
version = "0.0.1"
description = "Graduation Project Advisor — backend"
readme = "../README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Hesham Haroon" }]

dependencies = [
  "fastapi==0.115.6",
  "uvicorn[standard]==0.32.1",
  "pydantic==2.10.3",
  "pydantic-settings==2.7.0",
  "sqlalchemy[asyncio]==2.0.36",
  "alembic==1.14.0",
  "asyncpg==0.30.0",
  "aiosqlite==0.20.0",
  "redis==5.2.1",
  "qdrant-client==1.16.1",
  "celery[redis]==5.4.0",
  "loguru==0.7.3",
  "httpx==0.28.1",
  "prometheus-client==0.21.1",
  "itsdangerous==2.2.0",
]

[project.optional-dependencies]
dev = [
  "pytest==8.3.4",
  "pytest-asyncio==0.25.0",
  "pytest-cov==6.0.0",
  "ruff==0.8.4",
  "mypy==1.13.0",
  "types-redis==4.6.0.20241004",
  "httpx==0.28.1",
]

[tool.hatch.build.targets.wheel]
packages = ["api", "core", "ingestion"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "SIM", "RUF"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["celery.*", "qdrant_client.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
```

- [ ] **Step 2.2: Verify file syntax**

Run:
```bash
cd backend && python -c "import tomllib; tomllib.loads(open('pyproject.toml').read())" && echo OK
```
Expected: `OK`

- [ ] **Step 2.3: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore(backend): add pyproject.toml with pinned deps"
```

---

## Task 3: Settings module (TDD)

Settings loads from env via pydantic-settings. Must handle missing optional keys without crashing, must parse the `DATABASE_URL` and `REDIS_URL` as strings (not URL types — keep it simple), and must expose an `is_local` helper.

**Files:**
- Create: `backend/core/settings.py`
- Create: `backend/tests/unit/test_settings.py`

- [ ] **Step 3.1: Write the failing test**

Create `backend/tests/unit/test_settings.py`:
```python
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
```

- [ ] **Step 3.2: Run test to verify it fails**

Run:
```bash
cd backend && pytest tests/unit/test_settings.py -v
```
Expected: FAIL (`ModuleNotFoundError: No module named 'core.settings'` or similar).

- [ ] **Step 3.3: Implement `backend/core/settings.py`**

```python
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
```

- [ ] **Step 3.4: Run test to verify it passes**

Run:
```bash
cd backend && pytest tests/unit/test_settings.py -v
```
Expected: 3 passed.

- [ ] **Step 3.5: Commit**

```bash
git add backend/core/settings.py backend/tests/unit/test_settings.py
git commit -m "feat(backend): add Settings module with env loading"
```

---

## Task 4: Logging module (TDD)

Loguru configured for structured JSON output, with a `bind_context` helper that attaches `session_id`, `stage`, `candidate_id` to log records.

**Files:**
- Create: `backend/core/logging.py`
- Create: `backend/tests/unit/test_logging.py`

- [ ] **Step 4.1: Write the failing test**

Create `backend/tests/unit/test_logging.py`:
```python
from __future__ import annotations

import io
import json
import re

from loguru import logger


def test_configure_logging_emits_json_with_context() -> None:
    from core.logging import bind_context, configure_logging

    configure_logging(level="INFO")

    sink = io.StringIO()
    sink_id = logger.add(sink, serialize=True, level="INFO")
    try:
        log = bind_context(session_id="abc", stage="retrieve", candidate_id="xyz")
        log.info("hello")
    finally:
        logger.remove(sink_id)

    raw = sink.getvalue().strip()
    # Loguru serialize=True emits one JSON per line
    payload = json.loads(raw)
    record = payload["record"]
    assert record["message"] == "hello"
    extra = record["extra"]
    assert extra["session_id"] == "abc"
    assert extra["stage"] == "retrieve"
    assert extra["candidate_id"] == "xyz"


def test_configure_logging_respects_level() -> None:
    from core.logging import configure_logging

    configure_logging(level="ERROR")

    sink = io.StringIO()
    sink_id = logger.add(sink, serialize=True, level="ERROR")
    try:
        logger.info("quiet")
        logger.error("loud")
    finally:
        logger.remove(sink_id)

    output = sink.getvalue()
    assert "quiet" not in output
    # "loud" may be escaped/wrapped in JSON; check via regex
    assert re.search(r'"message":\s*"loud"', output)
```

- [ ] **Step 4.2: Run test to verify it fails**

Run:
```bash
cd backend && pytest tests/unit/test_logging.py -v
```
Expected: FAIL (module not found).

- [ ] **Step 4.3: Implement `backend/core/logging.py`**

```python
from __future__ import annotations

import sys
from typing import Any

from loguru import logger


def configure_logging(level: str = "INFO") -> None:
    """Configure loguru with JSON sink to stdout.

    Idempotent: removes existing handlers before adding.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        serialize=True,
        backtrace=False,
        diagnose=False,
    )


def bind_context(**kwargs: Any) -> Any:
    """Return a logger bound with the given context keys.

    Typical use: ``log = bind_context(session_id=sid, stage="retrieve")``.
    """
    return logger.bind(**kwargs)
```

- [ ] **Step 4.4: Run test to verify it passes**

Run:
```bash
cd backend && pytest tests/unit/test_logging.py -v
```
Expected: 2 passed.

- [ ] **Step 4.5: Commit**

```bash
git add backend/core/logging.py backend/tests/unit/test_logging.py
git commit -m "feat(backend): add structured loguru logging with context binding"
```

---

## Task 5: FastAPI app with /healthz and /metrics (TDD)

App factory pattern. `/healthz` returns `{"status": "ok", "env": ...}`. `/metrics` exposes Prometheus default metrics. App startup calls `configure_logging`.

**Files:**
- Create: `backend/api/main.py`
- Create: `backend/tests/unit/test_health.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 5.1: Write conftest for httpx client**

Create `backend/tests/conftest.py`:
```python
from __future__ import annotations

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from api.main import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

- [ ] **Step 5.2: Write the failing test**

Create `backend/tests/unit/test_health.py`:
```python
from __future__ import annotations

from httpx import AsyncClient


async def test_healthz_ok(client: AsyncClient) -> None:
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["env"] == "local"


async def test_metrics_prometheus_format(client: AsyncClient) -> None:
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    # Prometheus default counters always include python_info
    assert "python_info" in resp.text


async def test_root_returns_service_name(client: AsyncClient) -> None:
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "grad-backend"
```

- [ ] **Step 5.3: Run test to verify it fails**

Run:
```bash
cd backend && pytest tests/unit/test_health.py -v
```
Expected: FAIL (`ModuleNotFoundError: No module named 'api.main'`).

- [ ] **Step 5.4: Implement `backend/api/main.py`**

```python
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from core.logging import configure_logging
from core.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Graduation Project Advisor",
        version="0.0.1",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "grad-backend", "version": "0.0.1"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.environment}

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
```

- [ ] **Step 5.5: Run tests to verify they pass**

Run:
```bash
cd backend && pytest tests/unit -v
```
Expected: all tests pass (7 so far: 3 settings + 2 logging + 3 health — wait, 3+2+3=8; either way all green).

- [ ] **Step 5.6: Run the server locally to smoke test**

Run (from `backend/`):
```bash
uvicorn api.main:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/healthz
kill %1
```
Expected: `{"status":"ok","env":"local"}`

- [ ] **Step 5.7: Commit**

```bash
git add backend/api/main.py backend/tests/conftest.py backend/tests/unit/test_health.py
git commit -m "feat(api): add FastAPI app with /healthz, /metrics, CORS"
```

---

## Task 6: Backend Dockerfile

Multi-stage build. Installs deps into a virtualenv during build, copies to slim runtime image. Non-root user. Exposes 8000.

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 6.1: Write `backend/.dockerignore`**

```
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.coverage
coverage.xml
htmlcov
tests
.venv
venv
*.log
```

- [ ] **Step 6.2: Write `backend/Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install .

FROM python:3.12-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system app && useradd --system --gid app --home-dir /app app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app api ./api
COPY --chown=app:app core ./core
COPY --chown=app:app ingestion ./ingestion
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini
USER app
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6.3: Verify the Dockerfile builds**

Run (from repo root):
```bash
docker build -t grad-backend:dev backend/
```
Expected: build succeeds, final message `naming to docker.io/library/grad-backend:dev`.

NOTE: this will **fail at the COPY alembic line** until Task 7 creates those files. That's expected — skip the build check here and come back after Task 7. Alternatively, comment out the two `alembic` COPY lines, build, then uncomment.

- [ ] **Step 6.4: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore
git commit -m "chore(backend): add multi-stage Dockerfile"
```

---

## Task 7: Alembic setup + empty initial migration

Alembic configured for async SQLAlchemy. Initial migration is intentionally empty — Phase 1 will add schema.

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_empty_initial.py`

- [ ] **Step 7.1: Write `backend/alembic.ini`**

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 7.2: Write `backend/alembic/env.py`**

```python
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from core.settings import get_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Placeholder; Phase 1 replaces with Base.metadata from core.db.models
target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 7.3: Write `backend/alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 7.4: Write `backend/alembic/versions/0001_empty_initial.py`**

```python
"""empty initial

Revision ID: 0001
Revises:
Create Date: 2026-04-17 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

- [ ] **Step 7.5: Verify alembic can run (against SQLite)**

Run (from `backend/`, requires deps installed — set up venv if not already):
```bash
python -m venv ../.venv && . ../.venv/bin/activate && pip install -e .[dev]
DATABASE_URL="sqlite+aiosqlite:///./test.db" alembic upgrade head
rm -f test.db
```
Expected: output contains `Running upgrade  -> 0001, empty initial`.

- [ ] **Step 7.6: Rebuild Docker image (now that alembic files exist)**

Run (from repo root):
```bash
docker build -t grad-backend:dev backend/
```
Expected: build succeeds.

- [ ] **Step 7.7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat(backend): add alembic with empty initial migration"
```

---

## Task 8: Celery app skeleton

Shell only — Phase 1 will register the actual ingestion tasks. The skeleton proves the worker boots and connects to Redis.

**Files:**
- Create: `backend/ingestion/celery_app.py`

- [ ] **Step 8.1: Write `backend/ingestion/celery_app.py`**

```python
from __future__ import annotations

from celery import Celery

from core.settings import get_settings


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "grad",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[],  # Phase 1 will register pipelines here
    )
    app.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        timezone="UTC",
        enable_utc=True,
        beat_schedule={},  # Phase 1 will populate
    )
    return app


celery_app = make_celery()
```

- [ ] **Step 8.2: Verify it imports cleanly**

Run (from `backend/` with venv active):
```bash
python -c "from ingestion.celery_app import celery_app; print(celery_app.main)"
```
Expected: `grad`.

- [ ] **Step 8.3: Commit**

```bash
git add backend/ingestion/celery_app.py
git commit -m "feat(ingestion): add Celery app skeleton"
```

---

## Task 9: Docker Compose with all infra services

Postgres + Qdrant + Redis + backend (FastAPI) + celery-worker + celery-beat. Frontend added in Task 13.

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 9.1: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: grad-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: grad
      POSTGRES_PASSWORD: grad
      POSTGRES_DB: grad
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grad"]
      interval: 5s
      timeout: 3s
      retries: 10

  qdrant:
    image: qdrant/qdrant:v1.16.1
    container_name: grad-qdrant
    restart: unless-stopped
    volumes:
      - qdrant-storage:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:6333/readyz || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    container_name: grad-redis
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: grad-backend
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://grad:grad@postgres:5432/grad
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
      FRONTEND_ORIGIN: http://localhost:3000
    ports:
      - "8000:8000"
    depends_on:
      postgres: { condition: service_healthy }
      qdrant:   { condition: service_healthy }
      redis:    { condition: service_healthy }

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: grad-celery-worker
    restart: unless-stopped
    command: ["celery", "-A", "ingestion.celery_app.celery_app", "worker", "--loglevel=INFO"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://grad:grad@postgres:5432/grad
      REDIS_URL: redis://redis:6379/0
      QDRANT_URL: http://qdrant:6333
    depends_on:
      redis: { condition: service_healthy }

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: grad-celery-beat
    restart: unless-stopped
    command: ["celery", "-A", "ingestion.celery_app.celery_app", "beat", "--loglevel=INFO"]
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://grad:grad@postgres:5432/grad
      REDIS_URL: redis://redis:6379/0
    depends_on:
      redis: { condition: service_healthy }

volumes:
  postgres-data:
  qdrant-storage:
  redis-data:
```

- [ ] **Step 9.2: Copy env file so compose picks it up**

```bash
cp .env.example .env
```

- [ ] **Step 9.3: Boot the stack**

Run:
```bash
docker compose up -d --build
```
Wait ~30s for builds and healthchecks.

- [ ] **Step 9.4: Smoke-test each service**

Run in parallel (or sequentially):
```bash
curl -s http://localhost:8000/healthz | grep -q '"status":"ok"' && echo BACKEND_OK
curl -s http://localhost:6333/readyz | grep -q 'all shards' && echo QDRANT_OK || curl -s http://localhost:6333/readyz
docker exec grad-postgres pg_isready -U grad | grep -q 'accepting connections' && echo POSTGRES_OK
docker exec grad-redis redis-cli ping | grep -q PONG && echo REDIS_OK
docker logs grad-celery-worker 2>&1 | tail -5 | grep -q 'ready' && echo WORKER_OK
```

Expected: `BACKEND_OK`, `QDRANT_OK`, `POSTGRES_OK`, `REDIS_OK`, `WORKER_OK` all printed.

- [ ] **Step 9.5: Tear down**

```bash
docker compose down
```

- [ ] **Step 9.6: Commit**

```bash
git add docker-compose.yml
git commit -m "chore(infra): add docker-compose with postgres/qdrant/redis/backend/celery"
```

---

## Task 10: Frontend scaffold (Next.js 15 + TypeScript strict)

Hand-roll `package.json` and scaffolding — we don't want `create-next-app` clobbering our design decisions (manuscript theme, RTL, custom fonts, no default shadcn theme).

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/biome.json`
- Create: `frontend/.gitignore` (next-specific supplement, mostly covered by root but `next-env.d.ts` etc.)

- [ ] **Step 10.1: Write `frontend/package.json`**

```json
{
  "name": "grad-frontend",
  "version": "0.0.1",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "biome check .",
    "format": "biome format --write .",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "15.1.3",
    "next-intl": "3.26.3",
    "react": "19.0.0",
    "react-dom": "19.0.0"
  },
  "devDependencies": {
    "@biomejs/biome": "1.9.4",
    "@tailwindcss/postcss": "4.0.0-beta.9",
    "@testing-library/jest-dom": "6.6.3",
    "@testing-library/react": "16.1.0",
    "@types/node": "22.10.5",
    "@types/react": "19.0.7",
    "@types/react-dom": "19.0.3",
    "autoprefixer": "10.4.20",
    "jsdom": "26.0.0",
    "postcss": "8.4.49",
    "tailwindcss": "4.0.0-beta.9",
    "typescript": "5.7.3",
    "vitest": "2.1.8"
  },
  "packageManager": "pnpm@9.15.2"
}
```

- [ ] **Step 10.2: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "jsx": "preserve",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 10.3: Write `frontend/next.config.ts`**

```ts
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./i18n.ts");

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    typedRoutes: true,
  },
};

export default withNextIntl(nextConfig);
```

- [ ] **Step 10.4: Write `frontend/biome.json`**

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "a11y": { "recommended": true },
      "style": { "noParameterAssign": "error" }
    }
  },
  "javascript": {
    "formatter": { "quoteStyle": "double", "trailingCommas": "all", "semicolons": "always" }
  },
  "files": { "ignore": [".next", "node_modules", "public"] }
}
```

- [ ] **Step 10.5: Install deps**

```bash
cd frontend && corepack enable && pnpm install
```
Expected: no errors. `pnpm-lock.yaml` is produced — commit it.

- [ ] **Step 10.6: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/next.config.ts frontend/biome.json frontend/pnpm-lock.yaml
git commit -m "chore(frontend): scaffold Next.js 15 + TS strict + Biome"
```

---

## Task 11: i18n routing and messages

Locale-segmented routing (`/en`, `/ar`), middleware redirects `/` to the preferred locale, two flat message JSON files.

**Files:**
- Create: `frontend/i18n.ts`
- Create: `frontend/middleware.ts`
- Create: `frontend/messages/en.json`
- Create: `frontend/messages/ar.json`

- [ ] **Step 11.1: Write `frontend/i18n.ts`**

```ts
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

export const locales = ["en", "ar"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";

export default getRequestConfig(async ({ locale }) => {
  if (!locales.includes(locale as Locale)) {
    notFound();
  }
  const messages = (await import(`./messages/${locale}.json`)).default;
  return { messages };
});
```

- [ ] **Step 11.2: Write `frontend/middleware.ts`**

```ts
import createMiddleware from "next-intl/middleware";
import { defaultLocale, locales } from "./i18n";

export default createMiddleware({
  locales,
  defaultLocale,
  localePrefix: "always",
});

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

- [ ] **Step 11.3: Write `frontend/messages/en.json`**

```json
{
  "landing": {
    "headline": "Find your graduation project.",
    "subhead": "Grounded in real papers. Grounded in real repos.",
    "cta": "Start now",
    "langToggleLabel": "Language",
    "themeToggleLabel": "Theme"
  },
  "common": {
    "loading": "Loading…",
    "error": "Something went wrong",
    "tryAgain": "Try again"
  }
}
```

- [ ] **Step 11.4: Write `frontend/messages/ar.json`**

```json
{
  "landing": {
    "headline": "اختر مشروع تخرجك بثقة.",
    "subhead": "مبني على أبحاث حقيقية ومستودعات حقيقية.",
    "cta": "ابدأ الآن",
    "langToggleLabel": "اللغة",
    "themeToggleLabel": "المظهر"
  },
  "common": {
    "loading": "جاري التحميل…",
    "error": "حدث خطأ ما",
    "tryAgain": "حاول مرة أخرى"
  }
}
```

- [ ] **Step 11.5: Commit**

```bash
git add frontend/i18n.ts frontend/middleware.ts frontend/messages/
git commit -m "feat(frontend): wire next-intl with ar/en locales"
```

---

## Task 12: Tailwind v4 + manuscript tokens + fonts + globals.css

Tailwind v4 uses CSS-first config via `@theme`. Manuscript color tokens from spec §8.3.

**Files:**
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/app/globals.css`
- Create: `frontend/lib/fonts.ts`

- [ ] **Step 12.1: Write `frontend/postcss.config.mjs`**

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
};

export default config;
```

- [ ] **Step 12.2: Write `frontend/tailwind.config.ts`** (Tailwind v4 still supports JS config for content paths)

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
};

export default config;
```

- [ ] **Step 12.3: Write `frontend/lib/fonts.ts`**

Uses next/font/google for the four Latin fonts (Fraunces, Satoshi isn't on Google Fonts — substitute **Cabinet Grotesk**-style candidate available on Google: use **DM Sans** as a clean Satoshi-adjacent sans while we confirm self-hosting later; Lemonada and JetBrains Mono for the other slots). Phase 5 swaps to self-hosted Satoshi + IBM Plex Arabic.

```ts
import { Fraunces, DM_Sans, Lemonada, JetBrains_Mono } from "next/font/google";

export const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display-latin",
  axes: ["opsz"],
  weight: ["200", "400", "800"],
  display: "swap",
});

export const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body-latin",
  weight: ["400", "500", "700"],
  display: "swap",
});

export const lemonada = Lemonada({
  subsets: ["arabic", "latin"],
  variable: "--font-display-arabic",
  weight: ["300", "500", "700"],
  display: "swap",
});

export const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "600"],
  display: "swap",
});
```

NOTE: IBM Plex Arabic is on Google Fonts — we'll add it in Phase 5 alongside self-hosted Satoshi. For Phase 0 we prove the font pipeline works; the Arabic body currently falls back to Lemonada (which has Arabic glyphs), acceptable for the placeholder landing page.

- [ ] **Step 12.4: Write `frontend/app/globals.css`** (manuscript tokens + base styles)

```css
@import "tailwindcss";

@theme {
  --color-canvas: #f6efe1;
  --color-surface: #fbf6ea;
  --color-elevated: #ffffff;
  --color-text-primary: #1a1612;
  --color-text-muted: #6a5f52;
  --color-border-subtle: #e6dcc6;
  --color-accent: #c48a1e;
  --color-accent-strong: #8a5c10;
  --color-signal-code: #2f6b4f;
  --color-signal-paper: #8b2e2e;
  --color-signal-warn: #b84a1a;
}

@media (prefers-color-scheme: dark) {
  @theme {
    --color-canvas: #14110c;
    --color-surface: #1f1a12;
    --color-elevated: #26201a;
    --color-text-primary: #f0e6d0;
    --color-text-muted: #a89c82;
    --color-border-subtle: #3a3224;
    --color-accent: #e0a840;
    --color-accent-strong: #c48a1e;
  }
}

:root {
  color-scheme: light dark;
}

html {
  background: var(--color-canvas);
  color: var(--color-text-primary);
  font-family: var(--font-body-latin), system-ui, sans-serif;
}

html[lang="ar"] {
  font-family: var(--font-display-arabic), system-ui, sans-serif;
  line-height: 1.9;
}

html[lang="en"] {
  line-height: 1.55;
}

body {
  min-height: 100dvh;
}

/* Atmospheric grain background (used by AtmosphericBg component) */
.grain {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.06'/></svg>");
  background-repeat: repeat;
}
```

- [ ] **Step 12.5: Commit**

```bash
git add frontend/postcss.config.mjs frontend/tailwind.config.ts frontend/app/globals.css frontend/lib/fonts.ts
git commit -m "feat(frontend): add Tailwind v4 + manuscript tokens + font pipeline"
```

---

## Task 13: Root layout + home page for both locales + atmospheric bg component

Renders a placeholder landing in either locale with correct `dir` and `lang`. This is Phase 0's UI exit gate.

**Files:**
- Create: `frontend/app/[locale]/layout.tsx`
- Create: `frontend/app/[locale]/page.tsx`
- Create: `frontend/components/atmospheric-bg.tsx`
- Create: `frontend/tests/home.test.tsx`
- Create: `frontend/vitest.config.ts`

- [ ] **Step 13.1: Write `frontend/components/atmospheric-bg.tsx`**

```tsx
export function AtmosphericBg() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 grain"
      style={{
        backgroundImage: `
          radial-gradient(at 0% 0%, color-mix(in srgb, var(--color-accent) 14%, transparent), transparent 50%),
          radial-gradient(at 100% 100%, color-mix(in srgb, var(--color-accent-strong) 10%, transparent), transparent 60%)
        `,
      }}
    />
  );
}
```

- [ ] **Step 13.2: Write `frontend/app/[locale]/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";

import { AtmosphericBg } from "@/components/atmospheric-bg";
import { locales, type Locale } from "@/i18n";
import { fraunces, dmSans, lemonada, jetbrainsMono } from "@/lib/fonts";

import "../globals.css";

export const metadata: Metadata = {
  title: "Graduation Project Advisor",
  description: "Find your graduation project — grounded in papers and code.",
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!locales.includes(locale as Locale)) {
    notFound();
  }
  setRequestLocale(locale);
  const messages = await getMessages();

  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html
      lang={locale}
      dir={dir}
      className={`${fraunces.variable} ${dmSans.variable} ${lemonada.variable} ${jetbrainsMono.variable}`}
    >
      <body>
        <AtmosphericBg />
        <NextIntlClientProvider messages={messages}>
          <main className="relative mx-auto max-w-6xl px-6 py-16">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 13.3: Write `frontend/app/[locale]/page.tsx`**

```tsx
import { useTranslations } from "next-intl";

export default function HomePage() {
  const t = useTranslations("landing");

  return (
    <section className="flex flex-col gap-6">
      <h1
        className="text-5xl md:text-7xl"
        style={{ fontFamily: "var(--font-display-latin), var(--font-display-arabic)", fontWeight: 800 }}
      >
        {t("headline")}
      </h1>
      <p className="max-w-xl text-lg opacity-80">{t("subhead")}</p>
      <div>
        <button
          type="button"
          className="rounded-md px-5 py-3 text-sm font-medium"
          style={{ background: "var(--color-accent)", color: "var(--color-elevated)" }}
        >
          {t("cta")}
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 13.4: Write `frontend/vitest.config.ts`**

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: [],
    globals: true,
  },
  resolve: {
    alias: { "@": "." },
  },
});
```

- [ ] **Step 13.5: Write `frontend/tests/home.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import en from "../messages/en.json";
import ar from "../messages/ar.json";
import HomePage from "../app/[locale]/page";

function renderWithLocale(locale: "en" | "ar") {
  const messages = locale === "en" ? en : ar;
  return render(
    <NextIntlClientProvider messages={messages} locale={locale}>
      <HomePage />
    </NextIntlClientProvider>,
  );
}

describe("HomePage", () => {
  it("renders English headline", () => {
    renderWithLocale("en");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toMatch(/graduation/i);
  });

  it("renders Arabic headline", () => {
    renderWithLocale("ar");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toContain("تخرج");
  });

  it("renders CTA button in both locales", () => {
    const { unmount } = renderWithLocale("en");
    expect(screen.getByRole("button").textContent).toBe("Start now");
    unmount();
    renderWithLocale("ar");
    expect(screen.getByRole("button").textContent).toBe("ابدأ الآن");
  });
});
```

- [ ] **Step 13.6: Run the frontend tests**

Run (from `frontend/`):
```bash
pnpm test
```
Expected: 3 passed.

- [ ] **Step 13.7: Smoke-test the dev server**

Run (from `frontend/`):
```bash
pnpm dev &
DEV_PID=$!
sleep 6
curl -sI http://localhost:3000/en | head -1
curl -sI http://localhost:3000/ar | head -1
kill $DEV_PID
```
Expected (for both): `HTTP/1.1 200 OK`.

- [ ] **Step 13.8: Commit**

```bash
git add frontend/app/ frontend/components/ frontend/tests/ frontend/vitest.config.ts
git commit -m "feat(frontend): add root layout + landing page for /en and /ar"
```

---

## Task 14: Add frontend dev service to docker-compose

Runs `pnpm dev` inside a lightweight Node image.

**Files:**
- Modify: `docker-compose.yml` (add `frontend` service)
- Create: `frontend/Dockerfile.dev`

- [ ] **Step 14.1: Write `frontend/Dockerfile.dev`**

```dockerfile
FROM node:22-alpine
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
EXPOSE 3000
CMD ["pnpm", "dev"]
```

- [ ] **Step 14.2: Add `frontend` service to `docker-compose.yml`**

Append this block to `docker-compose.yml` **before** the `volumes:` section (so the indentation matches other services):

```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    container_name: grad-frontend
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

- [ ] **Step 14.3: Boot the full stack**

```bash
docker compose up -d --build
sleep 30
```

- [ ] **Step 14.4: Verify everything is alive**

```bash
curl -s http://localhost:8000/healthz | grep -q '"status":"ok"' && echo BACKEND_OK
curl -sI http://localhost:3000/en | head -1
docker compose ps
```
Expected: `BACKEND_OK`, `HTTP/1.1 200 OK`, and `docker compose ps` shows `postgres`, `qdrant`, `redis`, `backend`, `celery-worker`, `celery-beat`, `frontend` all `healthy` or `running`.

- [ ] **Step 14.5: Tear down**

```bash
docker compose down
```

- [ ] **Step 14.6: Commit**

```bash
git add frontend/Dockerfile.dev docker-compose.yml
git commit -m "chore(infra): add frontend dev service to docker-compose"
```

---

## Task 15: CI workflows (GitHub Actions)

Two separate workflows — backend and frontend — so they run in parallel and have independent caches.

**Files:**
- Create: `.github/workflows/backend-ci.yml`
- Create: `.github/workflows/frontend-ci.yml`

- [ ] **Step 15.1: Write `.github/workflows/backend-ci.yml`**

```yaml
name: backend-ci

on:
  push:
    branches: [main]
    paths: ["backend/**", ".github/workflows/backend-ci.yml"]
  pull_request:
    paths: ["backend/**", ".github/workflows/backend-ci.yml"]

jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
      - name: Lint
        run: ruff check .
      - name: Format check
        run: ruff format --check .
      - name: Typecheck
        run: mypy api core ingestion
      - name: Unit tests
        run: pytest tests/unit -v --cov=api --cov=core --cov=ingestion --cov-report=term-missing
```

- [ ] **Step 15.2: Write `.github/workflows/frontend-ci.yml`**

```yaml
name: frontend-ci

on:
  push:
    branches: [main]
    paths: ["frontend/**", ".github/workflows/frontend-ci.yml"]
  pull_request:
    paths: ["frontend/**", ".github/workflows/frontend-ci.yml"]

jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9.15.2
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "pnpm"
          cache-dependency-path: frontend/pnpm-lock.yaml
      - name: Install deps
        run: pnpm install --frozen-lockfile
      - name: Lint
        run: pnpm lint
      - name: Typecheck
        run: pnpm typecheck
      - name: Unit tests
        run: pnpm test
      - name: Build
        run: pnpm build
```

- [ ] **Step 15.3: Verify workflows locally (syntax)**

Run:
```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/backend-ci.yml'))" && echo backend-ci OK
python -c "import yaml; yaml.safe_load(open('.github/workflows/frontend-ci.yml'))" && echo frontend-ci OK
```
Expected: `backend-ci OK`, `frontend-ci OK`.

- [ ] **Step 15.4: Commit**

```bash
git add .github/
git commit -m "chore(ci): add backend and frontend GitHub Actions workflows"
```

---

## Task 16: README with setup + dev + troubleshooting

Final exit gate — an engineer who's never seen the repo can clone and boot it.

**Files:**
- Create: `README.md`

- [ ] **Step 16.1: Write `README.md`**

````markdown
# Graduation Project Advisor

Helps Egyptian CS / AI / SWE undergraduates pick a production-grade graduation project grounded in real research papers and real GitHub repos. Bilingual (Arabic + English) web app.

> Design spec: [`docs/superpowers/specs/2026-04-17-graduation-project-advisor-design.md`](docs/superpowers/specs/2026-04-17-graduation-project-advisor-design.md)
> Current implementation phase: **Phase 0 — Foundations** (scaffold only; no recommendations yet)

## Stack

- **Backend:** Python 3.12 · FastAPI · SQLAlchemy (async) · Alembic · Pydantic · Celery · Loguru
- **Data:** PostgreSQL · Qdrant · Redis
- **Frontend:** Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind v4 · next-intl · Biome
- **AI:** Azure OpenAI (`gpt-4o`, `gpt-4o-mini`) · local sentence-transformers embeddings
- **Deploy:** Docker Compose on a single VPS (Caddy for TLS in prod)

## Quick start

Requirements: Docker 27+, Docker Compose v2, and (optionally) Python 3.12 and Node 22 for running backend/frontend outside containers.

```bash
git clone <repo-url> graduation_project
cd graduation_project
cp .env.example .env
docker compose up -d --build
```

Wait ~30 seconds for healthchecks, then open:

- Frontend: http://localhost:3000/en or http://localhost:3000/ar
- Backend health: http://localhost:8000/healthz
- Backend metrics: http://localhost:8000/metrics
- Qdrant dashboard: http://localhost:6333/dashboard

## Dev workflow

### Backend (outside Docker)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e 'backend/[dev]'
cd backend
alembic upgrade head
uvicorn api.main:app --reload
```

Run tests:

```bash
cd backend
pytest tests/unit -v
```

Lint + typecheck:

```bash
cd backend
ruff check . && ruff format --check . && mypy api core ingestion
```

### Frontend (outside Docker)

```bash
cd frontend
corepack enable
pnpm install
pnpm dev
```

Run tests:

```bash
cd frontend
pnpm test
```

Lint + typecheck + build:

```bash
cd frontend
pnpm lint && pnpm typecheck && pnpm build
```

## Layout

```
backend/    FastAPI app, Celery workers, Alembic migrations, ingestion pipelines (later phases)
frontend/   Next.js 15 App Router, bilingual (ar/en) with RTL
docs/       Specs and plans under docs/superpowers/
.github/    CI workflows
docker-compose.yml   Local dev infra: postgres, qdrant, redis, backend, celery, frontend
```

## Troubleshooting

**`docker compose up` fails on Postgres healthcheck**
Increase the healthcheck retries in `docker-compose.yml` or allow more warm-up time. On first boot Postgres initializes the data dir which takes ~10 seconds.

**Backend fails with `ModuleNotFoundError: no module named 'core'`**
You're running uvicorn from the repo root. `cd backend` first, or run `uvicorn api.main:app --app-dir backend`.

**Frontend hot reload doesn't pick up changes inside Docker**
Ensure the bind mount `./frontend:/app` is in place and `/app/node_modules` is an anonymous volume (not a bind mount). On macOS, Next.js HMR can be slow with bind mounts — prefer running frontend on the host.

**Arabic text appears without proper direction**
Check that `<html dir="rtl" lang="ar">` is rendered — open DevTools on `/ar`. If missing, confirm `frontend/middleware.ts` is loading and that you visited `/ar` directly (not just `/`).

**Azure OpenAI 401**
Put real credentials in `.env.local` — `.env.example` intentionally ships empty. Phase 0 does not call Azure, so you can leave these blank until Phase 1.

## Current phase exit criteria (Phase 0)

- [ ] `docker compose up -d --build` brings all services to `healthy`
- [ ] `curl http://localhost:8000/healthz` returns `{"status":"ok","env":"local"}`
- [ ] `curl http://localhost:8000/metrics` returns Prometheus text
- [ ] http://localhost:3000/en and http://localhost:3000/ar both render 200 with correct `dir`
- [ ] `cd backend && pytest tests/unit` passes
- [ ] `cd frontend && pnpm test && pnpm typecheck && pnpm build` all pass
- [ ] CI (GitHub Actions) is green on `main`

## License

Private / TBD.
````

- [ ] **Step 16.2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup, dev workflow, troubleshooting"
```

---

## Task 17: End-to-end verification of Phase 0 exit criteria

Run the complete exit checklist from the README. If anything fails, fix and re-commit before declaring Phase 0 done.

- [ ] **Step 17.1: Boot the full stack and wait for health**

```bash
docker compose down -v  # clean slate
docker compose up -d --build
for i in $(seq 1 24); do
  UNHEALTHY=$(docker compose ps --format json | python -c "import json,sys; [print(s['Service']) for line in sys.stdin for s in [json.loads(line)] if s.get('Health') not in ('healthy', None) or s.get('State') != 'running']")
  [ -z "$UNHEALTHY" ] && echo ALL_HEALTHY && break
  echo "waiting... ($UNHEALTHY)"; sleep 5
done
```
Expected: `ALL_HEALTHY` printed within ~2 minutes.

- [ ] **Step 17.2: Hit every exit-criterion endpoint**

```bash
curl -sf http://localhost:8000/healthz | grep -q '"status":"ok"' && echo EXIT_HEALTHZ_OK
curl -sf http://localhost:8000/metrics | head -1 | grep -q 'HELP' && echo EXIT_METRICS_OK
curl -sfI http://localhost:3000/en | head -1 | grep -q '200' && echo EXIT_EN_OK
curl -sfI http://localhost:3000/ar | head -1 | grep -q '200' && echo EXIT_AR_OK
curl -sf http://localhost:3000/ar | grep -q 'dir="rtl"' && echo EXIT_RTL_OK
```
Expected: all five `EXIT_*_OK` lines printed.

- [ ] **Step 17.3: Run all tests**

```bash
docker compose exec backend pytest tests/unit -v
docker compose exec frontend pnpm test
```
Expected: both pass.

- [ ] **Step 17.4: Tear down and declare Phase 0 complete**

```bash
docker compose down
```

No commit for this task — it's verification only.

- [ ] **Step 17.5: Tag the milestone**

```bash
git tag -a phase-0-complete -m "Phase 0: foundations scaffold complete"
```

---

## Post-plan notes

**What's explicitly deferred to later phases (do NOT add to this plan):**
- Database models (Phase 1)
- Ingestion pipelines (Phase 1 / 2)
- Recommendation API routes beyond `/healthz` and `/metrics` (Phase 3)
- Any LLM integration (Phase 3)
- shadcn primitive installation (Phase 5)
- Self-hosted Satoshi / IBM Plex Arabic fonts (Phase 5)
- Language toggle and theme toggle components (Phase 5)
- Real landing design (Phase 6)
- Caddy / production deploy (Phase 10)

**If a step fails in an unexpected way:** stop, open the test/log, and fix the root cause rather than hacking around. The most common failure is `.env` missing or having stale values — `cp .env.example .env` from a clean checkout is the first thing to try.

**Commit hygiene:** one commit per task (not per step) keeps history readable. If a task requires rework, squash before merging to `main`.
