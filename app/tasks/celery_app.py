from celery import Celery
from app.core.config import settings

celery_app = Celery("tasks", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "check-expirations": {
        "task": "app.tasks.periodic.check_expirations_and_notify",
        "schedule": 86400.0,
    },
}