from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from loguru import logger

from ingestion.normalize import (
    NormalizedCandidate,
    compute_quality_score,
    find_github_in_text,
)

HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HTTP_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


async def fetch_day(d: date) -> list[dict[str, Any]]:
    """Fetch HF daily papers for one date. Returns a list (empty if none)."""
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(HF_DAILY_URL, params={"date": d.isoformat()})
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            logger.warning(f"HF daily_papers returned non-list for {d}: {type(data)}")
            return []
        return data


def _parse_dt(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    dt = _parse_dt(value)
    return dt.date() if dt else None


def normalize_hf_item(item: dict[str, Any]) -> NormalizedCandidate | None:
    """Flatten one HF Daily Papers row into a NormalizedCandidate.

    The API nests most paper fields under item["paper"]. Title and summary
    are duplicated at the outer level — we prefer the nested copy.
    """
    paper = item.get("paper") or {}
    if not isinstance(paper, dict):
        return None

    arxiv_id = str(paper.get("id") or "").strip() or None
    title = str(paper.get("title") or item.get("title") or "").strip()
    summary = str(paper.get("summary") or item.get("summary") or "").strip() or None
    ai_summary = str(paper.get("ai_summary") or "").strip() or None

    if not title:
        return None

    github_url = (
        str(paper.get("githubRepo") or "").strip() or None
    ) or find_github_in_text(summary or "")
    github_stars = int(paper.get("githubStars") or 0)
    upvotes = int(paper.get("upvotes") or 0)

    ai_keywords_raw = paper.get("ai_keywords") or []
    ai_keywords = [str(k).strip().lower() for k in ai_keywords_raw if str(k).strip()]

    project_page = str(paper.get("projectPage") or "").strip() or None

    # try to pull organization from first author's email/affiliation if present
    org = None
    authors = paper.get("authors") or []
    if authors and isinstance(authors, list) and isinstance(authors[0], dict):
        org = authors[0].get("affiliation") or None

    published_at = _parse_date(paper.get("publishedAt") or item.get("publishedAt"))
    submitted = _parse_dt(paper.get("submittedOnDailyAt"))

    source_type = (
        "paper_with_code" if github_url else "paper_only"
    )

    cand = NormalizedCandidate(
        source="hf_daily_papers",
        source_type=source_type,
        title=title,
        arxiv_id=arxiv_id,
        github_url=github_url,
        abstract=summary,
        ai_summary=ai_summary,
        ai_keywords=ai_keywords,
        has_code=bool(github_url),
        stars=github_stars,
        upvotes_daily=upvotes,
        project_page_url=project_page,
        organization=org,
        published_at=published_at,
        submitted_on_daily_at=submitted,
        raw_metadata={
            "hf_paper_url": f"https://huggingface.co/papers/{arxiv_id}" if arxiv_id else None,
            "numComments": item.get("numComments"),
            "submittedBy": (item.get("submittedBy") or {}).get("user"),
            "discussionId": paper.get("discussionId"),
        },
    )
    cand.quality_score = compute_quality_score(cand)
    return cand


async def fetch_recent(days: int) -> list[NormalizedCandidate]:
    """Pull the last `days` days of HF Daily Papers, normalize, dedup by arxiv_id."""
    today = datetime.now(tz=timezone.utc).date()
    out: list[NormalizedCandidate] = []
    seen_arxiv: set[str] = set()

    for offset in range(days):
        d = today - timedelta(days=offset)
        try:
            items = await fetch_day(d)
        except httpx.HTTPError as exc:
            logger.warning(f"HF daily_papers fetch failed for {d}: {exc}")
            continue

        kept = 0
        for item in items:
            cand = normalize_hf_item(item)
            if cand is None:
                continue
            key = cand.arxiv_id or cand.github_url or cand.title
            if key in seen_arxiv:
                continue
            seen_arxiv.add(key)
            out.append(cand)
            kept += 1
        logger.info(f"HF daily_papers {d.isoformat()}: fetched={len(items)} kept={kept}")

    logger.info(f"HF daily_papers total: {len(out)} candidates across {days} days")
    return out
