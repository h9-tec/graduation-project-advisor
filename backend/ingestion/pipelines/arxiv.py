"""arXiv pipeline using the REST API (Atom feed) via feedparser.

We intentionally use the public REST endpoint `export.arxiv.org/api/query`
instead of full OAI-PMH — it's simpler, respects arXiv's 3-second rate
limit by sleeping between page fetches, and covers the same fields we need.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import feedparser
import httpx
from loguru import logger

from ingestion.normalize import (
    NormalizedCandidate,
    compute_quality_score,
    find_github_in_text,
)

ARXIV_URL = "https://export.arxiv.org/api/query"
DEFAULT_CATS = ("cs.CL", "cs.CV", "cs.LG", "cs.AI", "cs.IR", "cs.RO", "cs.NE", "cs.HC")
MAX_PER_PAGE = 100
RATE_LIMIT_SECONDS = 3.0


def _build_query(categories: tuple[str, ...], since: date | None) -> str:
    cats = " OR ".join(f"cat:{c}" for c in categories)
    if since:
        # YYYYMMDDHHMM window
        start = since.strftime("%Y%m%d") + "0000"
        end = datetime.now(tz=timezone.utc).strftime("%Y%m%d") + "2359"
        return f"({cats}) AND submittedDate:[{start} TO {end}]"
    return f"({cats})"


async def _fetch_page(query: str, start: int) -> bytes:
    params = {
        "search_query": query,
        "start": str(start),
        "max_results": str(MAX_PER_PAGE),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(ARXIV_URL, params=params)
        resp.raise_for_status()
        return resp.content


def _parse_entry(entry: Any) -> NormalizedCandidate | None:
    # arXiv id lives in entry.id as http://arxiv.org/abs/XXXX.YYYYY[vN]
    raw_id = getattr(entry, "id", "") or ""
    if "/abs/" not in raw_id:
        return None
    arxiv_id = raw_id.split("/abs/")[-1].split("v")[0]

    title = " ".join((getattr(entry, "title", "") or "").split()).strip()
    summary = " ".join((getattr(entry, "summary", "") or "").split()).strip()
    if not title:
        return None

    # primary category → single-tag domain
    tags = [t.term for t in (getattr(entry, "tags", []) or []) if hasattr(t, "term")]
    # map cs.* categories to domain buckets
    domain_map = {
        "cs.CL": "nlp",
        "cs.CV": "cv",
        "cs.LG": "mlops",
        "cs.AI": "agents",
        "cs.IR": "rag",
        "cs.RO": "robotics",
        "cs.NE": "mlops",
        "cs.HC": "web",
    }
    domains = sorted({domain_map[t] for t in tags if t in domain_map})

    published = None
    if getattr(entry, "published_parsed", None):
        published = date(*entry.published_parsed[:3])

    github_url = find_github_in_text(summary)

    cand = NormalizedCandidate(
        source="arxiv",
        source_type="paper_with_code" if github_url else "paper_only",
        title=title,
        arxiv_id=arxiv_id,
        github_url=github_url,
        abstract=summary,
        domains=domains,
        has_code=bool(github_url),
        stars=0,
        upvotes_daily=0,
        published_at=published,
        raw_metadata={
            "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
            "categories": tags,
        },
    )
    cand.quality_score = compute_quality_score(cand)
    return cand


async def fetch_recent(
    days: int = 7,
    categories: tuple[str, ...] = DEFAULT_CATS,
    max_records: int = 500,
) -> list[NormalizedCandidate]:
    """Pull arXiv papers submitted in the last `days` days across categories.

    Respects arXiv's rate limit (3s between requests). Stops when a page
    returns fewer than MAX_PER_PAGE records, or when max_records is reached.
    """
    since = datetime.now(tz=timezone.utc).date() - timedelta(days=days)
    query = _build_query(categories, since)

    collected: list[NormalizedCandidate] = []
    seen_ids: set[str] = set()
    start = 0

    while len(collected) < max_records:
        try:
            raw = await _fetch_page(query, start)
        except httpx.HTTPError as exc:
            logger.warning(f"arxiv fetch failed at start={start}: {exc}")
            break

        parsed = feedparser.parse(raw)
        entries = parsed.entries or []
        if not entries:
            break

        kept = 0
        for e in entries:
            cand = _parse_entry(e)
            if cand is None or cand.arxiv_id in seen_ids:
                continue
            seen_ids.add(cand.arxiv_id)
            collected.append(cand)
            kept += 1
        logger.info(
            f"arxiv page start={start}: got {len(entries)}, kept {kept}, "
            f"total {len(collected)}"
        )

        if len(entries) < MAX_PER_PAGE:
            break
        start += MAX_PER_PAGE
        await asyncio.sleep(RATE_LIMIT_SECONDS)

    logger.info(f"arxiv total: {len(collected)} candidates (days={days})")
    return collected
