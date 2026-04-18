from __future__ import annotations

from celery import Celery

from core.settings import get_settings


def make_celery() -> Celery:
    settings = get_settings()
    app = Celery(
        "grad",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[],  # Phase 1 will register pipelines here
    )
    app.conf.update(
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        timezone="UTC",
        enable_utc=True,
        beat_schedule={},  # Phase 1 will populate
    )
    return app


celery_app = make_celery()
