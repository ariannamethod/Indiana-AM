import logging
import re
import shlex
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_FILE = Path("artefacts/blocked_commands.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("security")
if not logger.handlers:
    handler = TimedRotatingFileHandler(
        LOG_FILE, when="midnight", backupCount=7, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Whitelist of allowed commands and their permitted arguments
# ``None`` means any arguments are allowed, an empty set means no arguments.
ALLOWED_COMMANDS: dict[str, set[str] | None] = {
    "echo": None,
    "ls": {"-l", "-a", "-la", "-al"},
    "cat": None,
    "pwd": set(),
    "whoami": set(),
    "date": set(),
}

# Suspicious sequences to warn about
SUSPICIOUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"sudo\s",
    r":\(\)\s*{\s*:\|:&\s*};\s*:",
    r"curl\s",
    r"wget\s",
    r"ssh\s",
    r"scp\s",
    r"nc\s",
    r"netcat\s",
    r"telnet\s",
    r"ping\s",
    r"apt(-get)?\s",
    r"pip\s+install",
    r"python\s+-m\s+http\.server",
    r">/dev/tcp",
    r"xmrig",
    r"minerd",
]
SUSPICIOUS_REGEXES = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]


def validate_command(command: str) -> tuple[bool, str | None]:
    """Validate a shell command against a whitelist.

    Returns a tuple ``(allowed, reason)`` where ``allowed`` indicates whether the
    command is permitted. ``reason`` contains the block reason when ``allowed`` is
    ``False``.
    """

    if any(regex.search(command) for regex in SUSPICIOUS_REGEXES):
        logger.warning("Suspicious command sequence: %s", command)

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return False, f"parse error: {exc}"

    if not parts:
        return False, "empty command"

    cmd, *args = parts
    if cmd not in ALLOWED_COMMANDS:
        return False, f"command {cmd} not allowed"

    allowed_args = ALLOWED_COMMANDS[cmd]
    if allowed_args is None:
        return True, None

    if args and not all(arg in allowed_args for arg in args):
        return False, f"arguments {args} not allowed for {cmd}"

    return True, None


def log_blocked(command: str, reason: str) -> None:
    """Log a blocked command attempt with the reason."""

    logger.error("Blocked command: %s - %s", command, reason)


__all__ = ["validate_command", "log_blocked"]
