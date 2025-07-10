import sqlite3
from datetime import datetime

class MemoryManager:
    def __init__(self, db_path="memory.db"):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                user_id TEXT,
                timestamp TEXT,
                query TEXT,
                response TEXT
            )
        """)
        self.db.commit()

    async def save(self, user_id: str, query: str, response: str):
        ts = datetime.utcnow().isoformat()
        self.db.execute(
            "INSERT INTO memory VALUES (?,?,?,?)",
            (user_id, ts, query, response)
        )
        self.db.commit()

    async def retrieve(self, user_id: str) -> str:
        cur = self.db.execute(
            "SELECT response FROM memory WHERE user_id=? ORDER BY timestamp DESC LIMIT 5",
            (user_id,)
        )
        rows = cur.fetchall()
        if not rows:
            return ""
        # склеиваем последние 5 ответов как контекст
        return "\n".join(r[0] for r in rows)

