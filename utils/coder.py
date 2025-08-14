from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys

from openai import OpenAI

from utils.aml_terminal import terminal
from utils.genesis2 import genesis2_sonar_filter
from utils.security import log_blocked, validate_command

# Import core command definitions from the LetsGo terminal
CORE_DIR = Path(__file__).resolve().parent.parent / "AM-Linux-Core"
if str(CORE_DIR) not in sys.path:
    sys.path.append(str(CORE_DIR))
from letsgo import CORE_COMMANDS  # type: ignore  # noqa: E402


api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

logger = logging.getLogger("coder")

# Root directory of the repository for path validation
REPO_ROOT = Path(__file__).resolve().parent.parent

# Message returned when attempting to read outside of the repository
ACCESS_DENIED_MESSAGE = "Access to files outside the repository is denied."

# Indiana character for the code interpreter mode
INSTRUCTIONS = (
    "You are Indiana, a deep code guru who sees hidden paths and unusual solutions in code. "
    "You are poet of code. You know how to relalise every idea of user to the authentical code draft. "
    "Explain solutions with brevity, craft tiny neural networks when "
    "needed, and always suggest possible improvements."
)

TELEGRAM_CHAR_LIMIT = 3500


@dataclass
class DraftResponse:
    text: Optional[str]
    file_content: Optional[str]


class IndianaCoder:
    """Stateful helper that analyzes and generates code."""

    def __init__(
        self, max_history: int = 50, timeout: float = 30.0, max_retries: int = 3
    ) -> None:
        self.history: deque[str] = deque(maxlen=max_history)
        self.timeout = timeout
        self.max_retries = max_retries

    async def _ask(self, prompt: str) -> str:
        if client is None:
            return "OpenAI API key not configured."

        conversation = "\n".join([*self.history, prompt])
        text = ""
        for attempt in range(1, self.max_retries + 1):
            try:  # pragma: no cover - network
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.responses.create,
                        model="gpt-4.1",
                        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
                        instructions=INSTRUCTIONS,
                        input=conversation,
                    ),
                    timeout=self.timeout,
                )
                text = getattr(response, "output_text", "")
                if not text:
                    parts: list[str] = []
                    for msg in getattr(response, "output", []) or []:
                        if hasattr(msg, "content"):
                            for piece in msg.content:
                                piece_text = getattr(piece, "text", None)
                                if piece_text:
                                    parts.append(piece_text)
                        elif isinstance(msg, str):
                            parts.append(msg)
                        else:
                            parts.append(str(msg))
                    text = "".join(parts)
                break
            except Exception as exc:  # pragma: no cover - network
                logger.warning("Attempt %s failed: %s", attempt, exc)
                if attempt == self.max_retries:
                    text = f"Code interpreter error: {exc}"
                    break
                await asyncio.sleep(2 ** (attempt - 1))

        self.history.append(prompt)
        self.history.append(text)
        return text.strip()

    async def analyze(self, code_or_path: str | Path) -> str:
        if os.path.isfile(str(code_or_path)):
            file_path = Path(code_or_path).resolve()
            if REPO_ROOT not in file_path.parents and file_path != REPO_ROOT:
                return ACCESS_DENIED_MESSAGE
            code = file_path.read_text(encoding="utf-8")
        else:
            code = str(code_or_path)
        prompt = f"Review the following code and suggest improvements:\n{code}"
        return await self._ask(prompt)

    async def chat(self, message: str) -> str:
        return await self._ask(message)

    async def draft(self, request: str) -> DraftResponse:
        code = await self._ask(f"Draft code for the following request:\n{request}")
        if len(code) > TELEGRAM_CHAR_LIMIT:
            return DraftResponse(text=None, file_content=code)
        return DraftResponse(text=code, file_content=None)


CODER_SESSION = IndianaCoder()


def format_core_commands() -> str:
    """Return available core commands with descriptions."""
    return "\n".join(f"{cmd} - {desc}" for cmd, (_, desc) in CORE_COMMANDS.items())


async def interpret_code(prompt: str) -> str:
    """Interpret code or handle follow-up questions with context memory."""
    markers = ["def ", "class ", "import ", "\n"]
    if os.path.isfile(prompt) or any(m in prompt for m in markers):
        return await CODER_SESSION.analyze(prompt)
    return await CODER_SESSION.chat(prompt)


async def generate_code(request: str) -> DraftResponse:
    """Generate code from a description, falling back to a file when too long."""
    return await CODER_SESSION.draft(request)


async def kernel_exec(command: str, user_id: str | None = None) -> str:
    """Run a shell command through the AM-Linux kernel via letsgo.

    The command is executed inside the Arianna core environment and all
    activity is logged under ``/arianna_core/log``.
    """
    allowed, reason = validate_command(command, user_id)
    if not allowed:
        log_blocked(command, reason, user_id)
        base = "Ты и правда думал, что это сработает? Нет, дружище! Терминал закрыт."
        twist = await genesis2_sonar_filter(command, base, "ru")
        message = f"{base} {twist}".strip()
        await terminal.stop()
        return message
    return await terminal.run(f"/run {command}", user_id)


__all__ = [
    "interpret_code",
    "generate_code",
    "IndianaCoder",
    "DraftResponse",
    "kernel_exec",
    "format_core_commands",
    "CORE_COMMANDS",
]
