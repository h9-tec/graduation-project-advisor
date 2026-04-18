from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from core.settings import get_settings


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "grad",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["ingestion.tasks"],
    )
    app.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        task_time_limit=3600,              # 1h hard
        task_soft_time_limit=3300,         # 55m soft
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            # HF Daily curates on US Pacific evenings; 4-per-day covers drift.
            "hf-daily-papers-every-6h": {
                "task": "ingestion.tasks.run_hf_daily_papers",
                "schedule": crontab(minute=0, hour="*/6"),
                "args": (2,),
            },
            "arxiv-delta-nightly": {
                "task": "ingestion.tasks.run_arxiv_delta",
                "schedule": crontab(minute=0, hour=3),
                "args": (2, 500),
            },
            "github-trending-weekly": {
                "task": "ingestion.tasks.run_github_trending",
                "schedule": crontab(minute=0, hour=4, day_of_week=0),  # Sunday
                "args": (25,),
            },
        },
    )
    return app


celery_app = make_celery()
