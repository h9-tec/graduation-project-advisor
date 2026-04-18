# Phase 1 Ingestion — PWC Sunset Addendum

- **Status:** Active (amends the 2026-04-17 design spec, §6)
- **Date:** 2026-04-18
- **Trigger:** Papers-With-Code was sunset by Meta on 2025-07-24 without notice. `paperswithcode.com` now 302-redirects to `huggingface.co/papers`. Every PWC-dependent decision in §6 of the original spec needs a new plan.

## 1. What changed

- **Source removed:** `paperswithcode.com/api/v1/papers/{arxiv_id}/repositories/` — permanently gone.
- **Consequence:** the original paper↔code linking strategy loses its primary channel. Secondary (regex-scan abstracts for `github.com` URLs) and tertiary (README scans) are now primary.

## 2. Replacements

### 2.1 Primary: HuggingFace Daily Papers API

`GET https://huggingface.co/api/daily_papers` returns a JSON array. Each record already contains the fields PWC used to give us:

| Field | Purpose |
|---|---|
| `id` | arXiv ID (dedup key) |
| `title`, `summary` | paper metadata |
| `githubRepo` | **direct paper → code link** (replaces PWC's primary value) |
| `githubStars` | quality signal |
| `projectPage` | bonus project URL |
| `ai_summary` | pre-generated LLM summary (skips our ingestion-time enrichment call) |
| `ai_keywords` | pre-generated tag list (skips our domain classifier call) |
| `upvotes`, `numComments` | social quality signal |
| `publishedAt`, `submittedOnDailyAt` | recency |
| `organization` | affiliation |

This is **strictly better than PWC was** — PWC never had AI-generated summaries or community upvotes.

### 2.2 Broader base: arXiv OAI-PMH (unchanged)

Still the right source for papers that didn't make HF Daily but are still cs-category relevant. Feed delta-pulled nightly, cs.CL / cs.CV / cs.LG / cs.AI / cs.IR / cs.RO / cs.NE / cs.HC, last 24 months.

### 2.3 Paper↔code link when HF Daily doesn't have it

Five-stage fallback, in order:

1. **HF Daily Papers**: `record.githubRepo` (authoritative when present).
2. **HF paper-page scrape**: `https://huggingface.co/papers/{arxiv_id}` — even for papers not in the Daily list, this page often lists linked GitHub repos from models/datasets that reference the paper.
3. **arXiv abstract regex scan**: `github\.com/[\w.-]+/[\w.-]+` — catches ~10–15% more.
4. **GitHub search by title**: `q={title}+in:readme+is:public&sort=stars` — catches implementations that don't mention the paper explicitly.
5. **Agent-driven fallback (Phase 2)**: Crawl4AI + Ollama on first three Google-Scholar-style results. Only invoked for high-signal papers (upvotes > 10) with no code found via 1–4.

### 2.4 Code-first sources (papers-less "stunning projects")

For the "stunning projects on GitHub" arm of the requirements, we're no longer piggybacking on PWC's leaderboard coverage. New strategy:

| Source | How | Rationale |
|---|---|---|
| GitHub Search API | `stars:>200` + topic filters + `pushed:>2024-01-01` | Popular-and-maintained |
| `github.com/trending` | Scraped via Crawl4AI, weekly Python filter | Surfaces net-new repos |
| Curated awesome-lists | Scraped via Crawl4AI as plain markdown, regex-parse repo links | Community-vetted quality |
| HuggingFace Spaces | `huggingface.co/api/spaces?sort=likes` | Deployed demos with source code |

## 3. Open-source scraping agent choice

**Crawl4AI** (Apache 2.0, 58k+ stars) is the chosen open-source scraping agent. Selection criteria:

| Criterion | Crawl4AI | Trafilatura | Firecrawl OSS | Browser-use |
|---|---|---|---|---|
| License | Apache 2.0 ✓ | Apache 2.0 ✓ | AGPL-3.0 ✗ | MIT ✓ |
| Self-hostable | Yes ✓ | Yes ✓ | Rough self-host story | Yes ✓ |
| LLM-ready markdown | Built-in | Built-in | Built-in | Via LLM loop |
| JS rendering | Playwright inside | No | Playwright | Playwright + vision |
| Ollama integration | First-class | N/A | Cloud-only | First-class |
| Ingestion surface fit | Perfect for our static pages | Perfect for volume | — | Overkill, no auth flows |

**Usage pattern:**

```python
from crawl4ai import AsyncWebCrawler
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://github.com/foo/bar")
    markdown = result.markdown  # clean, LLM-ready
```

For simple HTML pages where JS isn't required, we fall through to **direct httpx + Crawl4AI's own extraction** to keep the image slim. Playwright browsers are downloaded lazily the first time Crawl4AI is used.

**What we're not using (and why):**

- **Firecrawl OSS** — AGPL-3.0 is a portfolio-repo hazard. Great product, wrong license for this project.
- **Browser-use** — 78k stars, excellent for interactive multi-step workflows (logins, forms). Overkill here; our ingestion surface is static.
- **ScrapeGraphAI** — premium feature is LLM-powered semantic extraction without selectors. Our sources are structured enough that we don't need it. Keep as Phase 2 option for truly unstructured sources.
- **Jina Reader** — not self-hostable (keyless is rate-limited; we want deterministic offline-capable pipelines).

## 4. Data model change

Add these fields to `ProjectCandidate` (spec §6.2):

```python
upvotes_daily: int = 0         # HF Daily Papers social signal
submitted_on_daily_at: datetime | None
ai_keywords: list[str]         # directly from HF Daily (skips our enrichment)
project_page_url: str | None
organization: str | None
```

`ai_keywords` replaces our LLM-generated `domains` for HF-sourced records (the classification is already done, consistently, and free). For arXiv-only records we still run the enrichment LLM call.

## 5. Embedding strategy (unchanged)

- Multilingual MiniLM-L12-v2, 384 dim, local CPU (~2 ms/record).
- Embed `f"{title}\n\n{abstract or ai_summary}"`, 512-token truncation.

## 6. Recommender consequences (§7)

The retrieval pipeline stays identical — filter + ANN + deterministic pre-score + LLM re-rank + anti-hallucination. Two changes:

- **Pre-score weights adjusted**: `has_code` bonus stays; add a small `upvotes_daily` bonus for HF-curated papers (bounded so it doesn't dominate). Tunable later via eval-set.
- **Empty-retrieval fallback**: When the filter + ANN returns <10 candidates, fall back to pure-LLM recommendation (current Phase-0 behavior) so the UX never breaks during the cold-start ingestion window.

## 7. Schedule (Celery beat)

| Job | Schedule | Source | Target volume |
|---|---|---|---|
| `pull_hf_daily_papers` | Every 6 hours | HF Daily Papers API | ~10–50 new/day |
| `pull_arxiv_delta` | Nightly 03:00 UTC | arXiv OAI-PMH 48h window | ~200–500 new/day |
| `refresh_github_metadata` | Nightly 03:30 UTC | GitHub API for tracked repos | — |
| `scrape_github_trending` | Weekly Sunday 04:00 UTC | Crawl4AI on github.com/trending | ~25/week |
| `scrape_awesome_lists` | Weekly Sunday 04:30 UTC | Crawl4AI on configured awesome-list URLs | ~few hundred/week |
| `enrich_unclassified` | Continuous worker | LLM domain/difficulty tagging for arXiv records that lack ai_keywords | — |

## 8. Non-goals for this phase

- Active crawling of paywalled or login-gated sources.
- OCR of paper PDFs (HF Daily's `summary` + `ai_summary` is enough).
- Semantic Scholar ingestion (200M+ records too noisy; use only as an on-demand reference lookup in the blueprint view).
- Translation of Arabic papers (still English-only sources; Arabic UX continues via multilingual embeddings at query time).

## 9. Open questions

- **arXiv full-text vs abstract**: start with abstract only; revisit if retrieval recall is poor on specific domains.
- **Crawl4AI Playwright image size**: if the backend image bloats past 1.5 GB, split scraping into its own `ingestion-worker` service with its own (heavier) image.
- **Rate-limiting on HF API**: unspecified publicly. Start conservative (1 req/sec) and raise if no 429s after a week of running.
