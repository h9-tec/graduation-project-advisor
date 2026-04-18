from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, HTTPException

from api.schemas.blueprint import Blueprint, BlueprintResponse
from api.schemas.intent import IntentProfile
from api.schemas.recommendation import LeanCard, RecommendationsResponse
from core.llm.azure import chat_json
from core.llm.prompts import (
    blueprint_system_prompt,
    blueprint_user_prompt,
    rec_system_prompt,
    rec_user_prompt,
)
from core.session_store import (
    load_cards,
    load_profile,
    save_blueprint,
    save_cards,
    save_profile,
)
from core.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or uuid.uuid4().hex[:8]


@router.post("/recommendations", response_model=RecommendationsResponse)
async def create_recommendations(profile: IntentProfile) -> RecommendationsResponse:
    settings = get_settings()
    session_id = uuid.uuid4().hex

    await save_profile(session_id, profile.model_dump())

    system = rec_system_prompt(profile.language)
    user = rec_user_prompt(profile.model_dump())

    try:
        raw = await chat_json(
            deployment=settings.azure_openai_deployment_fast,
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
    settings = get_settings()
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
            deployment=settings.azure_openai_deployment_smart,
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
