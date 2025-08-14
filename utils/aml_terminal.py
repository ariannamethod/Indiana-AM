import asyncio
import logging
import os
import sys
from pathlib import Path

from utils.security import log_blocked, validate_command


class AriannaTerminal:
    """Minimal bridge to the AM-Linux letsgo terminal."""

    def __init__(self, prompt: str = ">>", data_dir: str = "/arianna_core") -> None:
        self.prompt = prompt
        self.data_dir = data_dir
        self.proc: asyncio.subprocess.Process | None = None
        self._lock = asyncio.Lock()
        self._cg_dir: Path | None = None
        self.restart_count = 0

    def _apply_cgroup_limits(self, pid: int) -> None:
        cpu_limit = os.getenv("LETSGO_CPU_LIMIT")
        mem_limit = os.getenv("LETSGO_MEMORY_LIMIT")
        if not cpu_limit and not mem_limit:
            return
        root = Path(os.getenv("LETSGO_CGROUP_ROOT", "/sys/fs/cgroup"))
        cg_dir = root / f"arianna_terminal_{pid}"
        self._cg_dir = cg_dir
        try:
            cg_dir.mkdir(parents=True, exist_ok=True)
            if mem_limit:
                (cg_dir / "memory.max").write_text(mem_limit)
            if cpu_limit:
                (cg_dir / "cpu.max").write_text(cpu_limit)
            (cg_dir / "cgroup.procs").write_text(str(pid))
        except OSError:
            # If cgroups are unavailable or permissions are missing, ignore the error.
            pass

    async def _ensure_started(self) -> None:
        if self.proc:
            return
        env = os.environ.copy()
        env.setdefault("LETSGO_DATA_DIR", self.data_dir)
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "AM-Linux-Core" / "letsgo.py"),
            "--no-color",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            env=env,
        )
        if self.proc.pid:
            self._apply_cgroup_limits(self.proc.pid)
        await self._read_until_prompt()

    async def _read_until_prompt(self) -> None:
        if not self.proc or not self.proc.stdout:
            return
        prompt_bytes = (self.prompt + " ").encode()
        buf = b""
        while not buf.endswith(prompt_bytes):
            chunk = await self.proc.stdout.read(1)
            if not chunk:
                break
            buf += chunk

    def is_running(self) -> bool:
        return bool(self.proc) and self.proc.returncode is None

    async def run(self, cmd: str, user_id: str | None = None) -> str:
        real_cmd = cmd[5:] if cmd.startswith("/run ") else cmd
        allowed, reason = validate_command(real_cmd, user_id)
        if not allowed:
            log_blocked(real_cmd, reason, user_id)
            return "Терминал закрыт"
        if not self.is_running():
            if self.proc and self.proc.returncode is not None:
                logging.info(
                    "AriannaTerminal process exited with code %s, restarting",
                    self.proc.returncode,
                )
                self.restart_count += 1
                if self._cg_dir:
                    try:
                        self._cg_dir.rmdir()
                    except OSError:
                        pass
                    self._cg_dir = None
            self.proc = None
        await self._ensure_started()
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("process not started")
        async with self._lock:
            self.proc.stdin.write((cmd + "\n").encode())
            await self.proc.stdin.drain()
            prompt_bytes = (self.prompt + " ").encode()
            buf = b""
            while not buf.endswith(prompt_bytes):
                chunk = await self.proc.stdout.read(1)
                if not chunk:
                    break
                buf += chunk
            text = buf.decode()
            if text.endswith(self.prompt + " "):
                text = text[: -len(self.prompt) - 1]
            if text.startswith(self.prompt + " "):
                text = text[len(self.prompt) + 1:]
            return text.strip()

    async def stop(self) -> None:
        if self.proc:
            if self.proc.stdin:
                self.proc.stdin.close()
            try:
                self.proc.terminate()
            except ProcessLookupError:
                pass
            try:
                await self.proc.wait()
            except ProcessLookupError:
                pass
            self.proc = None
        if self._cg_dir:
            try:
                self._cg_dir.rmdir()
            except OSError:
                pass
            self._cg_dir = None
        if self.restart_count:
            logging.info("AriannaTerminal restarted %d times", self.restart_count)


terminal = AriannaTerminal()

__all__ = ["terminal", "AriannaTerminal"]
