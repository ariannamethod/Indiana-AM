import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import asyncio
import pytest

# Ensure project root is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


@pytest.mark.asyncio
async def test_background_task_exception_logged(monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr(main, "logger", mock_logger)
    monkeypatch.setattr(main.repo_watcher, "stop", MagicMock())
    monkeypatch.setattr(main.memory, "close", AsyncMock())
    monkeypatch.setattr(main.knowtheworld.memory, "close", AsyncMock())

    main.background_tasks.clear()
    main.task_group = asyncio.TaskGroup()
    await main.task_group.__aenter__()

    async def boom():
        raise ValueError("boom")

    task = main.task_group.create_task(boom())
    main.background_tasks.append(task)

    await asyncio.sleep(0)
    await main.on_shutdown(None)

    error_exc_infos = [call.kwargs.get("exc_info") for call in mock_logger.error.call_args_list]
    assert any(isinstance(e, ValueError) and str(e) == "boom" for e in error_exc_infos)


@pytest.mark.asyncio
async def test_cleanup_tasks_terminate(monkeypatch, tmp_path):
    """Background cleanup tasks should finish without errors when cancelled."""
    monkeypatch.setattr(main.repo_watcher, "stop", MagicMock())
    monkeypatch.setattr(main.memory, "close", AsyncMock())
    monkeypatch.setattr(main.knowtheworld.memory, "close", AsyncMock())
    monkeypatch.setattr(main, "VOICE_DIR", tmp_path)

    real_sleep = asyncio.sleep

    async def fast_sleep(*_, **__):
        await real_sleep(0)

    monkeypatch.setattr(main.asyncio, "sleep", fast_sleep)

    main.background_tasks.clear()
    main.task_group = asyncio.TaskGroup()
    await main.task_group.__aenter__()

    tasks = [
        main.task_group.create_task(main.cleanup_old_voice_files()),
        main.task_group.create_task(main.cleanup_user_langs()),
        main.task_group.create_task(main.cleanup_user_states()),
    ]
    main.background_tasks.extend(tasks)

    await asyncio.sleep(0)  # let tasks start

    await main.on_shutdown(None)

    for t in tasks:
        assert t.done()
        assert t.exception() is None
