import asyncio
from pathlib import Path
import sys

# Ensure project root is importable
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.keyboards import control_keyboard  # noqa: E402
import main  # noqa: E402


class DummyMessage:
    def __init__(self):
        self.text = None
        self.reply_markup = None

    async def edit_text(self, text, reply_markup=None):
        self.text = text
        self.reply_markup = reply_markup


class DummyCallback:
    def __init__(self, data, user_id="1"):
        self.data = data
        self.from_user = type("U", (), {"id": int(user_id)})()
        self.message = DummyMessage()

    async def answer(self, text=None, show_alert=False):
        self.answered = text


def test_control_keyboard_labels():
    kb = control_keyboard(voice_enabled=False, deep_enabled=True, coder_enabled=False)
    assert kb.inline_keyboard[0][0].text == "Voice On"
    assert kb.inline_keyboard[1][0].text == "Deep Off"
    assert kb.inline_keyboard[2][0].text == "Coder On"


def test_voice_callback_toggle():
    main.VOICE_USERS.clear()
    cb = DummyCallback("voice_toggle")
    asyncio.run(main.voice_toggle_cb(cb))
    assert asyncio.run(main.VOICE_USERS.get("1")) is not None
    assert cb.message.text == "☝🏻 voice mode enabled"
    assert cb.message.reply_markup.inline_keyboard[0][0].text == "Voice Off"


def test_deep_callback_toggle():
    main.FORCE_DEEP_DIVE = False
    cb = DummyCallback("deep_toggle")
    asyncio.run(main.deep_toggle_cb(cb))
    assert main.FORCE_DEEP_DIVE is True
    assert cb.message.text == "☝🏻 deep mode enabled"
    assert cb.message.reply_markup.inline_keyboard[1][0].text == "Deep Off"


def test_coder_callback_toggle():
    main.CODER_USERS.clear()
    cb = DummyCallback("coder_toggle")
    asyncio.run(main.coder_toggle_cb(cb))
    assert asyncio.run(main.CODER_USERS.get("1")) is not None
    assert cb.message.text == "☝🏻 coder mode enabled"
    assert cb.message.reply_markup.inline_keyboard[2][0].text == "Coder Off"
