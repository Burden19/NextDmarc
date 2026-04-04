from celery import Celery
from celery.schedules import crontab
from kombu import Queue

from app.core.config import get_settings

settings = get_settings()

QUEUE_NAMES: tuple[str, ...] = (
    "collect.queue",
    "parse.queue",
    "analysis.queue",
    "correlate.queue",
    "score.queue",
    "recommend.queue",
    "alert.queue",
)

celery_app = Celery(
    "nextdmarc",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.collect",
        "app.workers.tasks.parse",
        "app.workers.tasks.analysis",
        "app.workers.tasks.correlate",
        "app.workers.tasks.score",
        "app.workers.tasks.recommend",
    ],
)

celery_app.conf.update(
    task_default_queue="collect.queue",
    task_queues=tuple(Queue(name) for name in QUEUE_NAMES),
    task_routes={
        "app.workers.tasks.collect.*": {"queue": "collect.queue"},
        "app.workers.tasks.parse.*": {"queue": "parse.queue"},
        "app.workers.tasks.analysis.*": {"queue": "analysis.queue"},
        "app.workers.tasks.correlate.*": {"queue": "correlate.queue"},
        "app.workers.tasks.score.*": {"queue": "score.queue"},
        "app.workers.tasks.recommend.*": {"queue": "recommend.queue"},
        "app.workers.tasks.alert.*": {"queue": "alert.queue"},
    },
    timezone=settings.celery_timezone,
    enable_utc=True,
    beat_schedule={
        "poll-mailboxes-every-5-minutes": {
            "task": "app.workers.tasks.collect.poll_active_mailboxes",
            "schedule": crontab(minute="*/5"),
        }
    },
)
