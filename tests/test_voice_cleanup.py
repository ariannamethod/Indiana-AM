import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


class DummyVoice:
    file_id = "voice123"


class DummyMessage:
    def __init__(self, voice):
        self.text = None
        self.voice = voice
        self.from_user = SimpleNamespace(id=1, language_code="en")
        self.chat = SimpleNamespace(id=1, type="private")
        self.answers = []

    async def answer(self, text: str):
        self.answers.append(text)


@pytest.mark.asyncio
async def test_voice_file_removed(monkeypatch, tmp_path):
    main.VOICE_DIR = tmp_path
    main.EMERGENCY_MODE = True
    main.client = object()

    async def fake_get_file(file_id):
        return SimpleNamespace(file_path="path", file_unique_id="abc")

    async def fake_download_file(file_path, destination):
        destination.write_text("voice")

    async def fake_voice_to_text(client, file_path):
        return "transcribed"

    async def fake_run(cmd):
        return "run"

    main.bot = SimpleNamespace(get_file=fake_get_file, download_file=fake_download_file)
    monkeypatch.setattr(main, "voice_to_text", fake_voice_to_text)
    monkeypatch.setattr(main.terminal, "run", fake_run)

    m = DummyMessage(DummyVoice())
    await main.handle_message(m)

    assert not (tmp_path / "abc.ogg").exists()
