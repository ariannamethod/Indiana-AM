import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import gzip
import shutil

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "indiana.log"

def setup_logging() -> None:
    """Configure root logger with weekly rotating gzip-compressed file handler."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if logging.getLogger().handlers:
        return
    handler = TimedRotatingFileHandler(
        LOG_FILE, when="W0", backupCount=8, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    def namer(name: str) -> str:
        return f"{name}.gz"

    def rotator(source: str, dest: str) -> None:
        with open(source, "rb") as f_in, gzip.open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        Path(source).unlink(missing_ok=True)

    handler.namer = namer
    handler.rotator = rotator

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


setup_logging()
