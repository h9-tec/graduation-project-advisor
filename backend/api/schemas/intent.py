from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Domain = Literal[
    "nlp",
    "cv",
    "rl",
    "mlops",
    "agents",
    "rag",
    "robotics",
    "audio",
    "timeseries",
    "security",
    "iot",
    "web",
    "mobile",
    "data_engineering",
]

SkillLevel = Literal["beginner", "intermediate", "advanced"]
Language = Literal["ar", "en"]


class IntentProfile(BaseModel):
    language: Language = "en"
    domains: list[Domain] = Field(default_factory=list)
    skill_level: SkillLevel = "intermediate"
    months_available: int = Field(default=6, ge=2, le=12)
    team_size: int = Field(default=1, ge=1, le=5)
    preferred_stacks: list[str] = Field(default_factory=list)
    interests_text: str = Field(default="", max_length=500)
    requires_code_reference: bool = True
    avoid: list[str] = Field(default_factory=list)
