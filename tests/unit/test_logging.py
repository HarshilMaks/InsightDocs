"""Test structured logging configuration."""
import json
import logging
from unittest.mock import patch

from backend.core.logging import configure_logging


def test_configure_logging_produces_json_in_production(tmp_path):
    """In non-development environments, logs should be JSON-structured."""
    root = logging.getLogger()
    root._insightdocs_configured = False  # Reset guard
    root.handlers = []  # Clear any handlers from prior tests

    with patch("backend.core.logging.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.log_level = "INFO"
        configure_logging()

    handler = logging.getLogger().handlers[0]
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="hello world", args=(), exc_info=None
    )
    output = handler.formatter.format(record)
    data = json.loads(output)
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert "timestamp" in data

    # Reset for other tests
    logging.getLogger()._insightdocs_configured = False


def test_configure_logging_uses_dev_format_in_development():
    """In development mode, logs should be human-readable, not JSON."""
    logging.getLogger()._insightdocs_configured = False

    with patch("backend.core.logging.settings") as mock_settings:
        mock_settings.app_env = "development"
        mock_settings.log_level = "DEBUG"
        configure_logging()

    handler = logging.getLogger().handlers[0]
    record = logging.LogRecord(
        name="test", level=logging.DEBUG, pathname="", lineno=1,
        msg="debug msg", args=(), exc_info=None
    )
    output = handler.formatter.format(record)
    # Should NOT be JSON
    assert output.startswith("{") is False
    assert "debug msg" in output

    logging.getLogger()._insightdocs_configured = False
