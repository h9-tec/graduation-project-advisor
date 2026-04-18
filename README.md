# Graduation Project Advisor

**Helps Egyptian CS / AI / SWE undergraduates pick a production-grade graduation project — grounded in real research papers and real GitHub repos, delivered as ranked idea cards that expand into supervisor-ready blueprints.**

Bilingual from day one. Arabic-first UX, English-parity toggle, full RTL. Locally-typed, locally-served; no tracking, no accounts, no PII.

<p align="center">
  <img src="docs/assets/landing-ar-dark.png" alt="Arabic landing page, dark manuscript theme" width="820" />
</p>

> **Status:** Scaffold and functional LLM-backed UI shipped · **ingestion pipeline shipped** — 997 records in Qdrant across 3 sources, retrieval-first RAG recommender, blueprint output grounded to the real retrieved paper and repo.

---

## The problem

Every senior-year CS student in Egypt hits the same wall: *what should my graduation project be?* The usual answers are shallow ("build a todo app with auth"), disconnected from research (no paper grounding), or overwhelming (raw arXiv feeds, endless GitHub trending). Supervisors don't have the hours to hand-tailor ideas to every student's background, timeline, and interests.

## The solution

One form. Five minutes. Five grounded project ideas, each with a research hook and a stack hook, ranked for your skill level and time budget. Any card expands — with one click — into a full production-grade blueprint: problem statement, scope boundaries, suggested architecture, milestones by week, datasets, evaluation metrics, risks, and how to stand out. Bilingual reasoning (technical terms stay English, the "why this fits you" is in the student's language).

Under the hood it's an **indexed-RAG pipeline** over a live corpus:

- **997 real papers + repos** in Qdrant (695 HF Daily Papers · 290 arXiv · 12 GitHub Trending)
- **multilingual embeddings** (`paraphrase-multilingual-MiniLM-L12-v2`, 384-d) so an Arabic query retrieves English papers natively
- **deterministic pre-score** before any LLM sees the candidates (0.5 · cosine + 0.2 · quality + 0.1 · recency + 0.1 · has-code + 0.1 · difficulty-match)
- **LLM re-rank with anti-hallucination ids** — the re-ranker is constrained to pick from the retrieved set; any fabricated id is dropped
- **blueprint URL injection** — the expand endpoint prepends the retrieved paper's real arxiv/github URL to the blueprint's reference list, so every supervisor-ready artifact cites something that genuinely exists

Wrapped in a clean-theme editorial UI that deliberately doesn't look like another ChatGPT clone.

> **Why not Papers-With-Code?** Meta sunset PWC on 2025-07-24. We pivoted to **HuggingFace Daily Papers** — which already carries `githubRepo`, `ai_summary`, and `ai_keywords` per record — plus arXiv (REST) and GitHub Trending (scraped via Crawl4AI). Addendum spec linked above.

---

## Screens

### Onboarding — the only form in the app

Domain chips, skill level, months available, team size, preferred stack, interests free-text, topics to avoid. Estimated completion: **under a minute**. No tracking, no login, no account. The profile lives in the server session (Redis, 6-hour TTL) and is discarded when you close the tab.

<p align="center">
  <img src="docs/assets/onboard-ar-dark.png" alt="Arabic onboarding form, dark theme" width="820" />
</p>

### The board — ranked cards, not a chat transcript

Five cards, asymmetric layout, every card grounds itself on a named research area and a named stack. Click any card to expand into a full blueprint. Intentionally *not* a chat UI — students don't need to "prompt engineer" their own grad project.

<p align="center">
  <img src="docs/assets/board-ar-light.png" alt="Arabic board of 5 ideas, light theme" width="820" />
</p>

### Blueprint — supervisor-ready

Every blueprint has: problem statement, why it matters, in-scope / out-of-scope, suggested architecture, tech stack, milestones by week (typically 6–7 phases across 10–16 weeks), datasets with URLs, evaluation metrics, risks & mitigations, "how to stand out" (3+ differentiation ideas), and real paper / repo references.

---

## Architecture

```
 ┌──────────────────────────── request path ────────────────────────────┐

 ┌────────────────────┐   REST     ┌──────────────────────┐   ANN +     ┌──────────┐
 │  Next.js 15 web    │◄─────────► │   FastAPI recommender│◄─────────── │  Qdrant  │
 │  ar / en + RTL     │   JSON     │   stateless          │  top-50     │  997 pts │
 └────────────────────┘            └───────┬──────────────┘  filter     └──────────┘
         ▲                                 │
         │                                 ▼
         │                       ┌──────────────────┐
         │                       │  pre-score →     │
         │                       │  top 20 → LLM    │
         │                       │  re-rank (guard: │
         │                       │  ids ∈ retrieved)│
         │                       └───────┬──────────┘
         │                               ▼
         │                     ┌──────────────────┐
         │                     │  LeanCard[5]     │
         │                     │  with arxiv_url  │
         │                     │  + github_url    │
         │                     └──────────────────┘

 ┌───────────────────────── ingestion path ─────────────────────────────┐

  HF Daily Papers API ───────┐
  arXiv REST (feedparser)    ├──► normalize (dedup by arxiv_id / gh_url)
  GitHub Trending (Crawl4AI) ─┘     │
                                    ▼
                          ┌─ multilingual MiniLM embedder ─┐
                          │    (local CPU, 384-dim)        │
                          └───────────┬────────────────────┘
                                      ▼
                     ┌─ Postgres (ProjectCandidate rows)   ─┐
                     │  + Qdrant payload-indexed points    │
                     └──────────────────────────────────────┘

 ┌────────────────────── session + infra plane ─────────────────────────┐

                      ┌──────────┐   ┌────────────┐   ┌─────────────────┐
                      │ Postgres │   │   Redis    │   │  LLM gateway    │
                      │ candidates│  │ sessions + │   │                 │
                      │ + users  │   │ card cache │   │  azure  │ ollama│
                      └──────────┘   └────────────┘   └─────────────────┘
```

Three clean subsystems with narrow interfaces:

1. **Ingestion** — three pipelines land normalized `ProjectCandidate` records into Postgres + Qdrant with multilingual embeddings. HF Daily Papers carries pre-generated `ai_summary` and `ai_keywords` so we skip an LLM enrichment call entirely for those records. arXiv fills the long tail. Crawl4AI scrapes the weekly Python trending page (GitHub has no trending API).
2. **Recommender** *(FastAPI, stateless)* — form → Qdrant filter+ANN → deterministic pre-score → LLM re-rank with id-validation → lean cards. One-click blueprint expansion injects the retrieved paper's real arxiv/github URL into the output. Redis-backed session cache.
3. **Web app** *(Next.js 15 App Router)* — landing + onboarding + board + blueprint. Bilingual / RTL. Light, dark, and system themes with FOUC-safe boot.

---

## Stack

| Layer | Tech |
|---|---|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · Pydantic v2 · Loguru |
| **Workers** | Celery 5 · Celery beat (nightly ingestion jobs, Phase 1+) |
| **Data** | PostgreSQL 16 · Qdrant 1.16 · Redis 7 |
| **LLM — cloud** | Azure OpenAI `gpt-4o-mini` (fast tier) · `gpt-4o` (smart tier) |
| **LLM — local** | Ollama via OpenAI-compat: `llama3.2:3b` (fast) · `aya:8b` (multilingual smart) |
| **Embeddings** | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (local CPU, 384-d) |
| **Frontend** | Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind v4 · next-intl · Biome |
| **Type system** | Server-side Pydantic, frontend `lib/api.ts` mirrors the schemas |
| **Container runtime** | Docker + Docker Compose |
| **CI** | GitHub Actions: `backend-ci.yml` and `frontend-ci.yml` (lint · typecheck · test) |

---

## Quick start

Requirements: Docker 27+, Docker Compose v2. Optional: Python 3.12 and Node 22+ for running backend/frontend outside containers.

```bash
git clone <repo-url> graduation_project
cd graduation_project
cp .env.example .env
# Edit .env and paste your Azure OpenAI endpoint + key (or flip LLM_PROVIDER=ollama)
docker compose up -d --build
```

Wait ~30 seconds for healthchecks, then:

| URL | What |
|---|---|
| <http://localhost:3000/en> | English landing |
| <http://localhost:3000/ar> | Arabic landing (RTL) |
| <http://localhost:8010/healthz> | Backend liveness |
| <http://localhost:8010/metrics> | Prometheus metrics |
| <http://localhost:8010/docs> | FastAPI Swagger UI |
| <http://localhost:6333/dashboard> | Qdrant dashboard |

---

## Host port cheat sheet

Compose deliberately remaps host ports off the usual defaults to avoid clashing with a dev's existing local Postgres / Redis:

| Service | Host port | Container port | Why remapped |
|---|---|---|---|
| Postgres | `5433` | 5432 | Dev likely has a 5432 already |
| Redis | `6380` | 6379 | Dev likely has a 6379 already |
| Backend (FastAPI) | `8010` | 8000 | 8000/8001 were bound on the test machine |
| Qdrant HTTP | `6333` | 6333 | — |
| Qdrant gRPC | `6334` | 6334 | — |
| Frontend (Next.js) | `3000` | 3000 | — |

**Inter-service calls inside the compose network always use the container ports** (e.g. `postgres:5432`, `redis:6379`, `qdrant:6333`).

---

## LLM providers

The gateway abstracts which model you're talking to. Flip `LLM_PROVIDER` in `.env`.

### Azure OpenAI *(default, recommended for production)*

```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_SMART=gpt-4o
```

Measured latencies against a real Egyptian-CS-student profile:

| Call | Model | Time | Output |
|---|---|---|---|
| `/recommendations` (5 cards) | `gpt-4o-mini` | ~3 s | ~1.5 KB JSON |
| `/sessions/{sid}/cards/{id}/expand` | `gpt-4o` | ~6 s | ~3–5 KB JSON |

### Ollama *(local, no Azure spend, no rate limits)*

```env
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL_FAST=llama3.2:3b
OLLAMA_MODEL_SMART=aya:8b
```

`aya:8b` is Cohere's multilingual model and produces strong Arabic output alongside English. Measured on an RTX 5060 Laptop (8 GB VRAM):

| Call | Model | Time |
|---|---|---|
| `/recommendations` (5 cards) | `llama3.2:3b` | ~13 s |
| `/expand` (full blueprint) | `aya:8b` | ~50 s |

**Running with Ollama — recommended path**

```bash
# 1. Keep compose infra running (postgres, redis, qdrant, frontend)
docker compose up -d postgres redis qdrant frontend

# 2. Start Ollama on the host
OLLAMA_HOST=127.0.0.1:11434 ollama serve &

# 3. Stop the dockerized backend; run uvicorn on the host so it can
#    reach Ollama (docker→host traffic needs an iptables allow-rule
#    on this machine, so the host-run path is the tested one).
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

> **Heads-up on docker→host networking:** if you run the backend inside compose with `LLM_PROVIDER=ollama`, the container needs to reach the host's Ollama. On Docker Desktop this works out of the box via `host.docker.internal`. On bare Ubuntu with default firewall rules, docker→host traffic is silently dropped — run the backend on the host (as above) or add the iptables allow-rule for your bridge network.

---

## Design philosophy

The design direction has a name: **Manuscript meets Production**. Three ideas collide on purpose.

- **Papers** — editorial, rational typography. Fraunces (Latin) + Lemonada (Arabic). Size jumps are 3×, not 1.5×.
- **Code** — terminal minimalism. JetBrains Mono for domain chips, arXiv IDs, stars, milestone weeks. No filler chrome.
- **Arabic-first** — dominant warm ink on cream (light) or warm ink on near-black (dark). A single sharp accent — manuscript gold `#c48a1e`. Direction-aware icons, logical CSS properties throughout. Arabic line-height 1.9 vs Latin 1.55 because Arabic needs the room.

It's deliberately *not* a ChatGPT clone. The recommendation screen is a **board of idea cards**, not a chat transcript. Chat refinement sits quietly in a dismissable bottom rail (Phase 3). The blueprint expands into its own full-page artifact — the kind of document a student can hand to their supervisor.

Every color is a CSS custom property with a semantic name (`--color-canvas`, `--color-accent`, `--color-signal-code`, `--color-signal-paper`). Dark and light themes share the same semantic map; swapping is a `data-theme` attribute on `<html>` and a FOUC-safe boot script.

---

## Dev workflow

### Backend (outside Docker)

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
pytest tests/unit -v                          # 8 tests, async-aware
ruff check . && ruff format --check .
mypy api core ingestion                       # strict mode
```

### Frontend (outside Docker)

```bash
cd frontend
corepack pnpm install              # corepack ships with Node 16+; no global pnpm needed
corepack pnpm dev                  # Next.js dev server on :3000
corepack pnpm test                 # Vitest — 3 tests, jsdom
corepack pnpm lint                 # Biome
corepack pnpm typecheck            # tsc --noEmit, strict
corepack pnpm build                # production Next.js build
```

### End-to-end (the real flow)

The app has been manually validated end-to-end with Playwright in both locales. The golden path is:

1. `GET /{locale}` — landing
2. Click CTA → `GET /{locale}/onboard`
3. Fill form, click submit → `POST /api/v1/recommendations` (~3 s with Azure, ~13 s with Ollama)
4. Redirect to `/{locale}/board/{sid}` — render 5 cards
5. Click "Expand blueprint" on a card → `POST /api/v1/sessions/{sid}/cards/{id}/expand` (~6 s / ~50 s)
6. Render full blueprint with 13 sections

---

## Project layout

```
graduation_project/
├── backend/
│   ├── api/
│   │   ├── main.py                        FastAPI factory + lifespan + CORS
│   │   ├── routes/recommendations.py      POST /recommendations, GET cards, POST expand
│   │   └── schemas/                       IntentProfile · LeanCard · Blueprint (pydantic)
│   ├── core/
│   │   ├── settings.py                    Pydantic Settings — all env in one place
│   │   ├── logging.py                     Loguru JSON sink + bind_context helper
│   │   ├── session_store.py               Redis-backed profile + cards + blueprint cache
│   │   └── llm/
│   │       ├── azure.py                   AsyncAzureOpenAI JSON-mode helper
│   │       ├── ollama.py                  AsyncOpenAI pointed at Ollama /v1
│   │       ├── gateway.py                 provider-neutral chat_json(tier='fast'|'smart')
│   │       └── prompts.py                 bilingual rec + blueprint system/user prompts
│   ├── ingestion/celery_app.py            Celery skeleton (Phase 1+ populates beat schedule)
│   ├── alembic/                           migrations (starts with an empty initial migration)
│   ├── tests/unit/                        8 tests — settings, logging, health, metrics
│   ├── Dockerfile                         multi-stage, non-root app user
│   └── pyproject.toml                     hatchling, ruff, mypy strict, pytest-asyncio
├── frontend/
│   ├── app/[locale]/
│   │   ├── layout.tsx                     bilingual html/dir, FOUC-safe theme boot
│   │   ├── page.tsx                       asymmetric editorial landing
│   │   ├── onboard/page.tsx               OnboardForm (client)
│   │   ├── board/[sid]/page.tsx           BoardView (client; fetches cards)
│   │   └── blueprint/[sid]/[cardId]/      BlueprintView (client; fetches expansion)
│   ├── components/
│   │   ├── app-header.tsx                 locale + theme toggles (localStorage)
│   │   ├── onboard-form.tsx               domain chips · skill · sliders · textarea
│   │   ├── idea-card.tsx                  lean card with varied masonry heights
│   │   ├── blueprint-view.tsx             full 13-section artifact
│   │   └── atmospheric-bg.tsx             SVG noise + corner radial gradient
│   ├── lib/
│   │   ├── api.ts                         typed fetch client (IntentProfile → LeanCard → Blueprint)
│   │   └── fonts.ts                       next/font — Fraunces · DM Sans · Lemonada · JetBrains Mono
│   ├── messages/{ar,en}.json              all i18n strings
│   ├── app/globals.css                    manuscript color tokens (light + dark)
│   ├── middleware.ts                      next-intl locale routing (/ar, /en)
│   └── i18n.ts                            next-intl config
├── docker-compose.yml                     postgres · qdrant · redis · backend · celery × 2 · frontend
├── docs/
│   └── assets/                            screenshots
├── .github/workflows/                     backend-ci.yml · frontend-ci.yml
├── .env.example                           all required env keys, commented
└── README.md
```

---

## Roadmap

| Phase | Status | Gist |
|---|---|---|
| **0. Foundations** | Done | Repo scaffold, compose, FastAPI skeleton, bilingual Next.js, CI |
| **+. Functional MVP** | Done | Azure + Ollama LLM gateway, onboarding form, LLM-backed board + blueprint |
| **1. Ingestion backbone** | Next | arXiv (OAI-PMH) + HF Papers + embeddings → Qdrant |
| **2. Linking + corpus** | Planned | PWC paper↔repo linking, GitHub search API, LLM enrichment |
| **3. True RAG pipeline** | Planned | Deterministic pre-score → LLM re-rank over retrieved candidates |
| **4. Chat refinement** | Planned | "more RL, less infra" → profile diff → new board |
| **5. Feedback + save** | Planned | Thumbs up/down, saved cards, compare-3 view |
| **6. Polish + production** | Planned | Caddy TLS, VPS deploy, UptimeRobot, LLM eval harness |

---

## Troubleshooting

**`docker compose up` fails with `port already allocated`**
Something on the host already uses 5432 / 6379 / 8000. Compose remaps to 5433 / 6380 / 8010 — if those clash too, edit `docker-compose.yml`.

**Qdrant healthcheck fails with `wget: not found`**
The qdrant image doesn't ship `wget`. Compose uses `bash </dev/tcp/localhost/6333` instead. If that fails in your fork, drop the healthcheck and use `depends_on: qdrant: { condition: service_started }`.

**Celery beat crashes with `Permission denied: 'celerybeat-schedule'`**
The container runs as the non-root `app` user and `/app` is read-only to that user. Compose already passes `--schedule=/tmp/celerybeat-schedule` to work around it.

**Backend errors with `ModuleNotFoundError: No module named 'core'`**
You ran `uvicorn` from the repo root. Either `cd backend` first, or `uvicorn api.main:app --app-dir backend`.

**Frontend hot reload is sluggish inside Docker on macOS**
Known Next.js + macOS bind-mount issue. Run the frontend on the host instead: `cd frontend && corepack pnpm dev`.

**Arabic text renders LTR**
Confirm you're visiting `/ar` directly (not `/`) and that `<html dir="rtl" lang="ar">` is present in DevTools. If missing, check `frontend/middleware.ts` is loading.

**`Hydration failed because the server rendered HTML didn't match the client`**
A browser extension (most commonly Grammarly, LastPass, ColorZilla) is injecting attributes onto `<body>`. Already handled: `<body suppressHydrationWarning>`.

**`corepack enable` fails without sudo**
Use `corepack pnpm <cmd>` directly — it runs pnpm through corepack without needing to enable the global shim.

**Ollama requests from dockerized backend time out**
Default Ubuntu iptables blocks docker→host traffic. Run the backend on the host (see "Running with Ollama"), or add an allow-rule for your compose bridge to `host:11434`.

---

## Tests

```
backend/  8 tests (async-aware, asyncio_mode=auto)
frontend/ 3 tests (Vitest + Testing Library, jsdom)
```

CI runs lint + typecheck + tests on every PR touching `backend/**` or `frontend/**`.

---

## Security notes

- Anonymous sessions only — no passwords, no OAuth, no PII beyond an optional email (Phase 6).
- `.env` is gitignored; `.env.example` ships placeholders only.
- CORS locked to `FRONTEND_ORIGIN`, never `*`.
- All user text (`interests_text`, chat refinements) is length-capped and wrapped in `<untrusted_input>` markers in the system prompt.
- Pydantic validates everything at the API boundary; Zod-adjacent typing in the frontend.
- No user-supplied URLs are fetched server-side (SSRF guard).

---

## License

Private / TBD.

---

## Credits

Built by Hesham Haroon. Part of a broader Arabic-first AI systems portfolio — see `al-muwatta-ai` and `dhakira` for related work.
