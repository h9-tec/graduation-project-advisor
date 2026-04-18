"""GitHub Trending via Crawl4AI.

GitHub doesn't publish a trending API. We scrape github.com/trending with
Crawl4AI (Apache 2.0, Playwright under the hood, LLM-ready markdown output)
and parse repo slugs from the markdown, then fetch each repo's metadata via
the GitHub REST API.
"""
from __future__ import annotations

import asyncio
import re
from datetime import date, datetime, timezone
from typing import Any

import httpx
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from loguru import logger

from ingestion.normalize import NormalizedCandidate, compute_quality_score

TRENDING_URL = "https://github.com/trending/python?since=weekly"
GITHUB_API = "https://api.github.com"

# Top-level paths on github.com that are NOT user/repo slugs
_NON_REPO_OWNERS = {
    "login", "signup", "trending", "topics", "collections", "marketplace",
    "features", "sponsors", "search", "codespaces", "about", "pricing",
    "settings", "notifications", "pulls", "issues", "explore", "enterprise",
    "team", "mobile", "premium-support", "site-policy", "security",
    "customer-stories", "readme", "nonprofit", "contact", "contact-sales",
    "accessibility", "apps", "resources", "solutions", "mcp", "new",
    "organizations",
}

_SLUG_RE = re.compile(
    r"^(?:https?://github\.com)?/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+)/?$"
)


async def _fetch_trending_slugs(count: int) -> list[tuple[str, str]]:
    """Run Crawl4AI against github.com/trending, extract real owner/repo slugs.

    Uses Crawl4AI's structured `result.links.internal` (much cleaner than
    regex-scraping the rendered markdown).
    """
    browser = BrowserConfig(headless=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        word_count_threshold=5,
        cache_mode="BYPASS",
        wait_until="networkidle",
        page_timeout=30000,
    )

    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=TRENDING_URL, config=run_cfg)
        if not result.success:
            logger.warning(f"crawl4ai trending fetch failed: {result.error_message}")
            return []
        internal_links = (result.links or {}).get("internal") or []

    seen: set[tuple[str, str]] = set()
    slugs: list[tuple[str, str]] = []
    for link in internal_links:
        href = (link.get("href") or "").split("?")[0].split("#")[0]
        m = _SLUG_RE.match(href)
        if not m:
            continue
        owner, repo = m.group(1), m.group(2)
        if owner.lower() in _NON_REPO_OWNERS:
            continue
        if (owner, repo) in seen:
            continue
        seen.add((owner, repo))
        slugs.append((owner, repo))
        if len(slugs) >= count:
            break

    logger.info(f"crawl4ai trending: {len(slugs)} unique repo slugs parsed")
    return slugs


async def _fetch_repo_meta(
    client: httpx.AsyncClient, owner: str, repo: str
) -> dict[str, Any] | None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 403:
            logger.warning("GitHub API rate-limited — returning what we have")
            return None
        if resp.status_code != 200:
            return None
        return resp.json()
    except httpx.HTTPError as exc:
        logger.warning(f"repo meta fetch failed for {owner}/{repo}: {exc}")
        return None


def _normalize_repo(meta: dict[str, Any]) -> NormalizedCandidate | None:
    name = meta.get("full_name") or ""
    if not name or "/" not in name:
        return None
    description = (meta.get("description") or "").strip() or None

    title = f"{name}"
    if description:
        title = f"{name} — {description}"
    # Cap title length
    title = title[:480]

    # Parse pushed_at
    last_push = None
    pushed = meta.get("pushed_at")
    if pushed:
        try:
            last_push = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
        except ValueError:
            pass

    topics = meta.get("topics") or []
    keywords = [t.lower() for t in topics if isinstance(t, str)][:8]

    # Map GitHub topics to our domain buckets
    dom_map = {
        "machine-learning": "mlops",
        "deep-learning": "mlops",
        "nlp": "nlp",
        "natural-language-processing": "nlp",
        "computer-vision": "cv",
        "llm": "nlp",
        "rag": "rag",
        "agents": "agents",
        "agent": "agents",
        "reinforcement-learning": "rl",
        "robotics": "robotics",
        "speech": "audio",
        "audio": "audio",
    }
    domains = sorted({dom_map[t] for t in keywords if t in dom_map})

    cand = NormalizedCandidate(
        source="github_trending",
        source_type="repo_only",
        title=title,
        github_url=meta.get("html_url") or f"https://github.com/{name}",
        readme_summary=description,
        domains=domains,
        ai_keywords=keywords,
        has_code=True,
        stars=int(meta.get("stargazers_count") or 0),
        upvotes_daily=0,
        code_language=meta.get("language"),
        published_at=(
            date.fromisoformat(meta["created_at"][:10]) if meta.get("created_at") else None
        ),
        raw_metadata={
            "default_branch": meta.get("default_branch"),
            "forks": meta.get("forks_count"),
            "open_issues": meta.get("open_issues_count"),
            "license": (meta.get("license") or {}).get("spdx_id"),
            "source": "github_trending_weekly_python",
        },
    )
    # override last_github_push via dataclass post-init-style
    cand.raw_metadata["last_pushed_at"] = pushed
    cand.quality_score = compute_quality_score(cand)
    return cand


async def fetch_trending(count: int = 25) -> list[NormalizedCandidate]:
    """End-to-end: scrape trending → resolve each repo's metadata → normalize."""
    slugs = await _fetch_trending_slugs(count * 2)  # over-fetch to survive drops
    if not slugs:
        return []

    candidates: list[NormalizedCandidate] = []
    async with httpx.AsyncClient() as client:
        for owner, repo in slugs:
            meta = await _fetch_repo_meta(client, owner, repo)
            if meta is None:
                continue
            cand = _normalize_repo(meta)
            if cand is None:
                continue
            candidates.append(cand)
            if len(candidates) >= count:
                break
            await asyncio.sleep(0.2)  # polite to GitHub

    logger.info(f"github_trending total: {len(candidates)} candidates")
    return candidates
