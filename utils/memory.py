import aiosqlite
from datetime import datetime


class MemoryManager:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self.db: aiosqlite.Connection | None = None

    async def init(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self._init_db()

    async def _init_db(self):
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS memory (
                user_id TEXT,
                timestamp TEXT,
                query TEXT,
                response TEXT
            )
            """
        )
        await self.db.commit()

    async def save(self, user_id: str, query: str, response: str):
        ts = datetime.utcnow().isoformat()
        await self.db.execute(
            "INSERT INTO memory VALUES (?,?,?,?)",
            (user_id, ts, query, response),
        )
        await self.db.commit()

    async def retrieve(self, user_id: str, query: str) -> str:
        cur = await self.db.execute(
            "SELECT response FROM memory WHERE user_id=? ORDER BY timestamp DESC LIMIT 5",
            (user_id,),
        )
        rows = await cur.fetchall()
        await cur.close()
        if not rows:
            return ""
        return "\n".join(r[0] for r in rows)
