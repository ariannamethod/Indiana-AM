import asyncio
import logging
import os
import base64
import hashlib
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
from cryptography.fernet import Fernet

from .vectorstore import BaseVectorStore, create_vector_store

logger = logging.getLogger(__name__)

# how many records to keep per user
DEFAULT_MAX_RECORDS = 100


class MemoryManager:
    def __init__(
        self,
        db_path: str = "memory.db",
        vectorstore: Optional[BaseVectorStore] = None,
        max_records_per_user: int = DEFAULT_MAX_RECORDS,
        encryption_key: str | None = None,
        encryption_version: int = 1,
    ):
        self.db_path = db_path
        self.vectorstore = vectorstore or create_vector_store()
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
        self.max_records_per_user = max_records_per_user
        self.encryption_key = encryption_key or os.getenv("MEMORY_ENCRYPTION_KEY")
        self.encryption_version = encryption_version
        self._cipher = (
            Fernet(
                base64.urlsafe_b64encode(
                    hashlib.sha256(self.encryption_key.encode()).digest()
                )
            )
            if self.encryption_key
            else None
        )

    async def __aenter__(self):
        """Ensure the database connection is ready when entering context."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Close the database connection when leaving context."""
        await self.close()
        return False

    async def connect(self) -> aiosqlite.Connection:
        """Create a single shared connection if it doesn't exist."""
        if self._db is None:
            async with self._lock:
                if self._db is None:
                    self._db = await aiosqlite.connect(self.db_path)
                    await self._init_db(self._db)
        return self._db

    async def close(self) -> None:
        """Close the shared database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def _init_db(self, db: aiosqlite.Connection):
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                user_id TEXT,
                timestamp TEXT,
                query TEXT,
                response TEXT,
                encryption_version INTEGER DEFAULT 0
            )
            """
        )
        async with db.execute("PRAGMA table_info(memory)") as cur:
            cols = [row[1] async for row in cur]
        if "encryption_version" not in cols:
            await db.execute(
                "ALTER TABLE memory ADD COLUMN encryption_version INTEGER DEFAULT 0"
            )
        # composite index to speed up per-user queries
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_ts ON memory(user_id, timestamp)"
        )
        # index on timestamp for global cleanup or ordering
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_ts ON memory(timestamp)"
        )
        await db.commit()

    async def _prune_user_records(self, db: aiosqlite.Connection, user_id: str) -> None:
        """Remove old records keeping only the most recent N per user."""
        await db.execute(
            """
            DELETE FROM memory
            WHERE rowid IN (
                SELECT rowid FROM memory
                WHERE user_id=?
                ORDER BY timestamp DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (user_id, self.max_records_per_user),
        )

    async def save(self, user_id: str, query: str, response: str) -> bool:
        """Save user query and response to memory database and vector store."""
        ts = datetime.now(timezone.utc).isoformat()
        db = await self.connect()
        enc_q = self._cipher.encrypt(query.encode()).decode() if self._cipher else query
        enc_r = (
            self._cipher.encrypt(response.encode()).decode() if self._cipher else response
        )
        version = self.encryption_version if self._cipher else 0
        await db.execute(
            "INSERT INTO memory VALUES (?,?,?,?,?)",
            (user_id, ts, enc_q, enc_r, version),
        )
        await self._prune_user_records(db, user_id)
        await db.commit()
        status = True
        if self.vectorstore:
            async def _store_vector() -> bool:
                for attempt in range(2):
                    try:
                        await self.vectorstore.store(
                            f"{user_id}-{ts}",
                            f"Q: {query}\nA: {response}",
                            user_id=user_id,
                        )
                        return True
                    except Exception:
                        logger.exception("Vector store failed (attempt %d)", attempt + 1)
                        if attempt == 0:
                            await asyncio.sleep(1)
                return False

            async with asyncio.TaskGroup() as tg:
                task = tg.create_task(_store_vector())
            status = task.result()

        return status

    async def retrieve(self, user_id: str, query: str) -> str:
        """Retrieve last 5 responses for a given user as context."""
        db = await self.connect()
        async with db.execute(
            "SELECT response, encryption_version FROM memory INDEXED BY idx_user_ts WHERE user_id=? ORDER BY timestamp DESC LIMIT 5",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        if not rows:
            return ""
        # склеиваем последние 5 ответов как контекст
        decrypted = [
            (
                self._cipher.decrypt(r[0].encode()).decode()
                if r[1] and self._cipher
                else r[0]
            )
            for r in rows
        ]
        return "\n".join(decrypted)

    async def recent_messages(self, limit: int = 10) -> list[tuple[str, str]]:
        """Return recent query/response pairs across all users."""
        db = await self.connect()
        async with db.execute(
            "SELECT query, response, encryption_version FROM memory INDEXED BY idx_ts ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        result: list[tuple[str, str]] = []
        for q, r, v in rows:
            if v and self._cipher:
                q = self._cipher.decrypt(q.encode()).decode()
                r = self._cipher.decrypt(r.encode()).decode()
            result.append((q, r))
        return result

    async def search_memory(self, user_id: str, query: str, top_k: int = 5) -> list[str]:
        """Search vector memory for similar texts belonging to the given user."""
        if not self.vectorstore:
            return []
        try:
            return await self.vectorstore.search(query, top_k, user_id=user_id)
        except Exception as e:
            # log and fall back to empty list
            logger.error(f"Vector search failed: {e}")
            return []

    async def last_response(self, user_id: str) -> str:
        """Return the most recent response for the given user."""
        db = await self.connect()
        async with db.execute(
            "SELECT response, encryption_version FROM memory WHERE user_id=? ORDER BY timestamp DESC LIMIT 1",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return ""
        resp, ver = row
        if ver and self._cipher:
            return self._cipher.decrypt(resp.encode()).decode()
        return resp
