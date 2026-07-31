"""Structured logging configuration for InsightDocs.

Configures Python's standard logging to emit JSON-structured log records
in production environments (APP_ENV != "development"), or plain text with
timestamps in development. This is the observability foundation required
by the architecture — every subsystem logs through this configuration.

Usage:
    Call configure_logging() once at application startup (main.py and
    celery_app.py). Individual modules use the standard
    `logging.getLogger(__name__)` pattern unchanged.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from backend.config import settings


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for machine-readable log ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[1]:
            payload["exception"] = self.formatException(record.exc_info)
        # Merge any extra structured fields attached via logger.info("msg", extra={...})
        for key in ("user_id", "document_id", "task_id", "query_id", "duration_ms", "status_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


class _DevFormatter(logging.Formatter):
    """Human-readable format for local development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s:%(funcName)s:%(lineno)d — %(message)s",
            datefmt="%H:%M:%S",
        )


def configure_logging() -> None:
    """Configure root logger for the current environment.

    Call once at process startup. Safe to call multiple times (idempotent
    after the first call via a guard flag on the root logger).
    """
    root = logging.getLogger()

    # Guard: don't reconfigure if already set up by a prior call.
    if getattr(root, "_insightdocs_configured", False):
        return
    root._insightdocs_configured = True  # type: ignore[attr-defined]

    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    if settings.app_env == "development":
        handler.setFormatter(_DevFormatter())
    else:
        handler.setFormatter(_JsonFormatter())

    # Replace any existing handlers (e.g. from basicConfig in main.py)
    root.handlers = [handler]

    # Reduce noise from chatty third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
