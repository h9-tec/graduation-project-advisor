"""Scheduled-ingestion runner.

Wraps each pipeline with:
  - `IngestionRun` row (status=running → succeeded|partial|failed, counts, last_error)
  - per-item dead-letter capture for bad records (no whole-run aborts)
  - retries happen at the Celery task boundary (autoretry_for=Exception)

The runner is source-agnostic: each pipeline returns a list of
`NormalizedCandidate` objects, the runner handles persistence.
"""
from __future__ import annotations

import asyncio
import traceback
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.db.models import DeadLetter, IngestionRun
from core.settings import get_settings
from ingestion.normalize import NormalizedCandidate
from ingestion.upsert import ingest

PipelineFetcher = Callable[[], Awaitable[list[NormalizedCandidate]]]


def _engine() -> Any:
    return create_async_engine(get_settings().database_url, future=True)


async def _start_run(source: str) -> uuid.UUID:
    run_id = uuid.uuid4()
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        session.add(
            IngestionRun(id=run_id, source=source, status="running")
        )
        await session.commit()
    await engine.dispose()
    return run_id


async def _finish_run(
    run_id: uuid.UUID,
    *,
    status: str,
    counts: dict[str, int],
    last_error: str | None,
) -> None:
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        row = await session.get(IngestionRun, run_id)
        if row is None:
            return
        row.status = status
        row.finished_at = datetime.now(tz=timezone.utc)
        row.total_fetched = counts.get("total", 0)
        row.new_records = counts.get("new", 0)
        row.updated_records = counts.get("updated", 0)
        row.embedded_records = counts.get("embedded", 0)
        row.dead_lettered = counts.get("dead_lettered", 0)
        row.last_error = last_error
        await session.commit()
    await engine.dispose()


async def _dead_letter(
    source: str, stage: str, candidate: NormalizedCandidate, error: str
) -> None:
    engine = _engine()
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as session:
        session.add(
            DeadLetter(
                id=uuid.uuid4(),
                source=source,
                stage=stage,
                external_id=candidate.arxiv_id or candidate.github_url,
                payload=_cand_to_dict(candidate),
                error=error[:4000],
                retries=0,
            )
        )
        await session.commit()
    await engine.dispose()


def _cand_to_dict(cand: NormalizedCandidate) -> dict[str, Any]:
    d = asdict(cand)
    # dataclasses with date/datetime need stringification for JSON
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d


async def run_pipeline(source: str, fetcher: PipelineFetcher) -> dict[str, int]:
    """Execute a pipeline end-to-end with observability + per-item DLQ.

    Returns the ingest counts. Re-raises any fatal error after recording
    status=failed on the IngestionRun — the Celery task wrapper sees that
    and decides whether to retry the whole job.
    """
    run_id = await _start_run(source)
    counts: dict[str, int] = {
        "total": 0,
        "new": 0,
        "updated": 0,
        "embedded": 0,
        "dead_lettered": 0,
    }
    try:
        candidates = await fetcher()
        counts["total"] = len(candidates)

        # Validate per-record before handing to the upsert batch. An item
        # that fails validation goes to dead_letter; the rest proceed.
        good: list[NormalizedCandidate] = []
        for c in candidates:
            try:
                if not c.title:
                    raise ValueError("missing title")
                good.append(c)
            except Exception as exc:  # noqa: BLE001
                await _dead_letter(source, "normalize", c, str(exc))
                counts["dead_lettered"] += 1

        result = await ingest(good)
        counts["new"] = result.get("new", 0)
        counts["updated"] = result.get("updated", 0)
        counts["embedded"] = result.get("embedded", 0)

        status = "succeeded" if counts["dead_lettered"] == 0 else "partial"
        await _finish_run(run_id, status=status, counts=counts, last_error=None)
        logger.info(f"run_pipeline {source} {status}: {counts}")
        return counts

    except Exception as exc:  # noqa: BLE001
        trace = traceback.format_exc()
        await _finish_run(
            run_id,
            status="failed",
            counts=counts,
            last_error=f"{exc}\n{trace[:2000]}",
        )
        logger.error(f"run_pipeline {source} failed: {exc}")
        raise


# ---------- pipeline fetchers bound for Celery -----------------------------

async def _fetch_hf(days: int) -> list[NormalizedCandidate]:
    from ingestion.pipelines.hf_papers import fetch_recent

    return await fetch_recent(days=days)


async def _fetch_arxiv(days: int, max_records: int) -> list[NormalizedCandidate]:
    from ingestion.pipelines.arxiv import fetch_recent

    return await fetch_recent(days=days, max_records=max_records)


async def _fetch_github(count: int) -> list[NormalizedCandidate]:
    from ingestion.pipelines.github_trending import fetch_trending

    return await fetch_trending(count=count)


def run_hf_daily_papers_sync(days: int = 2) -> dict[str, int]:
    return asyncio.run(run_pipeline("hf_daily_papers", lambda: _fetch_hf(days)))


def run_arxiv_delta_sync(
    days: int = 2, max_records: int = 500
) -> dict[str, int]:
    return asyncio.run(
        run_pipeline("arxiv", lambda: _fetch_arxiv(days, max_records))
    )


def run_github_trending_sync(count: int = 25) -> dict[str, int]:
    return asyncio.run(
        run_pipeline("github_trending", lambda: _fetch_github(count))
    )
