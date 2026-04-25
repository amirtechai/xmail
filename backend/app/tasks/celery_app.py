"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "xmail",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.daily_discovery_run",
        "app.tasks.daily_report_generation",
        "app.tasks.daily_report_delivery",
        "app.tasks.suppression_sync",
        "app.tasks.bounce_processing",
        "app.tasks.dea_list_update",
        "app.tasks.stale_verification_cleanup",
        "app.tasks.bloom_filter_snapshot",
        "app.tasks.scraping_task",
        "app.tasks.bulk_verify_task",
        "app.tasks.sequence_runner",
        "app.tasks.rss_scraping_task",
        "app.tasks.webhook_processor",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=600,   # 10 min soft
    task_time_limit=900,        # 15 min hard
    result_expires=86400,       # 24h
    worker_max_tasks_per_child=200,
)
