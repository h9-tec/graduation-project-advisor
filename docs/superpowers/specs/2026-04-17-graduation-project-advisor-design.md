# Graduation Project Advisor — Design Spec

- **Status:** Approved (brainstorming phase complete)
- **Date:** 2026-04-17
- **Owner:** Hesham Haroon
- **Target users:** Egyptian undergraduate CS / AI / SWE students
- **Goal:** Help students pick a production-grade graduation project grounded in real papers and real GitHub repos, delivered as a browsable board of ideas with on-demand full blueprints.

---

## 1. Problem statement

Egyptian CS students repeatedly face a painful bottleneck in their senior year: "what should my graduation project be?" The usual answers are shallow (generic "build a todo app with auth" lists), disconnected from research (no grounding in current papers), or overwhelming (raw arXiv feeds, endless GitHub trending). Supervisors rarely have time to hand-tailor ideas to a student's background, timeline, and interests.

This system produces a short, ranked, explanation-rich list of project ideas tailored to a student's profile, each grounded in a specific paper and/or GitHub repository. On demand, each idea expands into a full production-grade blueprint (architecture, milestones, datasets, metrics, risks, differentiation tips) the student can hand to a supervisor.

## 2. Success criteria

- A student completes onboarding → receives 5 grounded, distinct, ranked lean cards in under 3 seconds.
- Each card cites a real paper and/or a real GitHub repository (no hallucinated titles).
- Clicking "expand" returns a full blueprint in under 8 seconds.
- The UI is fully bilingual (ar / en) with correct RTL and typography.
- The production deploy costs under ~$100/month at 200 DAU.
- LLM eval recall@5 on the curated 50-pair dataset ≥ 0.7 at launch; regression guard alerts on ≥ 10% drop week-over-week.

## 3. Scope locked in during brainstorming

| Decision | Value |
|---|---|
| Target users | CS / AI / SWE undergrads |
| Language strategy | Bilingual (ar + en) toggle, full parity |
| Input method | Hybrid: 5-card form → chat refinement |
| Data sources | arXiv + HF Papers + Papers-With-Code + GitHub (linked via PWC) |
| Output shape | Tiered: lean card → blueprint on demand (starter-kit zip is v2, out of scope) |
| Delivery | Web app v1, channel-agnostic backend so a Telegram adapter is a later v2 add-on |
| Recommendation engine | Indexed RAG (filter → ANN → deterministic pre-score → LLM re-rank) |

Explicitly **out of v1 scope**: accounts/passwords/OAuth, team features, paid tier, WhatsApp/Telegram bot, starter-kit zip generation, supervisor dashboard, multi-tenant universities, Arabic-source papers, fine-tuned or locally-served chat model.

## 4. Architecture overview

Three clean subsystems, narrow interfaces between them:

```
┌────────────────────┐   REST    ┌──────────────────────┐   HTTP/gRPC   ┌──────────┐
│  Next.js 15 web    │◄────────► │   FastAPI recommender│◄────────────► │  Qdrant  │
│  (ar/en + RTL)     │  JSON     │   (stateless svc)    │   filter+ANN  │          │
└────────────────────┘           └──────────┬───────────┘               └──────────┘
                                            │
                            ┌───────────────┼────────────────┐
                            ▼               ▼                ▼
                      ┌──────────┐   ┌────────────┐   ┌─────────────┐
                      │ Postgres │   │   Redis    │   │ LLM Gateway │
                      │ sessions │   │ rate+cache │   │ (multi-prov)│
                      │ feedback │   │            │   │ Azure prim. │
                      └──────────┘   └────────────┘   └─────────────┘
                            ▲
                            │ populates
                   ┌────────┴─────────┐
                   │ Ingestion worker │  (Celery-beat, nightly)
                   │  arXiv / HF /    │
                   │  PWC / GitHub    │
                   └──────────────────┘
```

Responsibilities:
1. **Ingestion worker** (offline, nightly): pulls sources, normalizes into unified `ProjectCandidate`, LLM-enriches, embeds, upserts to Qdrant + Postgres (outbox-protected).
2. **Recommender service** (online, stateless FastAPI): form → filter → semantic retrieve → LLM re-rank → lean cards; blueprint expansion; chat refinement.
3. **Web app** (Next.js 15 App Router): landing + onboarding form + recommendation board + chat refinement + blueprint view. Bilingual with RTL, mobile-first.

## 5. Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy async + Alembic + Pydantic |
| Vector DB | Qdrant 1.16+ (using `query_points` API) |
| Relational DB | PostgreSQL (prod), SQLite (dev) |
| Cache / queue | Redis + Celery + Celery beat |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384-dim, local CPU, multilingual ar↔en) |
| LLM (re-rank + lean card) | Azure OpenAI `gpt-4o-mini` |
| LLM (blueprint expand) | Azure OpenAI `gpt-4o` |
| LLM fallback | Ollama (local) for dev; pluggable gateway |
| Frontend | Next.js 15 App Router + React 19 |
| CSS | Tailwind v4 + RTL plugin, CSS logical properties |
| Components | shadcn/ui primitives, heavily re-themed (not default theme) |
| i18n | next-intl, `/ar` and `/en` locale segments |
| Client state | Zustand (client) + TanStack Query (server state) |
| Forms | React Hook Form + Zod |
| Motion | Framer Motion (spring easing) |
| Auth v1 | Signed HTTP-only anonymous cookie sessions — no passwords |
| Reverse proxy / TLS | Caddy (auto-TLS) |
| Deploy | Docker Compose on a single Hetzner-class VPS |

Azure configuration surface:

```env
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_FAST=gpt-4o-mini
AZURE_OPENAI_DEPLOYMENT_SMART=gpt-4o
LLM_PROVIDER=azure
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

## 6. Data sources and ingestion

### 6.1 Sources

| Source | API | Cadence | Filter |
|---|---|---|---|
| arXiv | OAI-PMH | Nightly 48h delta | Categories `cs.CL cs.CV cs.LG cs.AI cs.IR cs.RO cs.NE cs.HC`, last 24 months |
| Hugging Face Papers | `huggingface.co/api/daily_papers` | Nightly | Curated daily list |
| Papers-With-Code | `paperswithcode.com/api/v1/papers/{arxiv_id}/repositories/` | Nightly per arXiv id | Link paper↔repo |
| GitHub Search API | `/search/repositories` | Weekly full + daily trending | Topics: `machine-learning deep-learning nlp computer-vision llm rag agent diffusion robotics`, `stars:>200`, `pushed:>2024-01-01` |
| GitHub Trending (optional) | HTML scrape of `github.com/trending` | Daily | Python, weekly window, top 25 |

Initial backfill target: ~10,000 high-quality candidates. Steady state adds ~500/day.

### 6.2 Unified `ProjectCandidate` record (Postgres)

```python
class ProjectCandidate(Base):
    id: UUID
    source_type: Literal["paper_with_code", "paper_only", "repo_only"]
    arxiv_id: str | None              # dedup key 1
    github_url: str | None            # dedup key 2
    title: str
    abstract: str | None
    readme_summary: str | None        # LLM-generated during ingestion
    domains: list[str]                # LLM-tagged: ["nlp", "rag", "arabic"]
    difficulty_estimated: Literal["beginner", "intermediate", "advanced"]
    difficulty_level: int             # 1/2/3 mirror of difficulty_estimated, for range filters
    has_code: bool
    stars: int
    citations: int | None
    published_at: date
    last_github_push: datetime | None
    code_language: str | None
    quality_score: float              # f(stars, citations, recency, has_code)
    raw_metadata: JSONB
    ingested_at, last_updated_at: datetime
```

### 6.3 Linking, deduplication, quality gate

- **Linking**: PWC API (primary) → regex-scan arXiv abstract for `github.com/...` (secondary) → GitHub README scan for `arXiv:XXXX.XXXXX` (tertiary).
- **Dedup**: `arxiv_id` primary key, else `github_url`, else `(normalized_title, first_author)` fuzzy match.
- **Quality gate**: repos need stars ≥ 50 OR a linked paper; papers need an abstract + at least one cs.* category; non-English titles/abstracts dropped at ingestion.

### 6.4 LLM enrichment (during ingestion)

One batched `gpt-4o-mini` call per new candidate returns `(domains, difficulty, readme_summary)` in a single structured call. Pydantic-parsed, cached. Cost: ~$0.001/record → ~$10 for the 10k backfill, ~$0.50/day steady state.

### 6.5 Embedding strategy

- Text embedded: `f"{title}\n\n{abstract or readme_summary}"`, truncated to 512 tokens.
- Model: local `paraphrase-multilingual-MiniLM-L12-v2` (384-dim).
- Re-embed only when title/abstract/readme_summary changes.

### 6.6 Qdrant collection schema

```
collection: project_candidates
vector: size=384, distance=Cosine
payload (indexed):
  domains: keyword
  difficulty_estimated: keyword     # for display
  difficulty_level: int             # 1/2/3, for range filters (<=, <, etc.)
  has_code: bool
  published_year: int
  source_type: keyword
  quality_score: float
payload (non-indexed, for card rendering):
  title, arxiv_url, github_url, stars, citations
```

Point ID = Postgres row UUID. Outbox pattern keeps Postgres and Qdrant in sync: Qdrant upsert only after successful Postgres commit; retries from outbox on Qdrant failure.

### 6.7 Scheduling

Celery beat runs these jobs. All workers are idempotent (upsert by source key, resume-safe mid-batch); a `dead_letter` table logs failures per source for re-run.

| Job | Schedule | Notes |
|---|---|---|
| `pull_arxiv` | Nightly 03:00 UTC | 48 h delta |
| `pull_hf_papers` | Nightly 03:10 UTC | Daily curated list |
| `refresh_pwc_links` | Nightly 03:20 UTC | Links newly ingested arXiv ids to repos |
| `refresh_github_trending` | Nightly 03:30 UTC | Daily trending + recently-updated repos we already track |
| `refresh_github_full` | **Sunday** 04:00 UTC | Full topic re-scan (`stars:>200`, pushed filter) — slow & rate-limit-heavy, so weekly only |
| `run_llm_enrichment` | Nightly 03:45 UTC | Processes any records missing `domains`/`difficulty_estimated`/`readme_summary` |

### 6.8 Storage and cost

- Storage: ~150 MB at 10k records (raw + embeddings).
- LLM enrichment: one-time ~$10; ongoing ~$0.50/day.
- Embedding compute: CPU-local, ~2 ms/record; 10k records ≈ 20 seconds.

## 7. Recommendation pipeline

### 7.1 Public API

```
POST /api/v1/sessions                         → {session_id, csrf_token}
POST /api/v1/recommendations                  → body: IntentProfile, returns LeanCard[5]
POST /api/v1/recommendations/{id}/expand      → returns Blueprint
POST /api/v1/sessions/{sid}/refine            → body: {message}, updates IntentProfile, returns LeanCard[5] + assistant_msg
POST /api/v1/sessions/{sid}/refine/undo       → reverts to previous IntentProfile version, returns LeanCard[5]
POST /api/v1/feedback                         → body: {rec_id, reaction}
GET  /api/v1/sessions/{sid}/saved             → saved cards
POST /api/v1/sessions/{sid}/saved             → save a card
GET  /healthz                                 → liveness
GET  /metrics                                 → Prometheus format
```

### 7.2 `IntentProfile` contract

```python
class IntentProfile(BaseModel):
    language: Literal["ar", "en"]
    domains: list[Literal["nlp","cv","rl","mlops","agents","rag","robotics","audio",
                          "timeseries","security","iot","web","mobile","data_engineering"]]
    skill_level: Literal["beginner", "intermediate", "advanced"]
    months_available: int = Field(ge=2, le=12)
    team_size: int = Field(ge=1, le=5)
    preferred_stacks: list[str]
    interests_text: str = Field(max_length=500)
    requires_code_reference: bool = True
    avoid: list[str] = []
```

### 7.3 Five-stage retrieval

Difficulty is stored in Qdrant as an indexed **integer** (`difficulty_level`) derived from the `difficulty_estimated` enum during ingestion: `beginner=1`, `intermediate=2`, `advanced=3`. This makes range filters trivial.

1. **Filter build** from profile: `domains IN profile.domains`, `difficulty_level <= skill_level_int + 1` (where `skill_level_int` uses the same 1/2/3 mapping), `has_code=true` if `requires_code_reference`, `published_year >= 2022`.
2. **ANN top-50** from Qdrant (cosine over the intent-profile-derived query vector).
3. **Deterministic pre-score** → keep top-20:
   `score = 0.5·cos + 0.2·quality + 0.1·recency + 0.1·has_code + 0.1·difficulty_match`
4. **LLM re-rank** (`gpt-4o-mini`, structured JSON) — picks top-5, writes 2–3 sentence `why_fit` in the chosen language, estimates `est_weeks` and `difficulty_verdict`.
5. **Anti-hallucination validation**: any returned `id` not in the input 20 is rejected — never serve fabricated titles.

### 7.4 Re-rank prompt (sketch)

```
SYSTEM: You are a graduation-project advisor for Egyptian CS students.
Given a student profile and 20 candidate projects, pick the 5 best-fit
projects and rank them. For each, write a 2–3 sentence "why this fits you"
in {language}. Keep technical terms in English. Return strict JSON matching
the schema. Do NOT invent project IDs or titles.

USER:
Student profile: {intent_profile_json}
Candidates: [{id, title, abstract_snippet, stars, citations, has_code} × 20]
Return: { "ranked": [{id, rank, why_fit, est_weeks, difficulty_verdict} × 5] }
```

### 7.5 Blueprint expansion

Triggered on card click. Pydantic schema:

```python
class Blueprint(BaseModel):
    problem_statement: str
    why_it_matters: str
    in_scope: list[str]
    out_of_scope: list[str]
    suggested_architecture: str           # markdown, simple diagrams ok
    tech_stack: list[str]
    milestones_by_week: list[Milestone]
    datasets: list[DatasetRef]
    evaluation_metrics: list[str]
    risks_and_mitigations: list[RiskItem]
    how_to_stand_out: list[str]           # 3–5 differentiation ideas
    paper_refs: list[Ref]
    repo_refs: list[Ref]
```

Prompt stuffs: full paper abstract + first ~3000 chars of linked repo README + the student's IntentProfile. One call with `gpt-4o`, ~$0.02 per blueprint. Cached by `(candidate_id, language)` for 24 h.

### 7.6 Chat refinement

1. Send `(current IntentProfile, last 5 cards, student message)` to `gpt-4o-mini` with output schema `{updated_profile, refinement_notes}`.
2. Diff-apply the new profile.
3. Re-run retrieval → new cards.
4. Return `{cards, assistant_msg: refinement_notes in {language}}`.

Session cap: 15 refinements per session (hard rate limit). Profile version history kept in Postgres for an "undo last refinement" action.

### 7.7 Caching and rate limits

| Concern | Mechanism |
|---|---|
| Retrieval cache | Redis; key = `hash(filter + quantized_query_emb)`, TTL 10 min |
| Re-rank cache | Redis; key = `hash(top20_ids + intent_profile_version)`, TTL 1 h |
| Blueprint cache | Redis; key = `(candidate_id, language)`, TTL 24 h |
| Rate limit (anon) | IP sliding window: 20 recs/h, 5 blueprints/h, 15 refinements/session |

### 7.8 Resilience

- LLM call: 15 s timeout → 1 retry (2 s backoff) → fallback provider (Ollama) → deterministic top-5 + pre-written generic `why_fit`.
- Qdrant unreachable: fall back to Postgres full-text `tsvector` search — degraded, not dead.
- Redis unreachable: skip cache, keep serving (latency penalty only).
- Azure 429: circuit breaker trips after 3 failures in 60 s, skips Azure for 60 s.
- Ingestion worker failure: per-source isolation; dead-letter table re-runs next night.
- Empty retrieval: HTTP 200 + explicit `no_matches` code + broadening suggestion — no fabricated cards.

### 7.9 Prompt injection and security

- `interests_text` and chat messages sanitized (strip `"ignore previous…"`, cap 500 chars).
- System prompt wraps user content in `<untrusted_input>…</untrusted_input>` markers.
- Anonymous session = signed HTTP-only cookie (UUID).
- CORS locked to frontend origin.
- Pydantic-parse-don't-validate at API boundary, Zod at frontend boundary.
- No user-supplied URLs fetched server-side (SSRF guard).

### 7.10 Session and auth (v1)

- Anonymous cookie session only — no passwords, no OAuth.
- Optional email magic-link save ships in v1.5, not day-one.
- Email column encrypted at rest (pgcrypto) when it arrives.

## 8. UI / UX

### 8.1 Aesthetic direction — "Manuscript meets Production"

Fusion of Arabic scholarly manuscripts + editorial typography + terminal minimalism. Warm ink on cream (light) / warm ink on near-black (dark). Sharp gold single accent. Explicit rejection of generic SaaS look and ChatGPT-clone chat UI.

### 8.2 Typography

| Role | Font |
|---|---|
| Display (EN) | Fraunces (opsz axis; weights 200 / 800) |
| Body (EN) | Satoshi |
| Display (AR) | Lemonada (weights 300 / 700) |
| Body (AR) | IBM Plex Arabic |
| Mono | JetBrains Mono |

Size jumps 3×, headline 64–96 px, label 14 px, body 18 px. Arabic line-height 1.9 vs Latin 1.55.

### 8.3 Color tokens (semantic, not color names)

```css
/* light */
--bg-canvas:     #f6efe1;  /* aged paper */
--bg-surface:    #fbf6ea;
--bg-elevated:   #ffffff;
--text-primary:  #1a1612;  /* warm ink */
--text-muted:    #6a5f52;
--border-subtle: #e6dcc6;
--accent:        #c48a1e;  /* manuscript gold */
--accent-strong: #8a5c10;
--signal-code:   #2f6b4f;
--signal-paper:  #8b2e2e;
--signal-warn:   #b84a1a;

/* dark: same semantic keys */
--bg-canvas:     #14110c;
--bg-surface:    #1f1a12;
--bg-elevated:   #26201a;
--text-primary:  #f0e6d0;
--text-muted:    #a89c82;
--border-subtle: #3a3224;
--accent:        #e0a840;
```

Background atmosphere: SVG noise grain at 3% opacity + corner radial gradient. Never flat.

### 8.4 Screens

1. **Landing** (`/[locale]`) — asymmetric editorial hero, one sentence of value, single CTA, language + theme toggles top-right, settings sheet trigger (gear icon), diagonal gold rule as anchor.
2. **Onboarding form** (`/[locale]/onboard`) — 5 question-cards, spring transitions, progress-dot indicator, estimated 40 s.
3. **Recommendation board** (`/[locale]/board/{sid}`) — **hero screen**. Asymmetric masonry grid of idea cards; sticky-bottom refine bar; explicitly NOT a chat transcript UI.
4. **Blueprint view** (`/[locale]/blueprint/{id}`) — full-page takeover, TOC sidebar, milestone timeline, paper/repo badges, Copy-as-markdown / Download-as-md / Print.
5. **Saved** (`/[locale]/saved`) — grid + compare-up-to-3 side-by-side column.
6. **Settings sheet** (shadcn Sheet component, slide-in from right/left depending on direction) — theme (light/dark/system), language (ar/en), Arabic-Indic numerals toggle, tashkeel toggle, "clear my session". Accessible from every screen via gear icon in the top bar.

### 8.5 Lean card anatomy

```
┌────────────────────────────────────┐
│ [nlp] [rag] [arabic]  · ★ 3.2k     │
│                                     │
│ Title in Fraunces/Lemonada, 28px,   │
│ max 3 lines                         │
│                                     │
│ Why it fits you — 3 lines in        │
│ Satoshi / Plex Arabic               │
│                                     │
│ ───────────────────────             │  hairline gold divider
│ [✔ has code] [⊘ 12 weeks]           │
│ [△ intermediate]                    │
│                                     │
│ [ expand blueprint → ]   [ ♡ save ] │
└────────────────────────────────────┘
```

### 8.6 Motion

- Board load: 80 ms stagger, spring easing.
- Refinement: old cards fade + displace, new cards slide up 60 ms stagger.
- Blueprint: spring-scale 0.96→1.0 + fade (not plain fade).
- `prefers-reduced-motion`: all scale/slide replaced by fade.

### 8.7 Accessibility

- Semantic HTML, keyboard flow (Enter/Space on card = expand, Esc closes blueprint).
- `lang` per element for mixed content; `<bdi>` for embedded opposite-direction tokens.
- Focus ring: 2 px gold, 2 px offset, visible in both themes.
- All text passes WCAG AA; headlines AAA.
- No color-only signaling (icon + color for every status).

### 8.8 RTL specifics (`/ar/*`)

- `dir="rtl"` on `<html>` when locale is `ar`.
- CSS logical properties everywhere (`margin-inline-start`, not `margin-left`).
- Directional icons auto-flip; logos never flip.
- Arabic-Indic numerals off by default, togglable; tashkeel off by default, togglable.

### 8.9 Responsive breakpoints

320 / 480 / 768 / 1024 / 1440 px — mobile-first. Board re-flows to single column below 768; blueprint TOC collapses to top-sheet below 1024.

## 9. Testing strategy

| Layer | Tool | Scope | Target |
|---|---|---|---|
| Python unit | pytest (`asyncio_mode=auto`) | Parsers, intent builder, prompt assembler, dedup, scorer, anti-hallucination validator | 80% lines in `core/`, 70% overall |
| Python integration | pytest + testcontainers (Qdrant + Postgres) | Full retrieval pipeline, migrations, cache, rate limit | Pre-merge gate |
| LLM boundary | Mocked clients with VCR replay cassettes in unit + integration; real Azure only in nightly eval | Deterministic, no CI spend | — |
| Frontend unit | Vitest + React Testing Library | Components, hooks, i18n utilities, form validation | 70% on `components/` |
| E2E | Playwright | Golden paths in both locales (landing → form → board → blueprint → save) | Two critical flows per locale, PR-gated |
| LLM eval harness | pytest-based, scheduled nightly | 50 curated `(IntentProfile, acceptable_candidates)` pairs | Alert if recall@5 drops ≥ 10% WoW |

TDD applied to: scorer, intent builder, prompt assembler, dedup, anti-hallucination validator.

## 10. Deployment

### 10.1 Topology — v1

Single VPS (Hetzner CX22-class: 2 vCPU / 4 GB / 40 GB NVMe / ~€4.51/mo).

```
┌────────────────────── VPS ──────────────────────┐
│  Caddy (auto-TLS, reverse proxy)                 │
│    ├── /          → Next.js SSR container        │
│    └── /api/*     → FastAPI container            │
│                                                   │
│  Internal docker network:                         │
│    fastapi ──► postgres ──► qdrant ──► redis      │
│    celery-worker + celery-beat                    │
│                                                   │
│  Volumes: postgres-data/, qdrant-storage/,        │
│           redis-data/                             │
└───────────────────────────────────────────────────┘
```

Rationale for VPS over multi-cloud: flat cost, no cold starts, self-hosted Qdrant is free, demo-friendly (`docker compose up`), and every container lifts-and-shifts to managed services later without code changes.

### 10.2 CI/CD (GitHub Actions)

```
.github/workflows/
├── ci.yml       # PR: lint, typecheck, unit + integration tests, Playwright smoke
├── deploy.yml   # main: build + push images to GHCR, SSH deploy, migrate
├── ingest.yml   # nightly: trigger ingestion workers
└── eval.yml     # nightly: LLM eval harness with drift alert
```

Deploy step: `ssh user@vps "cd /opt/grad && git pull && docker compose pull && docker compose up -d && docker compose exec api alembic upgrade head"`. Sub-60 s zero-downtime via Caddy warm handoff.

### 10.3 Environments

- `local` — SQLite + Qdrant container + Ollama optional, no Azure spend unless `.env.local` has a key.
- `staging` — same compose on a cheaper VPS or ephemeral GHA service containers, real Azure with a lower-rate-limit deployment.
- `production` — the VPS above.

### 10.4 Security posture

| Concern | Mitigation |
|---|---|
| Secrets | `.env` in dev, Docker secrets in prod; rotation doc in README |
| TLS | Caddy auto-TLS |
| CORS | Locked to frontend origin |
| Input validation | Pydantic at API boundary, Zod at form boundary |
| Prompt injection | Pattern strip + length cap + `<untrusted_input>` wrapping in system prompt |
| Rate limits | Redis sliding window: 20 rec/h, 5 blueprint/h, 15 refine/session |
| PII | None in v1; email (v1.5) encrypted at rest |
| Dependencies | `pip-audit` + `npm audit` in CI; Dependabot on main |
| SSRF | Allow-list hostnames for arxiv/HF/GitHub; no user-supplied URLs |

### 10.5 Observability

- Loguru structured JSON logs → Docker `json-file` log driver (10 MB × 3 rotation).
- Prometheus `/metrics`: `rec_latency_ms`, `rerank_cache_hit_rate`, `empty_result_rate`, `azure_tokens_daily`, `ingestion_last_success_ts` per source.
- UptimeRobot free tier pinging `/healthz` every 5 min.
- Every log tagged with `session_id`, `stage`, `candidate_id` for full request traceability.

### 10.6 Cost estimate (steady state, 200 DAU)

| Item | Monthly |
|---|---|
| VPS (Hetzner CX22) | ~€4.51 |
| Domain | ~$1 |
| Azure `gpt-4o-mini` re-ranking | ~$14 |
| Azure `gpt-4o` blueprint expansion (cached) | ~$60 |
| Azure ingestion enrichment | ~$15 |
| Backups / snapshots | ~€1 |
| **Total** | **~$95–100/mo** |

Aggressive caching trims this ~40%. At 20 DAU (first month), all-in ~$10–15/mo.

## 11. Repository layout

```
graduation_project/
├── README.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── Caddyfile
├── .env.example
├── .github/workflows/{ci,deploy,ingest,eval}.yml
├── docs/superpowers/specs/2026-04-17-graduation-project-advisor-design.md
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic/{env.py,versions/}
│   ├── api/
│   │   ├── main.py
│   │   ├── deps.py
│   │   ├── middleware.py
│   │   ├── routes/{sessions,recommendations,refine,feedback,saved,health}.py
│   │   └── schemas/{intent,recommendation,blueprint}.py
│   ├── core/
│   │   ├── db/{engine,models,queries}.py
│   │   ├── embeddings/{encoder,qdrant_client}.py
│   │   ├── llm/{base,azure,ollama,gateway}.py
│   │   ├── llm/prompts/{rerank,blueprint,refine,enrich}.py
│   │   ├── recommendation/{intent_builder,filter,retrieve,score,rerank,validate,expand}.py
│   │   ├── cache.py, ratelimit.py, security.py, logging.py, settings.py
│   ├── ingestion/
│   │   ├── celery_app.py
│   │   ├── pipelines/{arxiv,hf_papers,pwc,github,enrich}.py
│   │   ├── normalize.py, dedup.py, outbox.py
│   ├── evals/{dataset.yml,harness.py,report.py}
│   └── tests/{unit,integration,fixtures}/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── biome.json
    ├── messages/{ar,en}.json
    ├── app/
    │   ├── [locale]/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   ├── onboard/page.tsx
    │   │   ├── board/[sid]/page.tsx
    │   │   ├── blueprint/[id]/page.tsx
    │   │   └── saved/page.tsx
    │   ├── api/                  # thin proxy handlers
    │   └── globals.css
    ├── components/
    │   ├── primitives/           # re-themed shadcn
    │   ├── idea-card.tsx
    │   ├── blueprint-timeline.tsx
    │   ├── blueprint-toc.tsx
    │   ├── domain-chips.tsx
    │   ├── paper-badge.tsx, repo-badge.tsx
    │   ├── refine-bar.tsx
    │   ├── language-toggle.tsx, theme-toggle.tsx
    │   ├── form-wizard.tsx
    │   └── atmospheric-bg.tsx
    ├── lib/
    │   ├── api-client.ts
    │   ├── stores/
    │   ├── hooks/
    │   ├── i18n.ts, format.ts
    ├── e2e/*.spec.ts
    └── public/{fonts/,og-image.png}
```

## 12. Build order (phases, dependency-ordered)

### Phase 0 — Foundations
- Repo scaffold, `docker-compose.yml` booting Postgres + Qdrant + Redis + FastAPI skeleton + Next.js skeleton + Celery.
- `.env.example`, `settings.py`, `logging.py`, `/healthz`.
- First empty Alembic migration, CI workflow stub.
- **Exit:** `docker compose up` boots everything; `curl /healthz` 200; Next lands at `/en` with a placeholder.

### Phase 1 — Ingestion backbone
- `ProjectCandidate` model + migration with indexes.
- Qdrant collection bootstrap.
- arXiv pipeline (OAI-PMH, 48 h delta, upsert) → first 1000 records.
- HF Papers pipeline.
- Embedding encoder singleton + Qdrant upsert.
- Normalization + dedup + unit tests.
- **Exit:** 1000+ candidates queryable via `qdrant_client.query_points()`.

### Phase 2 — Linking, enrichment, full corpus
- Papers-With-Code pipeline (link by arxiv_id).
- GitHub search pipeline (topics, stars ≥ 200, pushed filter).
- GitHub trending scrape (optional).
- LLM enrichment job (`gpt-4o-mini` batch for domains, difficulty, readme_summary).
- Quality gate + `quality_score` computation.
- Celery beat schedule + outbox pattern.
- **Exit:** ~10,000 enriched, linked, embedded candidates; nightly run idempotent.

### Phase 3 — Recommendation API (no UI yet)
- `IntentProfile` + intent-builder.
- Filter builder → Qdrant.
- Deterministic pre-score.
- LLM re-rank (`gpt-4o-mini`, structured JSON) + anti-hallucination validator.
- `POST /recommendations` + cache + rate limit.
- `POST /recommendations/{id}/expand` (`gpt-4o`).
- Session endpoints + cookie signing.
- **Exit:** `curl` with a JSON IntentProfile returns 5 grounded cards in <3 s; expansion returns full blueprint JSON.

### Phase 4 — Chat refinement, feedback, saved
- `POST /sessions/{sid}/refine` with profile diff.
- Profile version history + undo endpoint.
- Thumbs up/down feedback endpoint.
- Saved cards endpoints.
- **Exit:** end-to-end refinement flow via `curl`; feedback persists.

### Phase 5 — Frontend foundation
- Next.js App Router with `[locale]` segment, next-intl wired.
- Tailwind v4 + RTL plugin + manuscript tokens in `globals.css`.
- Self-hosted fonts (Fraunces, Satoshi, Lemonada, IBM Plex Arabic, JetBrains Mono).
- shadcn primitives installed and re-themed.
- Zustand + TanStack Query + typed API client (Zod).
- Language toggle + theme toggle + atmospheric background.
- **Exit:** `/en` and `/ar` render with correct direction, fonts, colors.

### Phase 6 — Landing + onboarding form
- Landing editorial hero.
- Form wizard (5 question-cards) with spring transitions.
- IntentProfile submit → redirect to `/board/[sid]`.
- **Exit:** landing → onboard → board ≤ 40 s.

### Phase 7 — Recommendation board (hero)
- `IdeaCard` with full anatomy.
- Masonry grid with staggered load.
- `RefineBar` sticky-bottom + minimal transcript panel.
- Integration with `/recommendations` + loading skeletons + empty/error states.
- **Exit:** finish form → see 5 real cards → can refine.

### Phase 8 — Blueprint view
- Blueprint route with TOC sidebar.
- Milestone timeline, paper/repo badges, Copy-as-markdown, Download-as-md, Print stylesheet.
- **Exit:** click expand → full blueprint loads in both locales.

### Phase 9 — Save / compare / polish
- Saved page with compare-3-side-by-side.
- Feedback wiring.
- A11y sweep (keyboard, focus, ARIA, contrast).
- Mobile refinement (<768 px).
- `prefers-reduced-motion` pass.
- **Exit:** Playwright passes both locales; axe-core audits clean.

### Phase 10 — Eval + deploy
- Curate 50-pair eval dataset.
- Eval harness + GHA workflow, baseline recorded.
- Caddy + production compose.
- VPS provisioned, SSH deploy workflow, migrations on deploy.
- UptimeRobot, structured logs verified in prod.
- **Exit:** live domain over HTTPS, bilingual, cost within budget, first 10 beta students onboarded.

## 13. Open questions (tracked, not blocking v1)

- Arabic-source paper support: intentionally deferred. Most CS research is English; adding Arabic sources would require new ingestion targets (e.g., Arabic conference proceedings) and is unlikely to meaningfully help recommendations in v1.
- Auto-generated starter-kit zip (v2 option from brainstorming Q5): deferred to v2 pending user-facing signal that blueprints alone aren't enough.
- Telegram adapter: v2 candidate; backend API is already designed channel-agnostic.
- Fine-tuned local model: only if Azure costs blow past budget at scale.
- University / supervisor integration: out of scope; consider v3 if schools adopt.

## 14. Non-goals

- Not a general-purpose chatbot.
- Not a literature review tool.
- Not a GitHub trending explorer.
- Not a thesis writing assistant.
- Not multi-tenant / institutional.

## 15. Glossary

- **ProjectCandidate** — unified record for a paper, repo, or paper+repo pair.
- **IntentProfile** — structured representation of a student's filters + interests.
- **LeanCard** — short recommendation surface shown on the board.
- **Blueprint** — full production-grade project description on expand.
- **PWC** — Papers-With-Code.
- **OAI-PMH** — arXiv's metadata harvest protocol.
