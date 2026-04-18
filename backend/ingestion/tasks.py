"""Celery task wrappers around the ingestion runner.

Each task gets autoretry_for=Exception with exponential backoff so a
transient upstream hiccup (rate limit, 5xx from arXiv, etc.) retries
without human action. Terminal failures after max_retries are logged
and surface in the IngestionRun row (status=failed).
"""
from __future__ import annotations

from celery.utils.log import get_task_logger

from ingestion.celery_app import celery_app
from ingestion.runner import (
    run_arxiv_delta_sync,
    run_github_trending_sync,
    run_hf_daily_papers_sync,
)

logger = get_task_logger(__name__)

RETRY_KW = {
    "autoretry_for": (Exception,),
    "retry_backoff": 60,          # start at 60s
    "retry_backoff_max": 1800,    # cap at 30 min
    "retry_jitter": True,
    "max_retries": 3,
}


@celery_app.task(name="ingestion.tasks.run_hf_daily_papers", bind=True, **RETRY_KW)
def run_hf_daily_papers(self, days: int = 2) -> dict[str, int]:
    logger.info(f"run_hf_daily_papers days={days} retry={self.request.retries}")
    return run_hf_daily_papers_sync(days=days)


@celery_app.task(name="ingestion.tasks.run_arxiv_delta", bind=True, **RETRY_KW)
def run_arxiv_delta(self, days: int = 2, max_records: int = 500) -> dict[str, int]:
    logger.info(
        f"run_arxiv_delta days={days} max={max_records} retry={self.request.retries}"
    )
    return run_arxiv_delta_sync(days=days, max_records=max_records)


@celery_app.task(name="ingestion.tasks.run_github_trending", bind=True, **RETRY_KW)
def run_github_trending(self, count: int = 25) -> dict[str, int]:
    logger.info(f"run_github_trending count={count} retry={self.request.retries}")
    return run_github_trending_sync(count=count)
