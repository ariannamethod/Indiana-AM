import asyncio
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI

from .vectorstore import create_vector_store
from .config import settings

vector_store = create_vector_store(max_size=1000)
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())

async def _fetch_last_day():
    """Return the date string of the last daily log if present."""
    try:
        if hasattr(vector_store, "index"):
            result = vector_store.index.fetch(ids=["last-daily"])
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            if isinstance(result, dict):
                data = result.get("vectors", {}).get("last-daily")
            else:
                vectors = getattr(result, "vectors", None)
                data = vectors.get("last-daily") if isinstance(vectors, dict) else None
            if data:
                metadata = data.get("metadata") if isinstance(data, dict) else getattr(data, "metadata", {})
                if isinstance(metadata, dict):
                    return metadata.get("date")
        elif hasattr(vector_store, "_store"):
            entry = vector_store._store.get("last-daily")
            if entry and len(entry) >= 4 and entry[3]:
                return entry[3].get("date")
    except Exception as exc:
        logger.warning("Failed to fetch last daily log: %s", exc)
        return None
    return None

async def _store_last_day(date: str, text: str):
    try:
        metadata = {"date": date}
        await vector_store.store(f"daily-{date}", text, user_id="daily", metadata=metadata)
        await vector_store.store("last-daily", text, user_id="daily", metadata=metadata)
    except Exception as exc:
        logger.warning("Failed to store daily log: %s", exc)

async def default_reflection() -> str:
    """Generate a short daily reflection via OpenAI."""
    prompt = (
        "Summarise today's experiences in a couple of sentences and add your own "
        "thoughts about the day. Mention no personal user data."
    )
    if client:
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()
    return "Today was uneventful, but the lighthouse kept shining."

async def ensure_daily_entry(reflection_fn=default_reflection):
    """Create a daily log entry in Pinecone if one hasn't been stored today."""
    today = datetime.now(timezone.utc).date().isoformat()
    last = await _fetch_last_day()
    if last != today:
        text = await reflection_fn()
        await _store_last_day(today, text)
        return text
    return None

async def init_vector_memory():
    """Check and report the date of the last stored daily entry.

    Logs a message at the INFO level reporting the date of the most recent
    daily log in the vector store or indicating that none was found.
    """
    last = await _fetch_last_day()
    if last:
        logger.info("Last daily log stored on %s", last)
    else:
        logger.info("No daily log found in vector memory")

async def start_daily_task():
    """Background task that ensures a daily entry every 24 hours."""
    try:
        while True:
            try:
                await ensure_daily_entry()
            except Exception as exc:
                logger.warning("Daily entry failed: %s", exc)
            await asyncio.sleep(86400)
    except asyncio.CancelledError:
        logger.info("Daily task cancelled")
