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

Requirements: Docker 27+, Docker Compose v2, and (optionally) Python 3.12 and Node 22+ for running backend/frontend outside containers.

```bash
git clone <repo-url> graduation_project
cd graduation_project
cp .env.example .env
docker compose up -d --build
```

Wait ~30 seconds for healthchecks, then open:

- Frontend: <http://localhost:3000/en> or <http://localhost:3000/ar>
- Backend health: <http://localhost:8010/healthz>
- Backend metrics: <http://localhost:8010/metrics>
- Qdrant dashboard: <http://localhost:6333/dashboard>

**Port note:** Host-side ports are remapped so the compose stack does not clash with local Postgres/Redis/other services most developers already run:

| Service | Host port | Container port |
|---|---|---|
| Postgres | 5433 | 5432 |
| Qdrant HTTP | 6333 | 6333 |
| Qdrant gRPC | 6334 | 6334 |
| Redis | 6380 | 6379 |
| Backend (FastAPI) | 8010 | 8000 |
| Frontend (Next.js) | 3000 | 3000 |

Inter-service calls inside the compose network use the container ports (e.g. `DATABASE_URL=postgresql+asyncpg://grad:grad@postgres:5432/grad`).

## Dev workflow

### Backend (outside Docker)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e 'backend/[dev]'
cd backend
DATABASE_URL="sqlite+aiosqlite:///./grad.db" alembic upgrade head
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
corepack pnpm install            # (corepack ships with Node 16+; no global pnpm needed)
corepack pnpm dev
```

Run tests:

```bash
cd frontend
corepack pnpm test
```

Lint + typecheck + build:

```bash
cd frontend
corepack pnpm lint && corepack pnpm typecheck && corepack pnpm build
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

**`docker compose up` fails with "port already allocated"**
Something on the host is already using 5432 / 6379 / 8000. The compose file remaps to 5433 / 6380 / 8010 to avoid that. If you still have a clash (e.g. another dev is using 8010), edit `docker-compose.yml` and update the port mapping.

**Qdrant healthcheck fails with `wget: not found`**
The qdrant image does not include wget. The compose file uses `bash </dev/tcp/localhost/6333` for the healthcheck instead. If that also fails in your qdrant image, remove the `healthcheck:` block and change dependent services to `depends_on: qdrant: { condition: service_started }`.

**Celery beat container crashes with `Permission denied: 'celerybeat-schedule'`**
The container runs as a non-root `app` user, and `/app` is not writable by `app`. The compose file passes `--schedule=/tmp/celerybeat-schedule` so beat writes to `/tmp` instead.

**Backend fails with `ModuleNotFoundError: No module named 'core'`**
You ran `uvicorn` from the repo root. Either `cd backend` first, or run `uvicorn api.main:app --app-dir backend`.

**Frontend hot reload doesn't pick up changes inside Docker**
Ensure the bind mount `./frontend:/app` is in place and `/app/node_modules` is an anonymous volume (not a bind mount). On macOS, Next.js HMR can be slow with bind mounts — prefer running the frontend on the host.

**Arabic text appears without proper direction**
Check that `<html dir="rtl" lang="ar">` is rendered — open DevTools on `/ar`. If missing, confirm `frontend/middleware.ts` is loading and that you visited `/ar` directly (not just `/`).

**Azure OpenAI 401**
Put real credentials in `.env.local` — `.env.example` intentionally ships empty. Phase 0 does not call Azure, so you can leave these blank until Phase 1.

**`corepack enable` fails without sudo**
Use `corepack pnpm <cmd>` directly instead — it runs pnpm through corepack without needing to enable the global shim.

## Current phase exit criteria (Phase 0)

- [x] `docker compose up -d --build` brings all services to `healthy` (verified during scaffold)
- [x] `curl http://localhost:8010/healthz` returns `{"status":"ok","env":"local"}`
- [x] `curl http://localhost:8010/metrics` returns Prometheus text
- [x] <http://localhost:3000/en> and <http://localhost:3000/ar> both render 200 with correct `dir`
- [x] `cd backend && pytest tests/unit` passes (8 tests)
- [x] `cd frontend && corepack pnpm test` passes (3 tests)
- [x] CI workflows defined and YAML-valid (run on first push to GitHub)

## License

Private / TBD.
