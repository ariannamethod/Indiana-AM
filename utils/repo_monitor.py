import hashlib
import logging
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Iterable


logger = logging.getLogger(__name__)


class RepoWatcher:
    """Monitors repository paths and triggers a callback when files change.

    Files are identified by SHA-256 hashes so even unchanged sizes
    but modified contents will be detected.
    """

    def __init__(
        self,
        paths: Iterable[Path],
        on_change: Callable[[], None],
        exts: Iterable[str] | None = None,
        interval: int = 30,
    ) -> None:
        self.paths = [Path(p) for p in paths]
        self.on_change = on_change
        self.exts = {e.lower() for e in (exts or {'.md', '.txt', '.py', '.json'})}
        self.interval = interval
        self._file_sha: Dict[Path, str] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)

    def start(self) -> None:
        """Start background watching."""
        self._file_sha = self._scan()
        self._thread.start()

    def stop(self) -> None:
        """Stop background watching."""
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join()

    def check_now(self) -> None:
        """Trigger a synchronous scan and callback if needed."""
        current = self._scan()
        changed = [p for p, s in current.items() if self._file_sha.get(p) != s]
        if changed:
            self._file_sha = current
            try:
                self.on_change()
            except Exception:
                logger.error("Error in on_change callback", exc_info=True)

    def _scan(self) -> Dict[Path, str]:
        files: Dict[Path, str] = {}
        for base in self.paths:
            if not base.exists():
                continue
            for p in base.rglob('*'):
                if (
                    p.is_file()
                    and p.suffix.lower() in self.exts
                    and '.git' not in p.parts
                ):
                    try:
                        h = hashlib.sha256()
                        with p.open('rb') as f:
                            for chunk in iter(lambda: f.read(1 << 16), b''):
                                h.update(chunk)
                        files[p] = h.hexdigest()
                    except Exception:
                        logger.error("Failed hashing file %s", p, exc_info=True)
                        continue
        return files

    def _watch_loop(self) -> None:
        while not self._stop.is_set():
            time.sleep(self.interval)
            current = self._scan()
            changed = [p for p, s in current.items() if self._file_sha.get(p) != s]
            if changed:
                self._file_sha = current
                try:
                    self.on_change()
                except Exception:
                    logger.error("Error in on_change callback", exc_info=True)
