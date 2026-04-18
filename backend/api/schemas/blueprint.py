from __future__ import annotations

from pydantic import BaseModel


class Milestone(BaseModel):
    weeks: str
    goals: list[str]


class DatasetRef(BaseModel):
    name: str
    url: str | None = None
    note: str = ""


class RiskItem(BaseModel):
    risk: str
    mitigation: str


class Ref(BaseModel):
    name: str | None = None
    title: str | None = None
    note: str = ""


class Blueprint(BaseModel):
    problem_statement: str
    why_it_matters: str
    in_scope: list[str]
    out_of_scope: list[str]
    suggested_architecture: str
    tech_stack: list[str]
    milestones_by_week: list[Milestone]
    datasets: list[DatasetRef]
    evaluation_metrics: list[str]
    risks_and_mitigations: list[RiskItem]
    how_to_stand_out: list[str]
    paper_refs: list[Ref]
    repo_refs: list[Ref]


class BlueprintResponse(BaseModel):
    card_id: str
    blueprint: Blueprint
