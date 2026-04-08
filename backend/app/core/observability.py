from __future__ import annotations

import logging
import sys

import structlog
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def configure_structured_logging(*, log_level: str) -> None:
    level = _to_logging_level(log_level)

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_metrics(*, app: FastAPI, enabled: bool = True) -> None:
    if not enabled:
        return
    Instrumentator(should_group_status_codes=False).instrument(app).expose(app)


def setup_opentelemetry(*, app: FastAPI, enabled: bool = True) -> None:
    if not enabled:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except Exception:
        return

    FastAPIInstrumentor.instrument_app(app)


def _to_logging_level(value: str) -> int:
    normalized = value.strip().upper()
    if normalized == "CRITICAL":
        return logging.CRITICAL
    if normalized == "ERROR":
        return logging.ERROR
    if normalized == "WARNING":
        return logging.WARNING
    if normalized == "DEBUG":
        return logging.DEBUG
    return logging.INFO
