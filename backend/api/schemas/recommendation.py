from __future__ import annotations

from pydantic import BaseModel


class LeanCard(BaseModel):
    id: str
    rank: int
    title: str
    domains: list[str]
    why_fit: str
    est_weeks: int
    difficulty_verdict: str
    research_hook: str
    stack_hook: str
    stars_estimate: int


class RecommendationsResponse(BaseModel):
    session_id: str
    cards: list[LeanCard]
