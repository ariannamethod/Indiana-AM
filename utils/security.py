import json
import logging
import os
import re
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

DEFAULT_ALLOWED_PATTERNS = [
    r"^echo\b",
    r"^ls\b",
    r"^cat\b",
    r"^pwd\b",
    r"^whoami\b",
    r"^date\b",
]

DEFAULT_SUSPICIOUS_PATTERNS = [
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

ALLOWED_PATTERNS = DEFAULT_ALLOWED_PATTERNS
SUSPICIOUS_PATTERNS = DEFAULT_SUSPICIOUS_PATTERNS


def _compile_patterns() -> None:
    """Compile regex patterns after any modification."""

    global ALLOWED_REGEXES, SUSPICIOUS_REGEXES
    ALLOWED_REGEXES = [re.compile(p, re.IGNORECASE) for p in ALLOWED_PATTERNS]
    SUSPICIOUS_REGEXES = [re.compile(p, re.IGNORECASE) for p in SUSPICIOUS_PATTERNS]


_compile_patterns()


def load_config(path: str | os.PathLike[str] | None) -> None:
    """Load security patterns from JSON config file."""

    if not path:
        return
    cfg_path = Path(path)
    if not cfg_path.is_file():
        return
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    allowed = data.get("allowed")
    suspicious = data.get("suspicious")
    if isinstance(allowed, list) and allowed:
        global ALLOWED_PATTERNS
        ALLOWED_PATTERNS = allowed
    if isinstance(suspicious, list) and suspicious:
        global SUSPICIOUS_PATTERNS
        SUSPICIOUS_PATTERNS = suspicious
    _compile_patterns()


# Load external configuration if provided
load_config(os.getenv("SECURITY_CONFIG_PATH"))


def is_blocked(command: str) -> bool:
    """Return True if command is not in the whitelist.

    Suspicious sequences are logged regardless of allow status.
    """

    if any(regex.search(command) for regex in SUSPICIOUS_REGEXES):
        logger.warning("Suspicious command sequence: %s", command)

    allowed = any(regex.search(command) for regex in ALLOWED_REGEXES)
    return not allowed


def log_blocked(command: str) -> None:
    """Log a blocked command attempt."""

    logger.error("Blocked command: %s", command)


__all__ = ["is_blocked", "log_blocked", "load_config"]
