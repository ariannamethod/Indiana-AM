import logging
import re
import shlex
from collections.abc import Callable
from pathlib import Path

LOG_FILE = Path("artefacts/blocked_commands.log")

logger = logging.getLogger("security")

# Whitelist of allowed commands and their permitted arguments
# ``None`` means any arguments are allowed, an empty set means no arguments.
# A callable value is used for custom validation of arguments.
ALLOWED_PATHS = [Path("AM-Linux-Core")]


def is_safe_path(path: str, allowed_dirs: list[Path] | None = None) -> bool:
    """Return True if ``path`` is within one of ``allowed_dirs``."""

    allowed_dirs = allowed_dirs or ALLOWED_PATHS
    resolved = (Path.cwd() / path).resolve()

    for allowed in allowed_dirs:
        base = (Path.cwd() / allowed).resolve()
        if base == resolved or base in resolved.parents:
            return True
    return False


ALLOWED_COMMANDS: dict[str, set[str] | None | Callable[[str], bool]] = {
    "echo": None,
    "ls": {"-l", "-a", "-la", "-al"},
    "cat": is_safe_path,
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

    if callable(allowed_args):
        if not args:
            return False, f"no path provided for {cmd}"
        for arg in args:
            if not allowed_args(arg):
                return False, f"path {arg} not allowed for {cmd}"
        return True, None

    if allowed_args is None:
        return True, None

    if args and not all(arg in allowed_args for arg in args):
        return False, f"arguments {args} not allowed for {cmd}"

    return True, None


def log_blocked(command: str, reason: str) -> None:
    """Log a blocked command attempt with the reason."""

    logger.error("Blocked command: %s - %s", command, reason)
    for handler in logger.handlers:
        handler.flush()


def is_blocked(command: str) -> bool:
    """Return ``True`` if a command is disallowed and log the reason."""

    allowed, reason = validate_command(command)
    if not allowed:
        log_blocked(command, reason or "unknown reason")
    return not allowed


__all__ = ["validate_command", "log_blocked", "is_blocked", "is_safe_path"]
