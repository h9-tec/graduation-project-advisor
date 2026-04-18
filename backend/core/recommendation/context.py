"""Build a richly-grounded context for blueprint expansion.

The /expand endpoint used to feed the LLM only the card's 200-char snippet,
so every blueprint was mostly LLM-invented. We now:

  1. Look up the underlying ProjectCandidate in Postgres by its UUID (the
     card id is the Qdrant point id which equals the candidate row id in
     RAG-path; for pure-LLM fallback cards we skip this step).
  2. Try to fetch the README from the candidate's github_url — raw.github
     first (fast, public), Crawl4AI as the fallback for repos whose main
     branch markdown isn't at a predictable path.
  3. Collapse everything into a single dict the prompt can stuff into
     ~3 KB.

Nothing here is mocked. The LLM sees the actual abstract + actual README.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.db.models import ProjectCandidate
from core.settings import get_settings

_README_MAX_CHARS = 4000
_HTTP_TIMEOUT = httpx.Timeout(12.0, connect=5.0)

_README_CANDIDATES = (
    "README.md",
    "readme.md",
    "Readme.md",
    "README.rst",
    "README.txt",
    "README",
)


def _engine() -> Any:
    return create_async_engine(get_settings().database_url, future=True)


async def _load_candidate(
    card_id: str, arxiv_url: str | None, github_url: str | None
) -> ProjectCandidate | None:
    """Find the underlying Postgres row behind a card.

    Priority:
      1. card_id parsed as UUID → ProjectCandidate.id (RAG-path cards)
      2. github_url match
      3. arxiv_id parsed out of arxiv_url
    """
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as session:
            row: ProjectCandidate | None = None

            try:
                cid = uuid.UUID(card_id)
                row = await session.get(ProjectCandidate, cid)
            except ValueError:
                row = None

            if row is None and github_url:
                row = (
                    await session.execute(
                        select(ProjectCandidate).where(
                            ProjectCandidate.github_url == github_url
                        )
                    )
                ).scalar_one_or_none()

            if row is None and arxiv_url:
                aid = arxiv_url.rsplit("/", 1)[-1].split("v")[0]
                row = (
                    await session.execute(
                        select(ProjectCandidate).where(
                            or_(
                                ProjectCandidate.arxiv_id == aid,
                                ProjectCandidate.arxiv_id == aid.strip(),
                            )
                        )
                    )
                ).scalar_one_or_none()

            if row is not None:
                # detach so we can safely read attributes after the session closes
                session.expunge(row)
            return row
    finally:
        await engine.dispose()


def _parse_owner_repo(github_url: str) -> tuple[str, str] | None:
    m = re.match(
        r"https?://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+)(?:/|$)",
        github_url,
    )
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    # Drop trailing .git if present
    repo = repo.removesuffix(".git")
    return owner, repo


async def _fetch_default_branch(
    client: httpx.AsyncClient, owner: str, repo: str
) -> str | None:
    """GitHub REST → default branch. No auth needed for public repos."""
    try:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}", timeout=_HTTP_TIMEOUT
        )
        if resp.status_code != 200:
            return None
        return resp.json().get("default_branch") or "main"
    except httpx.HTTPError:
        return None


async def _fetch_readme_raw(github_url: str) -> str | None:
    """Try raw.githubusercontent for each candidate README filename + branch.

    Returns the first hit's text truncated to _README_MAX_CHARS.
    """
    parsed = _parse_owner_repo(github_url)
    if parsed is None:
        return None
    owner, repo = parsed

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        branch = await _fetch_default_branch(client, owner, repo) or "main"
        for name in _README_CANDIDATES:
            for br in (branch, "master", "main"):
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/{name}"
                try:
                    r = await client.get(url)
                except httpx.HTTPError:
                    continue
                if r.status_code == 200 and r.text:
                    return r.text[:_README_MAX_CHARS]
    return None


async def _fetch_readme_crawl4ai(github_url: str) -> str | None:
    """Fallback: run Crawl4AI against the repo landing page and keep the
    markdown body. Slower (spins Chromium) but works for repos where the
    raw path guess fails."""
    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    except ImportError:
        return None

    cfg = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        word_count_threshold=30,
        cache_mode="BYPASS",
        wait_until="domcontentloaded",
        page_timeout=20000,
    )
    try:
        async with AsyncWebCrawler(config=cfg) as crawler:
            result = await crawler.arun(url=github_url, config=run_cfg)
            if not result.success:
                return None
            md = result.markdown or ""
            # Strip the GitHub chrome at the top; keep the README body
            marker = "\n## README\n"
            lowered = md.lower()
            idx = lowered.find("\n## readme\n")
            if idx >= 0:
                md = md[idx + len(marker) :]
            return md[:_README_MAX_CHARS] or None
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"crawl4ai readme fetch failed for {github_url}: {exc}")
        return None


async def fetch_readme(github_url: str | None) -> str | None:
    if not github_url:
        return None
    text = await _fetch_readme_raw(github_url)
    if text:
        return text
    return await _fetch_readme_crawl4ai(github_url)


def _truncate(s: str | None, n: int) -> str:
    if not s:
        return ""
    s = s.strip()
    if len(s) <= n:
        return s
    return s[: n - 3].rstrip() + "…"


async def build_blueprint_context(card: dict[str, Any]) -> dict[str, Any]:
    """Return the enriched card context passed to the blueprint LLM prompt."""
    arxiv_url = card.get("arxiv_url")
    github_url = card.get("github_url")

    cand = await _load_candidate(card.get("id", ""), arxiv_url, github_url)
    readme = await fetch_readme(github_url)

    ctx: dict[str, Any] = {
        "title": card.get("title"),
        "research_hook": card.get("research_hook"),
        "stack_hook": card.get("stack_hook"),
        "est_weeks": card.get("est_weeks"),
        "difficulty_verdict": card.get("difficulty_verdict"),
        "stars": card.get("stars_estimate"),
        "arxiv_url": arxiv_url,
        "github_url": github_url,
        "abstract": None,
        "ai_summary": None,
        "ai_keywords": [],
        "published_year": None,
        "organization": None,
        "code_language": None,
        "readme_excerpt": _truncate(readme, _README_MAX_CHARS),
    }

    if cand is not None:
        ctx["abstract"] = _truncate(cand.abstract, 3000)
        ctx["ai_summary"] = _truncate(cand.ai_summary, 2000)
        ctx["ai_keywords"] = list(cand.ai_keywords or [])
        ctx["published_year"] = (
            cand.published_at.year if cand.published_at else None
        )
        ctx["organization"] = cand.organization
        ctx["code_language"] = cand.code_language
        # if the readme regex fallback missed but we stored a summary at
        # ingestion time, use it
        if not ctx["readme_excerpt"] and cand.readme_summary:
            ctx["readme_excerpt"] = _truncate(cand.readme_summary, _README_MAX_CHARS)

    return ctx
