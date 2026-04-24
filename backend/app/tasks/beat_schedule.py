"""Celery Beat periodic task schedule.

All times are UTC. Istanbul (UTC+3):
  - 08:30 UTC+3 = 05:30 UTC
  - 09:00 UTC+3 = 06:00 UTC
  - 04:00 UTC+3 = 01:00 UTC
"""

from celery.schedules import crontab

from app.tasks.celery_app import celery_app

celery_app.conf.beat_schedule = {
    # Discovery: run every hour during business hours UTC (07:00–19:00)
    "hourly-discovery": {
        "task": "app.tasks.daily_discovery_run.run_discovery_cycle",
        "schedule": crontab(minute=0),
    },

    # Daily report generation: 05:30 UTC (08:30 Istanbul)
    "daily-report-generate": {
        "task": "app.tasks.daily_report_generation.generate_daily_report",
        "schedule": crontab(hour=5, minute=30),
    },

    # Daily report delivery: 06:00 UTC (09:00 Istanbul)
    "daily-report-deliver": {
        "task": "app.tasks.daily_report_delivery.deliver_daily_report",
        "schedule": crontab(hour=6, minute=0),
    },

    # Suppression list sync: every 15 minutes
    "suppression-sync": {
        "task": "app.tasks.suppression_sync.sync_suppression_list",
        "schedule": crontab(minute="*/15"),
    },

    # Bounce processing: every 30 minutes
    "bounce-processing": {
        "task": "app.tasks.bounce_processing.process_bounces",
        "schedule": crontab(minute="*/30"),
    },

    # DEA list update: daily 01:00 UTC (04:00 Istanbul)
    "dea-list-update": {
        "task": "app.tasks.dea_list_update.update_dea_list",
        "schedule": crontab(hour=1, minute=0),
    },

    # Stale verification cleanup: weekly Monday 02:00 UTC
    "stale-verification-cleanup": {
        "task": "app.tasks.stale_verification_cleanup.cleanup_stale_verifications",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),
    },

    # Bloom filter snapshot: daily 03:00 UTC
    "bloom-filter-snapshot": {
        "task": "app.tasks.bloom_filter_snapshot.snapshot_bloom_filter",
        "schedule": crontab(hour=3, minute=0),
    },

    # Drip-sequence runner: daily 07:30 UTC (10:30 Istanbul)
    "sequence-runner": {
        "task": "app.tasks.sequence_runner.run_sequences",
        "schedule": crontab(hour=7, minute=30),
    },

    # RSS feed refresh: daily 06:00 UTC (09:00 Istanbul) — before discovery cycle
    "rss-feed-refresh": {
        "task": "app.tasks.rss_scraping_task.refresh_rss_feeds",
        "schedule": crontab(hour=6, minute=0),
    },
}
