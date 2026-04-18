from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


GITHUB_URL_RE = re.compile(
    r"https?://github\.com/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+",
    re.IGNORECASE,
)


@dataclass
class NormalizedCandidate:
    """Shape shared across every ingestion source before it hits the DB."""

    source: str
    source_type: str
    title: str

    arxiv_id: str | None = None
    github_url: str | None = None
    abstract: str | None = None
    ai_summary: str | None = None
    readme_summary: str | None = None

    ai_keywords: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    difficulty_estimated: str | None = None
    difficulty_level: int | None = None

    has_code: bool = False
    stars: int = 0
    upvotes_daily: int = 0
    citations: int | None = None

    project_page_url: str | None = None
    organization: str | None = None
    code_language: str | None = None

    published_at: date | None = None
    submitted_on_daily_at: datetime | None = None

    raw_metadata: dict[str, Any] = field(default_factory=dict)


def content_hash(c: NormalizedCandidate) -> str:
    """Stable hash over the text that feeds embeddings, for change detection."""
    text = (c.title or "") + "\n" + (c.abstract or c.ai_summary or c.readme_summary or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_text(c: NormalizedCandidate) -> str:
    """Text we actually feed to the embedder."""
    body = c.abstract or c.ai_summary or c.readme_summary or ""
    if not c.title and not body:
        return ""
    return f"{c.title}\n\n{body}".strip()


def compute_quality_score(c: NormalizedCandidate) -> float:
    """0..1 heuristic score, weighted toward proven community signal.

    Tunable. Used as a deterministic pre-score bonus before LLM re-rank.
    """
    s = 0.0
    # star mass on a log curve: 0 stars = 0, 100 stars ≈ 0.2, 10k stars ≈ 0.4
    if c.stars > 0:
        import math

        s += min(0.4, math.log1p(c.stars) / 25)
    # upvotes from HF community (max ~100 typically), worth up to +0.3
    s += min(0.3, c.upvotes_daily / 100)
    # citations (from Semantic Scholar someday) — log curve, up to +0.2
    if c.citations:
        import math

        s += min(0.2, math.log1p(c.citations) / 30)
    # has_code pays a flat bonus (crucial for actionable projects)
    if c.has_code:
        s += 0.1
    return round(min(1.0, s), 4)


def find_github_in_text(text: str) -> str | None:
    """Regex-scan text for the first github.com/<owner>/<repo> URL."""
    if not text:
        return None
    m = GITHUB_URL_RE.search(text)
    if not m:
        return None
    # Strip trailing punctuation that can sneak in
    url = m.group(0).rstrip(".,);:")
    # Drop sub-paths — we only care about the repo root
    parts = url.split("/")
    if len(parts) >= 5:
        return "/".join(parts[:5])
    return url
