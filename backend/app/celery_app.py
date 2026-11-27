from celery import Celery
from app.core.config import settings

celery_app = Celery("stockfish_review", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"],
    timezone="UTC", enable_utc=True,
    beat_schedule={
        "scheduled-chesscom-sync": {"task": "app.tasks.sync_due_accounts", "schedule": 60 * 60 * 12},
        "drain-analysis-queue": {"task": "app.tasks.drain_analysis_queue", "schedule": 2.0},
        "auto-analyze-imported-games": {"task": "app.tasks.auto_analyze_unreviewed", "schedule": 30.0},
    },
)
celery_app.autodiscover_tasks(["app"])
