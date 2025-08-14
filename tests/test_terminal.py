import asyncio
import logging
from pathlib import Path
import sys

# Ensure project root importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.coder import kernel_exec  # noqa: E402
from utils.aml_terminal import terminal  # noqa: E402
from utils.logging_config import LOG_FILE, setup_logging  # noqa: E402

setup_logging()


def test_kernel_exec(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("LETSGO_DATA_DIR", str(tmp_path))

    async def _run() -> str:
        output = await kernel_exec("echo hello")
        await terminal.stop()
        return output

    with caplog.at_level(logging.WARNING, logger="security"):
        result = asyncio.run(_run())
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "Терминал закрыт" not in result
    assert "echo hello" not in caplog.text


def test_kernel_exec_blocks_malicious_command(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("LETSGO_DATA_DIR", str(tmp_path))

    async def fake_run(cmd: str) -> str:
        raise AssertionError("run should not be called")

    monkeypatch.setattr(terminal, "run", fake_run)

    async def _run() -> str:
        return await kernel_exec("rm -rf /")

    with caplog.at_level(logging.ERROR, logger="security"):
        result = asyncio.run(_run())
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "Терминал закрыт" in result
    assert "rm -rf /" in caplog.text


def test_kernel_exec_logs_suspicious_sequences(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("LETSGO_DATA_DIR", str(tmp_path))

    async def fake_run(cmd: str) -> str:
        raise AssertionError("run should not be called")

    monkeypatch.setattr(terminal, "run", fake_run)

    async def _run() -> str:
        return await kernel_exec("curl http://example.com")

    with caplog.at_level(logging.WARNING, logger="security"):
        result = asyncio.run(_run())
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "Терминал закрыт" in result
    assert "curl http://example.com" in caplog.text
    assert "Suspicious" in caplog.text


def test_terminal_run_blocks_malicious_command(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv("LETSGO_DATA_DIR", str(tmp_path))

    async def _run() -> tuple[str, bool]:
        result = await terminal.run("rm -rf /")
        started = terminal.proc is not None
        await terminal.stop()
        return result, started

    with caplog.at_level(logging.ERROR, logger="security"):
        result, started = asyncio.run(_run())
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert "Терминал закрыт" in result
    assert not started
    assert "rm -rf /" in caplog.text


def test_cgroup_limits(monkeypatch, tmp_path):
    monkeypatch.setenv("LETSGO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LETSGO_CGROUP_ROOT", str(tmp_path))
    monkeypatch.setenv("LETSGO_CPU_LIMIT", "50000 100000")
    monkeypatch.setenv("LETSGO_MEMORY_LIMIT", "104857600")

    async def _run() -> int | None:
        await terminal._ensure_started()
        pid = terminal.proc.pid if terminal.proc else None
        await terminal.stop()
        return pid

    pid = asyncio.run(_run())
    assert pid is not None
    cg_dir = tmp_path / f"arianna_terminal_{pid}"
    assert (cg_dir / "cpu.max").read_text() == "50000 100000"
    assert (cg_dir / "memory.max").read_text() == "104857600"
    assert (cg_dir / "cgroup.procs").read_text() == str(pid)
