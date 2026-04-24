"""Celery tasks package. Import beat_schedule to register periodic tasks."""

# Importing beat_schedule registers the Celery Beat schedule
from app.tasks import beat_schedule as beat_schedule  # noqa: F401
