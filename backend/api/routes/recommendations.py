from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.schemas.blueprint import Blueprint, BlueprintResponse
from api.schemas.intent import IntentProfile
from api.schemas.recommendation import LeanCard, RecommendationsResponse
from core.llm.gateway import chat_json
from core.llm.prompts import (
    blueprint_system_prompt,
    blueprint_user_prompt,
    rec_system_prompt,
    rec_user_prompt,
)
from core.llm.prompts_rag import rerank_system_prompt, rerank_user_prompt
from core.recommendation.retrieve import pre_score, retrieve
from core.session_store import (
    load_cards,
    load_profile,
    save_blueprint,
    save_cards,
    save_profile,
)

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

# Minimum Qdrant hits before we trust retrieval; below this we fall back to pure LLM.
RETRIEVAL_FLOOR = 8


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or uuid.uuid4().hex[:8]


@router.post("/recommendations", response_model=RecommendationsResponse)
async def create_recommendations(profile: IntentProfile) -> RecommendationsResponse:
    session_id = uuid.uuid4().hex
    await save_profile(session_id, profile.model_dump())

    # ---------- RAG path: retrieve → pre-score → LLM re-rank -----------
    hits = await retrieve(profile, top_k=50)
    logger.info(f"retrieve: {len(hits)} hits from Qdrant (floor={RETRIEVAL_FLOOR})")

    if len(hits) >= RETRIEVAL_FLOOR:
        top = pre_score(hits, profile, keep=20)
        cands = [
            {
                "id": c.point_id,
                "title": c.payload.get("title", ""),
                "summary": c.payload.get("summary", ""),
                "stars": c.payload.get("stars", 0),
                "ai_keywords": c.payload.get("ai_keywords") or [],
                "github_url": c.payload.get("github_url"),
                "arxiv_url": (
                    f"https://arxiv.org/abs/{c.payload['arxiv_id']}"
                    if c.payload.get("arxiv_id")
                    else None
                ),
            }
            for c in top
        ]
        rag_system = rerank_system_prompt(profile.language)
        rag_user = rerank_user_prompt(profile.model_dump(), cands)

        try:
            raw = await chat_json(
                tier="fast",
                system=rag_system,
                user=rag_user,
                max_tokens=1600,
                temperature=0.3,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"LLM re-rank failed: {exc}"
            ) from exc

        valid_ids = {c["id"] for c in cands}
        ranked_items = raw.get("ranked", [])
        cards: list[LeanCard] = []
        id_to_meta = {c["id"]: c for c in cands}
        id_to_payload = {c.point_id: c.payload for c in top}

        for i, item in enumerate(ranked_items[:5], start=1):
            cid = str(item.get("id", ""))
            if cid not in valid_ids:
                logger.warning(f"re-rank hallucinated id={cid}, dropping")
                continue
            meta = id_to_meta[cid]
            payload = id_to_payload.get(cid) or {}
            cards.append(
                LeanCard(
                    id=cid,
                    rank=int(item.get("rank", i)),
                    title=meta["title"],
                    domains=(payload.get("ai_keywords") or [])[:3]
                    or payload.get("domains", []),
                    why_fit=str(item.get("why_fit", "")),
                    est_weeks=int(item.get("est_weeks", profile.months_available * 4)),
                    difficulty_verdict=str(
                        item.get("difficulty_verdict", profile.skill_level)
                    ),
                    research_hook=(meta.get("summary") or "")[:200],
                    stack_hook=(
                        f"Reference: {meta['github_url']}"
                        if meta.get("github_url")
                        else f"Paper: {meta.get('arxiv_url') or ''}"
                    ),
                    stars_estimate=int(meta.get("stars") or 0),
                )
            )

        if cards:
            await save_cards(session_id, [c.model_dump() for c in cards])
            logger.info(f"rag: returned {len(cards)} cards (session {session_id})")
            return RecommendationsResponse(session_id=session_id, cards=cards)

        logger.warning("rag: all re-rank ids were invalid, falling back to pure-LLM")

    # ---------- Fallback: pure-LLM (Phase-0 behavior) ------------------
    system = rec_system_prompt(profile.language)
    user = rec_user_prompt(profile.model_dump())

    try:
        raw = await chat_json(
            tier="fast",
            system=system,
            user=user,
            max_tokens=1600,
            temperature=0.7,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    ranked = raw.get("ranked", [])
    if not ranked:
        raise HTTPException(status_code=502, detail="LLM returned no ranked items")

    cards: list[LeanCard] = []
    seen_ids: set[str] = set()
    for i, item in enumerate(ranked[:5], start=1):
        raw_id = str(item.get("id") or item.get("title") or f"card-{i}")
        card_id = _slug(raw_id)
        if card_id in seen_ids:
            card_id = f"{card_id}-{i}"
        seen_ids.add(card_id)

        cards.append(
            LeanCard(
                id=card_id,
                rank=int(item.get("rank", i)),
                title=str(item.get("title", "Untitled project")),
                domains=list(item.get("domains", [])),
                why_fit=str(item.get("why_fit", "")),
                est_weeks=int(item.get("est_weeks", profile.months_available * 4)),
                difficulty_verdict=str(item.get("difficulty_verdict", profile.skill_level)),
                research_hook=str(item.get("research_hook", "")),
                stack_hook=str(item.get("stack_hook", "")),
                stars_estimate=int(item.get("stars_estimate", 1000)),
            )
        )

    await save_cards(session_id, [c.model_dump() for c in cards])
    return RecommendationsResponse(session_id=session_id, cards=cards)


@router.get("/sessions/{session_id}/cards", response_model=list[LeanCard])
async def list_cards(session_id: str) -> list[LeanCard]:
    cards = await load_cards(session_id)
    if cards is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return [LeanCard(**c) for c in cards]


@router.post(
    "/sessions/{session_id}/cards/{card_id}/expand",
    response_model=BlueprintResponse,
)
async def expand_card(session_id: str, card_id: str) -> BlueprintResponse:
    cards = await load_cards(session_id)
    profile = await load_profile(session_id)
    if cards is None or profile is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    card = next((c for c in cards if c["id"] == card_id), None)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found in session")

    language = profile.get("language", "en")
    system = blueprint_system_prompt(language)
    user = blueprint_user_prompt(card, profile)

    try:
        raw = await chat_json(
            tier="smart",
            system=system,
            user=user,
            max_tokens=2800,
            temperature=0.5,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    try:
        bp = Blueprint.model_validate(raw)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM returned malformed blueprint: {exc}") from exc

    await save_blueprint(session_id, card_id, bp.model_dump())
    return BlueprintResponse(card_id=card_id, blueprint=bp)
