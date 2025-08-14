import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import logging  # noqa: E402
from logging.handlers import TimedRotatingFileHandler  # noqa: E402
import pytest  # noqa: E402

from utils import security  # noqa: E402


@pytest.fixture(autouse=True)
def temp_security_log(tmp_path, monkeypatch):
    """Redirect security logger to a temporary file for each test."""

    log_file = tmp_path / "blocked.log"
    monkeypatch.setattr(security, "LOG_FILE", log_file)

    # Reconfigure logger to use the temporary file
    logger = security.logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    yield log_file

    handler.close()
    logger.removeHandler(handler)


def test_allowed_command():
    """Whitelisted commands should not be blocked."""

    assert security.is_blocked("ls -la") is False


def test_blocked_command_and_logging(temp_security_log, caplog):
    """Disallowed commands are flagged and logged."""

    caplog.set_level(logging.WARNING, logger="security")
    assert security.is_blocked("rm -rf /", user_id="alice") is True
    assert any("Suspicious command sequence" in r.message for r in caplog.records)
    assert "alice" in caplog.text

    caplog.clear()
    caplog.set_level(logging.ERROR, logger="security")
    security.log_blocked("rm -rf /", "manual reason", user_id="bob")
    assert "Blocked command" in caplog.text
    assert "bob" in caplog.text

    # Ensure log file records the blocked command
    log_text = temp_security_log.read_text(encoding="utf-8")
    assert "Blocked command" in log_text
    assert "manual reason" in log_text
    assert "bob" in log_text


def test_cat_path_validation():
    safe_file = Path("AM-Linux-Core/README.md")
    unsafe_file = Path(__file__).resolve()
    assert security.is_blocked(f"cat {safe_file}") is False
    assert security.is_blocked(f"cat {unsafe_file}") is True
