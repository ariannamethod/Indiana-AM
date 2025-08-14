import asyncio
import sys
import time
import logging
from pathlib import Path
from types import SimpleNamespace

# Ensure project root is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.coder import (  # noqa: E402
    ACCESS_DENIED_MESSAGE,
    IndianaCoder,
    format_core_commands,
    CORE_COMMANDS,
)
from utils.logging_config import setup_logging  # noqa: E402

setup_logging()


def test_analyze_denies_outside_repo(tmp_path):
    outside_file = tmp_path / "code.py"
    outside_file.write_text("print('hi')", encoding="utf-8")

    coder = IndianaCoder()
    result = asyncio.run(coder.analyze(str(outside_file)))
    assert result == ACCESS_DENIED_MESSAGE


def test_analyze_allows_repo_file(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    inside_file = repo_root / "tmp_test_file.py"
    inside_file.write_text("print('hi')", encoding="utf-8")

    coder = IndianaCoder()

    async def fake_ask(self, prompt: str) -> str:  # pragma: no cover - simple stub
        return "OK"

    monkeypatch.setattr(IndianaCoder, "_ask", fake_ask)

    try:
        result = asyncio.run(coder.analyze(str(inside_file)))
        assert result == "OK"
    finally:
        inside_file.unlink()


def test_help_lists_core_commands():
    """Ensure /help returns entries from CORE_COMMANDS."""
    help_text = format_core_commands()
    assert any(cmd in help_text for cmd in CORE_COMMANDS)


def test_ask_retries_and_succeeds(monkeypatch):
    calls = {"n": 0}

    def create(**_: object) -> object:  # pragma: no cover - behavior mocked
        calls["n"] += 1
        if calls["n"] == 1:
            time.sleep(0.2)

        class Resp:
            output_text = "ok"
        return Resp()

    fake_client = SimpleNamespace(responses=SimpleNamespace(create=create))
    monkeypatch.setattr("utils.coder.client", fake_client, raising=False)

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    coder = IndianaCoder(timeout=0.01)
    result = asyncio.run(coder._ask("hi"))
    assert result == "ok"
    assert calls["n"] == 2


def test_ask_logs_failures(monkeypatch, caplog):
    def create(**_: object) -> None:  # pragma: no cover - behavior mocked
        time.sleep(0.2)

    fake_client = SimpleNamespace(responses=SimpleNamespace(create=create))
    monkeypatch.setattr("utils.coder.client", fake_client, raising=False)

    async def no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", no_sleep)

    coder = IndianaCoder(timeout=0.01)
    with caplog.at_level(logging.WARNING, logger="coder"):
        result = asyncio.run(coder._ask("hi"))
    assert "Code interpreter error" in result
    assert "Attempt" in caplog.text
