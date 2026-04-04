from app.workers.celery_app import QUEUE_NAMES, celery_app


def test_celery_queues_are_configured_for_pipeline() -> None:
    configured_queue_names = [queue.name for queue in celery_app.conf.task_queues]

    assert configured_queue_names == list(QUEUE_NAMES)
    assert celery_app.conf.task_default_queue == "collect.queue"


def test_celery_routes_cover_all_pipeline_stages() -> None:
    routes = celery_app.conf.task_routes

    assert routes["app.workers.tasks.collect.*"]["queue"] == "collect.queue"
    assert routes["app.workers.tasks.parse.*"]["queue"] == "parse.queue"
    assert routes["app.workers.tasks.analysis.*"]["queue"] == "analysis.queue"
    assert routes["app.workers.tasks.correlate.*"]["queue"] == "correlate.queue"
    assert routes["app.workers.tasks.score.*"]["queue"] == "score.queue"
    assert routes["app.workers.tasks.recommend.*"]["queue"] == "recommend.queue"
    assert routes["app.workers.tasks.alert.*"]["queue"] == "alert.queue"
