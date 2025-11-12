# CRITICAL BUGFIXES FOR main.py

## 1. Genesis1 Infinite Loop Fix (line 313-329)

**Problem**: If `used` set is full (86400 seconds), the while loop can run forever.

**Fix**:
```python
async def genesis1_daily_task():
    """Run Genesis-1 once per day at a random non-repeating time."""
    used: set[int] = set()
    if GENESIS1_SCHEDULE_FILE.exists():
        try:
            used = set(json.loads(GENESIS1_SCHEDULE_FILE.read_text()))
        except Exception:
            used = set()
    while True:
        # FIX: Clear used set BEFORE checking to avoid edge case
        if len(used) >= 86400:
            used.clear()

        # FIX: Add safety check to prevent infinite loop
        attempts = 0
        max_attempts = 100
        sec = random.randint(0, 86399)
        while sec in used and attempts < max_attempts:
            sec = random.randint(0, 86399)
            attempts += 1

        if attempts >= max_attempts:
            # If we can't find unused slot, clear and restart
            used.clear()
            sec = random.randint(0, 86399)

        used.add(sec)
        # ... rest of code
```

## 2. Assistant API Timeout Fix (line 558-570)

**Problem**: The polling loop can run forever if status never becomes "completed".

**Fix**:
```python
# Poll for completion with timeout
max_iterations = 120  # 2 minutes max
iterations = 0
while True:
    run_status = await client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    if run_status.status == "completed":
        break
    elif run_status.status in ["failed", "cancelled", "expired"]:
        logger.error(
            "Run failed with status: %s", run_status.status
        )
        return "I encountered an error while processing your request."
    iterations += 1
    if iterations >= max_iterations:
        logger.error("Assistant API timeout after %d seconds", max_iterations)
        return "Request timed out. Please try again."
    await asyncio.sleep(1)
```

## 3. Voice File Size Check (line 1226-1229)

**Problem**: No size check before loading audio into memory.

**Fix**:
```python
MAX_VOICE_SIZE = 10 * 1024 * 1024  # 10MB

if await VOICE_USERS.get(user_id) and client:
    try:
        audio_bytes = await text_to_voice(client, reply)
        if len(audio_bytes) > MAX_VOICE_SIZE:
            logger.warning("Voice file too large: %d bytes", len(audio_bytes))
        else:
            voice_file = types.BufferedInputFile(audio_bytes, filename="reply.ogg")
            await m.answer_voice(voice_file)
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
```

## 4. Rawthinking Fallback (line 1036-1150)

**Problem**: If all 4 agents fail, synthesize_final gets all None values.

**Fix**:
```python
# After collecting all responses
if not any([b_resp, c_resp, d_resp, g_resp]):
    # All agents failed - use fallback
    fallback = "All perspectives temporarily unavailable. Core reasoning engaged."
    reply = await process_with_assistant(text, system_ctx, lang, profile)
    await send_split_message(bot, chat_id=chat_id, text=reply, delay=MESSAGE_DELAY)
    return

# Continue with synthesis
final = await synthesize_final(text, b_resp, c_resp, d_resp, g_resp, lang)
```

## 5. Genesis3 Timeout (line 1203-1211)

**Problem**: No timeout on genesis3_deep_dive call.

**Fix**:
```python
if (complexity == 3 or FORCE_DEEP_DIVE) and settings.PPLX_API_KEY:
    try:
        logger.info("Attempting Genesis3 deep dive for main response")
        # Add timeout wrapper
        deep_dive = await asyncio.wait_for(
            genesis3_deep_dive(draft, text),
            timeout=30.0
        )
        logger.info("Genesis3 completed successfully for main response")
    except asyncio.TimeoutError:
        logger.error("[Genesis-3] timeout after 30s")
        deep_dive = ""
    except Exception as e:
        logger.error(f"[Genesis-3] fail {e}")
        if FORCE_DEEP_DIVE:
            deep_dive = "🔍 Глубокий анализ не удался из-за технической ошибки."
```

## 6. RepoWatcher Race Condition (line 252)

**Problem**: repo_watcher may have race conditions in _scan.

**Already has semaphore in FileHandler, but recommend:**
```python
# In repo_monitor.py, add lock for hash updates
import threading

class RepoWatcher:
    def __init__(self, ...):
        # ...
        self._hash_lock = threading.Lock()

    def _scan(self):
        # ... compute new_hashes ...
        with self._hash_lock:
            if new_hashes != self.file_hashes:
                self.file_hashes = new_hashes
                if self.on_change:
                    self.on_change()
```
