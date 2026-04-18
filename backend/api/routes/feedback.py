from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.schemas.recommendation import LeanCard
from core.db.models import Feedback
from core.session_store import (
    list_saved_cards,
    load_cards,
    load_profile,
    save_card_for_session,
    unsave_card_for_session,
)
from core.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    session_id: str = Field(..., min_length=4, max_length=128)
    card_id: str = Field(..., min_length=1, max_length=128)
    reaction: Literal["up", "down"]


class FeedbackResponse(BaseModel):
    feedback_id: str


class SaveRequest(BaseModel):
    card_id: str = Field(..., min_length=1, max_length=128)


class SavedListResponse(BaseModel):
    cards: list[LeanCard]


class EvalRow(BaseModel):
    feedback_id: str
    reaction: str
    card_id: str
    created_at: str
    profile_domains: list[str]
    profile_skill_level: str | None
    profile_interests_text: str | None
    card_title: str
    card_stars: int
    card_github_url: str | None
    card_arxiv_url: str | None


def _engine() -> object:
    settings = get_settings()
    return create_async_engine(settings.database_url, future=True)


@router.post("/feedback", response_model=FeedbackResponse)
async def post_feedback(body: FeedbackRequest) -> FeedbackResponse:
    """Persist a thumbs up/down, snapshotting the intent + card for eval use."""
    profile = await load_profile(body.session_id)
    cards = await load_cards(body.session_id)
    if profile is None or cards is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    card = next((c for c in cards if c.get("id") == body.card_id), None)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found in session")

    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    fb = Feedback(
        id=uuid.uuid4(),
        session_id=body.session_id,
        card_id=body.card_id,
        reaction=body.reaction,
        profile_snapshot=profile,
        card_snapshot=card,
    )
    async with sm() as session:
        session.add(fb)
        await session.commit()
    await engine.dispose()
    return FeedbackResponse(feedback_id=str(fb.id))


@router.get("/sessions/{session_id}/saved", response_model=SavedListResponse)
async def list_saved(session_id: str) -> SavedListResponse:
    rows = await list_saved_cards(session_id)
    return SavedListResponse(cards=[LeanCard(**r) for r in rows])


@router.post("/sessions/{session_id}/saved", response_model=SavedListResponse)
async def save_card(session_id: str, body: SaveRequest) -> SavedListResponse:
    cards = await load_cards(session_id)
    if cards is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    card = next((c for c in cards if c.get("id") == body.card_id), None)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found in session")

    await save_card_for_session(session_id, card)
    rows = await list_saved_cards(session_id)
    return SavedListResponse(cards=[LeanCard(**r) for r in rows])


@router.delete(
    "/sessions/{session_id}/saved/{card_id}", response_model=SavedListResponse
)
async def unsave_card(session_id: str, card_id: str) -> SavedListResponse:
    await unsave_card_for_session(session_id, card_id)
    rows = await list_saved_cards(session_id)
    return SavedListResponse(cards=[LeanCard(**r) for r in rows])


@router.get("/eval/dataset", response_model=list[EvalRow])
async def eval_dataset(limit: int = 1000) -> list[EvalRow]:
    """Dump recent feedback rows for eval-set construction.

    Used by the offline eval harness. Not gated by auth in this phase —
    feedback is non-sensitive and only addressable via the opaque feedback id.
    """
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        q = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
        rows = (await session.execute(q)).scalars().all()

    out: list[EvalRow] = []
    for fb in rows:
        profile = fb.profile_snapshot or {}
        card = fb.card_snapshot or {}
        out.append(
            EvalRow(
                feedback_id=str(fb.id),
                reaction=fb.reaction,
                card_id=fb.card_id,
                created_at=fb.created_at.isoformat() if fb.created_at else "",
                profile_domains=list(profile.get("domains") or []),
                profile_skill_level=profile.get("skill_level"),
                profile_interests_text=profile.get("interests_text"),
                card_title=str(card.get("title") or ""),
                card_stars=int(card.get("stars_estimate") or 0),
                card_github_url=card.get("github_url"),
                card_arxiv_url=card.get("arxiv_url"),
            )
        )
    await engine.dispose()
    return out
