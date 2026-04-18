from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.db.models import DeadLetter, IngestionRun, ProjectCandidate
from core.embeddings.qdrant_client import count_points
from core.settings import get_settings

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


class PerSource(BaseModel):
    source: str
    postgres_count: int
    last_run_started_at: datetime | None
    last_run_finished_at: datetime | None
    last_run_status: str | None
    last_run_new: int
    last_run_updated: int
    last_run_embedded: int
    last_run_dead_lettered: int
    last_error: str | None
    unresolved_dead_letter_count: int


class IngestStatusResponse(BaseModel):
    qdrant_points: int
    total_candidates: int
    per_source: list[PerSource]


def _engine() -> Any:
    return create_async_engine(get_settings().database_url, future=True)


@router.get("/status", response_model=IngestStatusResponse)
async def ingest_status() -> IngestStatusResponse:
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)

    sources: list[str] = []
    per_source_counts: dict[str, int] = {}
    total_candidates = 0
    async with sm() as session:
        r = await session.execute(
            select(
                ProjectCandidate.source,
                func.count(ProjectCandidate.id),
            ).group_by(ProjectCandidate.source)
        )
        for src, cnt in r.all():
            sources.append(src)
            per_source_counts[src] = int(cnt)
            total_candidates += int(cnt)

        out: list[PerSource] = []
        for src in sources or ["hf_daily_papers", "arxiv", "github_trending"]:
            last_run = (
                await session.execute(
                    select(IngestionRun)
                    .where(IngestionRun.source == src)
                    .order_by(IngestionRun.started_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            dlq_count = int(
                (
                    await session.execute(
                        select(func.count(DeadLetter.id)).where(
                            DeadLetter.source == src,
                            DeadLetter.resolved_at.is_(None),
                        )
                    )
                ).scalar_one()
            )

            out.append(
                PerSource(
                    source=src,
                    postgres_count=per_source_counts.get(src, 0),
                    last_run_started_at=last_run.started_at if last_run else None,
                    last_run_finished_at=last_run.finished_at if last_run else None,
                    last_run_status=last_run.status if last_run else None,
                    last_run_new=last_run.new_records if last_run else 0,
                    last_run_updated=last_run.updated_records if last_run else 0,
                    last_run_embedded=last_run.embedded_records if last_run else 0,
                    last_run_dead_lettered=(
                        last_run.dead_lettered if last_run else 0
                    ),
                    last_error=last_run.last_error if last_run else None,
                    unresolved_dead_letter_count=dlq_count,
                )
            )

    await engine.dispose()
    qdrant = await count_points()
    return IngestStatusResponse(
        qdrant_points=qdrant,
        total_candidates=total_candidates,
        per_source=out,
    )
