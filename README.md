<div align="center">

# Graduation Project Advisor

### Find the graduation project that's yours — grounded in real research, real code, and a plan your supervisor will actually read.

An Arabic-first, bilingual AI advisor for Egyptian CS / AI / SWE undergraduates. One form, five grounded ideas, and a one-click expansion into a supervisor-ready blueprint anchored in the paper's real abstract and the repo's real README.

<img src="docs/assets/landing-ar-dark.png" alt="Arabic landing page, dark manuscript theme" width="860" />

</div>

---

## Why this exists

Every senior-year CS student in Egypt hits the same wall: *what should my graduation project be?* The usual answers are:

- **Shallow** — "build a todo app with auth."
- **Disconnected from research** — no paper grounding, no clear novelty angle.
- **Overwhelming** — raw arXiv feeds, endless GitHub trending, contradictory advice.

Supervisors don't have the hours to hand-tailor ideas to every student's background, timeline, and interests. This tool fills that gap: a retrieval-grounded advisor that speaks the student's language, cites real papers and real repos, and produces an artifact the supervisor can sign off on.

---

## What it does

- **Five grounded ideas per session.** A short form captures the student's domains, skill level, timeline, team size, and interests. The recommender retrieves from a live corpus of papers + repos, scores candidates deterministically, lets a language model re-rank the top 20, and returns 5 cards — **every card cites a real paper or repo**. The re-ranker is constrained to pick only from the retrieved set; fabricated ids are dropped.

- **Plans grounded in actual content.** Clicking *Expand blueprint* on a card fetches the real abstract from the database and the real README from GitHub, feeds both into the prompt, and asks for a blueprint anchored in that material. Where the source is silent, the plan explicitly says *"details to refine with your supervisor"* instead of inventing.

- **Refine in place.** A sticky chat bar at the bottom of the board lets the student say "more RL, less infra, cut timeline to 3 months." The current intent profile is diffed, the board re-retrieves, and up to fifteen refinements per session are stackable with a one-click Undo.

- **Triage and compare.** Thumbs up / down per card (persisted for the offline eval set), a save button, a dedicated saved page, and a three-way side-by-side compare panel.

- **Fully bilingual, RTL-correct.** Every view works in Arabic and English. Technical terms stay in English (RAG, transformer, embedding, PyTorch) while the "why this fits you" reasoning is rendered in the student's language. The manuscript typography pairs Fraunces / DM Sans (Latin) with Lemonada (Arabic) and keeps Arabic line-height at 1.9 so the script has room to breathe.

---

## Screens

### Onboarding — the only form in the app

Domain chips, skill level, months available, team size, preferred stack, interests free-text, and topics to avoid. No tracking, no login, no account. The profile lives in the server session (Redis, 6-hour TTL) and is discarded when the tab closes.

<div align="center">
  <img src="docs/assets/onboard-ar-dark.png" alt="Arabic onboarding form, dark theme" width="860" />
</div>

### The board — ranked cards, not a chat transcript

Five cards, asymmetric layout, each grounded in a named research area and a named stack. Intentionally *not* a chat UI — students shouldn't have to prompt-engineer their own graduation project. The sticky refine bar at the bottom handles conversational follow-ups without taking over the screen.

<div align="center">
  <img src="docs/assets/board-ar-light.png" alt="Arabic board of 5 ideas, light theme" width="860" />
</div>

### Blueprint — supervisor-ready

Every blueprint carries thirteen sections: problem statement, why it matters, in-scope / out-of-scope, suggested architecture, tech stack, milestones by week (typically six to seven phases across 10 – 16 weeks), datasets with URLs, evaluation metrics, risks & mitigations, differentiation ideas, plus real paper and repo references — with the authoritative arXiv and GitHub URLs injected at the top of each reference list post-generation so they can never be hallucinated.

<div align="center">
  <img src="docs/assets/blueprint-ar-dark.png" alt="Arabic blueprint page, dark theme" width="860" />
</div>

The Arabic section headings (المشكلة, ليه مهمة, داخل النطاق, التقنيات, المراحل الزمنية) stay in Arabic; technical tokens (`embedding`, `FastAPI`, `python`, `transformer`, `LLM`) stay in English. This is the bilingual contract every downstream generation honors.

---

## How it works

```
┌──────────────────────────── request path ────────────────────────────┐

┌────────────────────┐   REST     ┌──────────────────────┐   ANN +     ┌──────────┐
│  Next.js 15 web    │◄─────────► │  FastAPI recommender │◄─────────── │  Qdrant  │
│  ar / en + RTL     │   JSON     │  stateless           │  filter     │          │
└────────────────────┘            └───────┬──────────────┘  top-50     └──────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │  deterministic       │
                               │  pre-score → top 20  │
                               │                      │
                               │  LLM re-rank         │
                               │  (ids validated)     │
                               │                      │
                               │  LeanCard[5] with    │
                               │  real arxiv_url +    │
                               │  real github_url     │
                               └──────────────────────┘

┌────────────────────── ingestion path ────────────────────────────────┐

 HF Daily Papers API ──┐
 arXiv REST            ├─►  normalize + dedup  ─►  multilingual encoder
 GitHub Trending       ─┘   (arxiv_id / github)    (MiniLM, 384-d, CPU)
  via Crawl4AI                      │                      │
                                    ▼                      ▼
                         ┌─────────────────────────────────────┐
                         │  Postgres (ProjectCandidate)        │
                         │  +                                  │
                         │  Qdrant (payload-indexed points)    │
                         └─────────────────────────────────────┘

 Celery beat: HF daily every 6h · arXiv nightly · GitHub weekly
 Dead-letter table for failed items · per-run IngestionRun stats
 Observability: GET /api/v1/ingest/status

┌────────────── session + infrastructure ──────────────────────────────┐

           ┌──────────┐   ┌────────────┐   ┌─────────────────┐
           │ Postgres │   │   Redis    │   │  LLM gateway    │
           │ feedback │   │ sessions + │   │                 │
           │ + runs   │   │ card cache │   │  azure  │ ollama│
           └──────────┘   └────────────┘   └─────────────────┘
```

Three clean subsystems with narrow interfaces:

1. **Ingestion.** Three pipelines land normalized `ProjectCandidate` records into Postgres and Qdrant with multilingual embeddings. HF Daily Papers carries pre-generated `ai_summary` and `ai_keywords`, so an enrichment LLM call is skipped for most records. arXiv covers the long tail via a rate-limited REST loop. A Crawl4AI scraping agent pulls GitHub's weekly Python trending page (no API exists). Celery beat schedules the three jobs at 6-hour / nightly / weekly cadences with autoretry, dead-letter capture, and per-run statistics exposed at `/api/v1/ingest/status`.

2. **Recommender.** Stateless FastAPI that converts an `IntentProfile` into a query embedding, runs an ANN + payload-filter query against Qdrant, applies a deterministic pre-score (a weighted blend of cosine similarity, quality, recency, code availability, and difficulty match), takes the top 20, and asks a small language model to re-rank them with strict id validation. The expansion endpoint pulls the real paper abstract and the real repo README before prompting the stronger model, so every blueprint is anchored in actual source material.

3. **Web.** Next.js 15 App Router, bilingual with RTL, FOUC-safe dark / light / system themes, self-hosted fonts. Server components handle the page shell; client components cover the interactive bits (form, refine bar, card actions). No client state outside what each component owns; session state lives on the server.

---

## Stack

| Layer | Tech |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2 async · Alembic · Pydantic v2 · Loguru |
| **Workers** | Celery 5 · Celery beat · autoretry with exponential backoff |
| **Data plane** | PostgreSQL 16 · Qdrant 1.16 · Redis 7 |
| **Embeddings** | `paraphrase-multilingual-MiniLM-L12-v2` — 384-dim, local CPU, cross-lingual Arabic ↔ English |
| **LLM (cloud)** | Azure OpenAI `gpt-4o-mini` (fast tier) · `gpt-4o` (smart tier) |
| **LLM (local)** | Ollama via OpenAI-compat, `llama3.2:3b` + `aya:8b` (strong Arabic) |
| **Scraping** | Crawl4AI — Apache 2.0, Playwright under the hood, Ollama-friendly |
| **Frontend** | Next.js 15 App Router · React 19 · TypeScript strict · Tailwind v4 · next-intl · Biome |
| **Type system** | Pydantic on the wire, TypeScript mirror in `lib/api.ts` |
| **Runtime** | Docker + Docker Compose |
| **CI** | GitHub Actions — backend lint / typecheck / test, frontend lint / typecheck / build / test |

---

## Quick start

Requirements: **Docker 27+**, **Docker Compose v2**. Optional: **Python 3.12** and **Node 22+** for running backend or frontend directly on the host.

```bash
git clone https://github.com/h9-tec/graduation-project-advisor.git graduation_project
# or over SSH:
# git clone git@github.com:h9-tec/graduation-project-advisor.git graduation_project

cd graduation_project
cp .env.example .env
# Open .env and paste your Azure OpenAI endpoint + key,
# or flip LLM_PROVIDER=ollama for a fully local stack.

docker compose up -d --build
```

Wait ~30 seconds for health checks, then:

| URL | What |
|---|---|
| <http://localhost:3000/en> | English landing |
| <http://localhost:3000/ar> | Arabic landing (RTL) |
| <http://localhost:8010/healthz> | Backend liveness |
| <http://localhost:8010/metrics> | Prometheus metrics |
| <http://localhost:8010/docs> | FastAPI Swagger UI |
| <http://localhost:8010/api/v1/ingest/status> | Per-source ingestion stats |
| <http://localhost:6333/dashboard> | Qdrant dashboard |

### Host port cheat sheet

Compose deliberately remaps host ports so the stack does not clash with local Postgres / Redis instances developers already run:

| Service | Host port | Container port |
|---|---|---|
| Postgres | `5433` | 5432 |
| Redis | `6380` | 6379 |
| Backend (FastAPI) | `8010` | 8000 |
| Qdrant HTTP | `6333` | 6333 |
| Qdrant gRPC | `6334` | 6334 |
| Frontend (Next.js) | `3000` | 3000 |

Inside the compose network, services speak on their container ports (e.g. `postgres:5432`, `redis:6379`, `qdrant:6333`).

---

## LLM providers

A provider-neutral gateway routes fast-tier and smart-tier calls by the `LLM_PROVIDER` env var. Switching is one setting.

### Azure OpenAI (default)

```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_SMART=gpt-4o
```

Measured latencies against a real student profile:

| Call | Tier | Latency |
|---|---|---|
| `POST /recommendations` | fast | ~ 3 s (5 cards) |
| `POST /sessions/{sid}/cards/{id}/expand` | smart | ~ 6 s (full blueprint) |

### Ollama (local)

```env
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_FAST=llama3.2:3b
OLLAMA_MODEL_SMART=aya:8b
```

Measured on an RTX 5060 Laptop (8 GB VRAM):

| Call | Model | Latency |
|---|---|---|
| `POST /recommendations` | `llama3.2:3b` | ~ 13 s |
| `POST /expand` | `aya:8b` | ~ 50 s |

`aya:8b` is chosen for the smart tier because it produces strong Arabic output alongside English.

**Running with Ollama** (tested path on Linux hosts where iptables blocks docker → host traffic):

```bash
# Keep compose infra running; start Ollama on the host.
docker compose up -d postgres redis qdrant frontend
OLLAMA_HOST=127.0.0.1:11434 ollama serve &

# Stop the dockerized backend, run uvicorn directly so it can reach Ollama.
docker compose stop backend
cd backend && source ../.venv/bin/activate
DATABASE_URL="postgresql+asyncpg://grad:grad@localhost:5433/grad" \
REDIS_URL="redis://localhost:6380/0" \
QDRANT_URL="http://localhost:6333" \
OLLAMA_URL="http://localhost:11434" \
LLM_PROVIDER=ollama \
FRONTEND_ORIGIN="http://localhost:3000" \
uvicorn api.main:app --port 8010 --reload
```

---

## API reference

All routes are under `/api/v1`. All request and response bodies are JSON. Pydantic validates on entry; the frontend mirrors the shape in `lib/api.ts`.

| Route | Verb | Purpose |
|---|---|---|
| `/recommendations` | POST | Submit an `IntentProfile`, receive 5 lean cards + a session id |
| `/sessions/{sid}` | GET | Full session state — cards + refinement count + undo stack depth |
| `/sessions/{sid}/cards` | GET | Current cards only |
| `/sessions/{sid}/cards/{card_id}/expand` | POST | Expand a card into a full blueprint (grounded in the real paper + README) |
| `/sessions/{sid}/refine` | POST | Apply a free-text refinement; returns updated cards + an assistant note |
| `/sessions/{sid}/refine/undo` | POST | Pop the most recent refinement; 400 when the stack is empty |
| `/feedback` | POST | Persist a thumbs up / down against a card (append-only, snapshot-bearing) |
| `/sessions/{sid}/saved` | GET / POST | List or add to the saved-cards shortlist |
| `/sessions/{sid}/saved/{card_id}` | DELETE | Remove a saved card |
| `/eval/dataset` | GET | Flatten recent feedback rows for the offline evaluation harness |
| `/ingest/status` | GET | Per-source last-run stats + unresolved dead-letter counts |

---

## Design philosophy

The aesthetic has a name: **Manuscript meets Production**.

- **Scholarly editorial feel.** Fraunces display + DM Sans body in Latin; Lemonada display + Lemonada body in Arabic. Size jumps are three-to-one, not one-and-a-half — a 64 px headline next to a 14 px label has more authority than two shades of middle weight.
- **Terminal minimalism.** JetBrains Mono for domain chips, arXiv ids, star counts, milestone week ranges. No filler chrome.
- **Warm ink on cream.** A dominant warm ink color (`#1a1612` light, `#f0e6d0` dark) against an aged-paper or near-black canvas. A single sharp accent — manuscript gold `#c48a1e` — never a gradient.
- **Not a chat clone.** The recommendation screen is an asymmetric board of idea cards, not a transcript. The refine bar sits quietly at the bottom. Students shouldn't have to prompt-engineer their own graduation project.
- **Direction-aware throughout.** CSS logical properties, `dir="rtl"` on the Arabic locale root, directional icons auto-flip, logos never flip. Arabic line-height is 1.9 vs 1.55 for Latin — Arabic needs the extra vertical room.

Every color is a semantically-named CSS custom property (`--color-canvas`, `--color-accent`, `--color-signal-code`, `--color-signal-paper`). Light and dark share the same semantic map; switching is a `data-theme` attribute on `<html>` plus a FOUC-safe inline boot script.

---

## Dev workflow

### Backend (on the host)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e 'backend/[dev]'

cd backend
DATABASE_URL="sqlite+aiosqlite:///./grad.db" alembic upgrade head
uvicorn api.main:app --reload
```

Tests, lint, typecheck:

```bash
cd backend
pytest tests/unit -v
ruff check . && ruff format --check .
mypy api core ingestion
```

### Frontend (on the host)

```bash
cd frontend
corepack pnpm install
corepack pnpm dev
```

Tests, lint, typecheck, production build:

```bash
cd frontend
corepack pnpm test
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm build
```

### One-shot ingestion

The three pipelines have a CLI entry point for manual runs:

```bash
cd backend && source ../.venv/bin/activate
python -m ingestion.run --source hf_daily_papers --days 30
python -m ingestion.run --source arxiv --days 3 --max-records 300
python -m ingestion.run --source github_trending --count 25
```

These are the same runners Celery beat schedules.

---

## Project layout

```
graduation_project/
├── backend/
│   ├── api/
│   │   ├── main.py                        FastAPI factory + lifespan + CORS
│   │   ├── routes/
│   │   │   ├── recommendations.py         POST /recommendations, /expand, /refine, /refine/undo, GET /sessions/{sid}
│   │   │   ├── feedback.py                POST /feedback, GET/POST/DELETE /saved, GET /eval/dataset
│   │   │   └── ingest_status.py           GET /ingest/status
│   │   └── schemas/                       IntentProfile · LeanCard · Blueprint · RefineRequest (Pydantic)
│   ├── core/
│   │   ├── settings.py                    Pydantic Settings — single source of env truth
│   │   ├── logging.py                     Loguru JSON sink + bind_context helper
│   │   ├── session_store.py               Redis-backed profile + cards + refinement stack + saved hash
│   │   ├── db/                            SQLAlchemy base + ProjectCandidate, Feedback, IngestionRun, DeadLetter
│   │   ├── embeddings/                    sentence-transformers encoder + async Qdrant helpers
│   │   ├── llm/
│   │   │   ├── azure.py                   AsyncAzureOpenAI JSON-mode helper
│   │   │   ├── ollama.py                  AsyncOpenAI pointed at Ollama /v1
│   │   │   ├── gateway.py                 Provider-neutral chat_json(tier="fast"|"smart")
│   │   │   └── prompts.py                 Bilingual rec + grounded-blueprint + refine prompts
│   │   └── recommendation/
│   │       ├── retrieve.py                Build filter, ANN top-50, deterministic pre-score → top 20
│   │       └── context.py                 Fetch real README + full abstract before expansion prompts
│   ├── ingestion/
│   │   ├── pipelines/                     hf_papers.py, arxiv.py, github_trending.py (Crawl4AI)
│   │   ├── normalize.py                   NormalizedCandidate, content_hash, quality_score
│   │   ├── upsert.py                      Dedup + embed + atomic Postgres + Qdrant upsert
│   │   ├── runner.py                      Per-run IngestionRun row + per-item dead-letter capture
│   │   ├── celery_app.py                  Celery app + beat schedule (6h / nightly / weekly)
│   │   ├── tasks.py                       Celery tasks with autoretry + backoff
│   │   └── run.py                         One-shot CLI
│   ├── alembic/                           4 migrations: candidates · feedback · ingestion_runs + dead_letter
│   ├── tests/                             pytest-asyncio, testcontainers-ready
│   ├── Dockerfile                         Multi-stage, non-root app user
│   └── pyproject.toml                     Hatchling + ruff + mypy strict + pytest-asyncio
├── frontend/
│   ├── app/[locale]/
│   │   ├── layout.tsx                     Bilingual html/dir, FOUC-safe theme boot, font pipeline
│   │   ├── page.tsx                       Asymmetric editorial landing
│   │   ├── onboard/page.tsx               The only form in the app
│   │   ├── board/[sid]/page.tsx           Board with sticky RefineBar
│   │   ├── blueprint/[sid]/[cardId]/      Grounded blueprint page
│   │   └── saved/page.tsx                 Saved shortlist + Compare-3
│   ├── components/
│   │   ├── app-header.tsx                 Locale + theme toggles + Saved link
│   │   ├── onboard-form.tsx               Domain chips · skill · sliders · textarea
│   │   ├── idea-card.tsx                  Lean card with varied masonry heights
│   │   ├── card-actions.tsx               Thumbs + save, optimistic, localStorage-backed
│   │   ├── refine-bar.tsx                 Sticky glass panel with Refine + Undo + counter
│   │   ├── board-view.tsx                 Hydrates the full session on mount
│   │   ├── saved-view.tsx                 Grid + Compare toggle + side-by-side panel
│   │   ├── blueprint-view.tsx             13-section artifact renderer
│   │   └── atmospheric-bg.tsx             SVG noise + corner radial gradient
│   ├── lib/
│   │   ├── api.ts                         Typed fetch client mirroring Pydantic schemas
│   │   └── fonts.ts                       next/font — Fraunces, DM Sans, Lemonada, JetBrains Mono
│   ├── messages/{ar,en}.json              All i18n strings
│   ├── middleware.ts                      next-intl locale routing
│   └── i18n.ts                            next-intl config
├── docker-compose.yml                     postgres · qdrant · redis · backend · celery × 2 · frontend
├── .github/workflows/                     backend-ci.yml, frontend-ci.yml
├── docs/assets/                           Screenshots used by this README
├── .env.example                           Every env key, commented
└── README.md
```

---

## Security notes

- Anonymous sessions only — no passwords, no OAuth, no PII beyond an optional email (not enabled by default).
- `.env` is gitignored; `.env.example` ships placeholder values only.
- CORS locked to `FRONTEND_ORIGIN`, never `*`.
- Free-text fields (`interests_text`, refine messages) are length-capped at 500 characters and wrapped in `<untrusted_input>` markers inside the system prompt.
- Pydantic validates every payload at the API boundary; TypeScript types mirror the shape on the client.
- No user-supplied URLs are fetched server-side (SSRF guard). The only outbound URLs the ingestion layer reaches are arXiv, Hugging Face, and GitHub — all over HTTPS with an allow-list.
- Dependencies scanned by `pip-audit` and `npm audit` in CI; Dependabot watches `main`.

---

## Credits

Built by **Hesham Haroon**. Part of an Arabic-first AI systems portfolio — see [`al-muwatta-ai`](https://github.com/h9-tec) and [`dhakira`](https://github.com/h9-tec) for related work.

## License

Private / TBD.
