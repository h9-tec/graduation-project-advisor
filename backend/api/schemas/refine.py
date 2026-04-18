from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.recommendation import LeanCard


class RefineRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class RefineResponse(BaseModel):
    session_id: str
    cards: list[LeanCard]
    assistant_msg: str
    refinement_count: int
    history_depth: int
