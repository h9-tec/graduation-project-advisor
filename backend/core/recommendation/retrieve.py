from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger
from qdrant_client.http import models as qm

from api.schemas.intent import IntentProfile
from core.embeddings.encoder import embed
from core.embeddings.qdrant_client import COLLECTION, get_qdrant

# Deterministic pre-score weights (documented in spec §7.3)
W_SIM = 0.50
W_QUALITY = 0.20
W_RECENCY = 0.10
W_HAS_CODE = 0.10
W_DIFFICULTY = 0.10

SKILL_TO_LEVEL = {"beginner": 1, "intermediate": 2, "advanced": 3}


@dataclass
class ScoredCandidate:
    point_id: str
    payload: dict[str, Any]
    similarity: float
    score: float


def _recency_bonus(published_year: int | None, current_year: int = 2026) -> float:
    """1.0 for this year, 0.5 two years ago, 0.0 for >=5 years old."""
    if not published_year:
        return 0.0
    diff = current_year - published_year
    if diff <= 0:
        return 1.0
    if diff >= 5:
        return 0.0
    return max(0.0, 1.0 - diff / 5)


def _difficulty_match(profile_level: int, candidate_level: int | None) -> float:
    """1.0 if candidate difficulty matches, 0.5 if one step off, 0 otherwise."""
    if candidate_level is None:
        return 0.5  # unknown = mild penalty
    diff = abs(candidate_level - profile_level)
    return max(0.0, 1.0 - diff * 0.4)


def build_filter(profile: IntentProfile) -> qm.Filter | None:
    """Loose filter — we use OR on domains/keywords so we get enough recall.

    Intentionally permissive; the pre-score + LLM re-rank sort it out.
    """
    must: list[qm.Condition] = []
    should: list[qm.Condition] = []

    # has_code only when the student explicitly wants a reference
    if profile.requires_code_reference:
        should.append(qm.FieldCondition(key="has_code", match=qm.MatchValue(value=True)))

    # domains: match the profile's declared domains against either stored
    # `domains` (our LLM-tagged) or `ai_keywords` (HF-pre-tagged)
    if profile.domains:
        for dom in profile.domains:
            should.append(
                qm.FieldCondition(key="domains", match=qm.MatchValue(value=dom))
            )
            should.append(
                qm.FieldCondition(key="ai_keywords", match=qm.MatchValue(value=dom))
            )

    if must or should:
        return qm.Filter(must=must or None, should=should or None)
    return None


async def retrieve(
    profile: IntentProfile,
    *,
    top_k: int = 50,
) -> list[qm.ScoredPoint]:
    """ANN over Qdrant with a loose filter. Returns raw scored points."""
    query_text = " ".join(
        [
            profile.interests_text,
            " ".join(profile.domains),
            profile.skill_level,
            " ".join(profile.preferred_stacks),
        ]
    ).strip()
    if not query_text:
        query_text = "machine learning graduation project"

    vec = await embed(query_text)
    client = get_qdrant()

    f = build_filter(profile)
    try:
        result = await client.query_points(
            collection_name=COLLECTION,
            query=vec,
            query_filter=f,
            limit=top_k,
            with_payload=True,
        )
    except Exception as exc:
        logger.warning(f"Qdrant retrieval failed: {exc}")
        return []
    return result.points


def pre_score(
    points: list[qm.ScoredPoint], profile: IntentProfile, *, keep: int = 20
) -> list[ScoredCandidate]:
    """Deterministic re-weight over the ANN hits, then truncate to top-N."""
    profile_level = SKILL_TO_LEVEL.get(profile.skill_level, 2)
    current_year = 2026

    scored: list[ScoredCandidate] = []
    for p in points:
        pl = p.payload or {}
        sim = float(p.score or 0.0)
        quality = float(pl.get("quality_score") or 0.0)
        recency = _recency_bonus(pl.get("published_year"), current_year)
        has_code = 1.0 if pl.get("has_code") else 0.0
        diff = _difficulty_match(profile_level, pl.get("difficulty_level"))

        score = (
            W_SIM * sim
            + W_QUALITY * quality
            + W_RECENCY * recency
            + W_HAS_CODE * has_code
            + W_DIFFICULTY * diff
        )
        scored.append(
            ScoredCandidate(
                point_id=str(p.id),
                payload=pl,
                similarity=sim,
                score=score,
            )
        )

    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:keep]
