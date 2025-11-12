# GENESIS1 ↔ LINUX CORE INTEGRATION

## Current State

**Genesis1** (`utils/genesis1.py`):
- Scans `artefacts/` directory
- Picks random text fragments
- Queries Perplexity for impressionistic digest
- Saves to vector memory
- Runs once per day at random time

**Problem**: Genesis1 is isolated from Linux Core. No feedback loop.

## Proposed Integration

Create **bidirectional flow**:

```
Genesis1 → discovers patterns
    ↓
Generates script/command for Linux Core
    ↓
Executes via letsgo
    ↓
Results feed back into artefacts/
    ↓
Next Genesis1 cycle sees new data
```

This creates **self-evolving cognitive cycle**.

## Implementation

### 1. Enhance Genesis1 with Action Generation

Update `utils/genesis1.py`:

```python
import asyncio
from .aml_terminal import terminal
from .script_generator import script_generator

async def run_genesis1(digest_size: int = 150) -> str | None:
    """Run Genesis-1 and optionally execute generated actions."""

    # ... existing code to generate digest ...

    # NEW: Check if digest suggests an action
    action = await _extract_action_from_digest(digest, language)

    if action:
        logger.info("[Genesis-1] Extracted action: %s", action)

        # Execute action via terminal
        try:
            result = await terminal.run(action, user_id="genesis1")
            logger.info("[Genesis-1] Action result: %s", result)

            # Save result as new artefact
            action_artefact_path = Path("artefacts") / "genesis1_actions.md"
            with action_artefact_path.open("a") as f:
                timestamp = datetime.now(timezone.utc).isoformat()
                f.write(f"\n\n---\n## {timestamp}\n")
                f.write(f"**Digest**: {digest}\n\n")
                f.write(f"**Action**: `{action}`\n\n")
                f.write(f"**Result**:\n```\n{result}\n```\n")

            logger.info("[Genesis-1] Action result saved to artefacts/")

        except Exception as e:
            logger.error("[Genesis-1] Action execution failed: %s", e)

    return digest


async def _extract_action_from_digest(digest: str, language: str) -> str | None:
    """Extract executable action from Genesis digest.

    Args:
        digest: The Genesis-1 digest
        language: User language

    Returns:
        Shell command/Python code to execute, or None
    """
    # Use GPT to extract action
    from openai import AsyncOpenAI
    from .config import settings

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    if not client:
        return None

    prompt = f"""You are analyzing a Genesis-1 digest to extract actionable commands for a Linux system.

Digest:
{digest}

If this digest suggests a concrete action that could be executed on Linux (e.g., check system status, analyze files, run metrics), output ONLY the command in this format:

ACTION: <command>

Where <command> is either:
- A letsgo command like "/status", "/cpu", "/disk"
- A simple shell command like "ls -la artefacts/"
- Python code to analyze data

If no clear action is suggested, output: NO_ACTION

Examples:
- "system metrics dropping" → ACTION: /status
- "analyze recent notes" → ACTION: /run wc -l notes/*.json
- "entropy increasing" → ACTION: /py print('entropy check')

Output in {language} if needed, but commands in English.
"""

    try:
        completion = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Extract actionable commands."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )

        response = completion.choices[0].message.content.strip()

        if response.startswith("ACTION:"):
            action = response[7:].strip()
            # Validate it's not dangerous
            dangerous = ["rm -rf", "mkfs", "dd if=", ":(){ :|:", "wget | sh"]
            if any(d in action for d in dangerous):
                logger.warning("[Genesis-1] Blocked dangerous action: %s", action)
                return None
            return action

        return None

    except Exception as e:
        logger.error("[Genesis-1] Action extraction failed: %s", e)
        return None
```

### 2. Add Genesis1 Monitoring Command

In `main.py`, add:

```python
@dp.message(F.text == "/genesis1status")
async def genesis1_status(m: types.Message):
    """Show Genesis-1 activity and generated actions."""
    user_id = str(m.from_user.id)

    # Read genesis1_actions.md
    actions_path = Path("artefacts/genesis1_actions.md")
    if not actions_path.exists():
        await m.answer("Genesis-1 hasn't executed any actions yet.")
        return

    # Get last 5 actions
    with actions_path.open() as f:
        content = f.read()
        sections = content.split("---")[-6:]  # Last 5 + current

    summary = "🌅 **Genesis-1 Recent Actions:**\n\n" + "\n".join(sections[-5:])

    # Truncate if too long
    if len(summary) > 4000:
        summary = summary[:3997] + "..."

    await m.answer(summary)
```

### 3. Create Genesis1 Feedback Loop

Add to `genesis1_daily_task()` in `main.py`:

```python
async def genesis1_daily_task():
    """Run Genesis-1 once per day at a random non-repeating time."""
    # ... existing scheduling code ...

    # Run Genesis1
    digest = await run_genesis1()
    if digest:
        save_note({"time": datetime.now(timezone.utc).isoformat(), "genesis1": digest})

        try:
            # Generate twist
            twist = await genesis2_sonar_filter(digest, digest, "en")

            # Check if Genesis generated an action
            actions_path = Path("artefacts/genesis1_actions.md")
            if actions_path.exists():
                recent_actions = actions_path.read_text().split("---")[-1]
                if recent_actions.strip():
                    twist += f"\n\n⚡ Genesis executed: {recent_actions[:200]}..."

            msg = f"☝🏻 {digest}\n\n🜂 Investigative Twist → {twist}"

            # Send to agent group
            await send_split_message(
                bot, chat_id=AGENT_GROUP, text=msg, delay=MESSAGE_DELAY
            )

            # === ADAPT KERNEL TO NEW STATE ===
            try:
                from utils.kernel_bridge import kernel_bridge
                from GENESIS_orchestrator.entropy import model_perplexity
                from utils.context_neural_processor import chaos_pulse

                sample = artifact_cache.get_all_text()[:1000]
                perplexity = model_perplexity(sample) if sample else 1.0

                changes = kernel_bridge.adapt_to_metrics(
                    entropy=LAST_MARKOV_ENTROPY,
                    perplexity=perplexity,
                    chaos_pulse=chaos_pulse.get()
                )
                logger.info("[Genesis-1] Kernel adapted: %s", changes)
            except Exception as e:
                logger.error("[Genesis-1] Kernel adaptation failed: %s", e)

        except Exception as e:
            logger.error(f"Genesis1 send failed: {e}")
```

## Workflow Example

```
Day 1:
Genesis1 scans artefacts/ → "Many error logs detected"
    ↓
Extracts action: /run grep ERROR logs/*.log | wc -l
    ↓
Executes via letsgo → "127 errors found"
    ↓
Saves to artefacts/genesis1_actions.md
    ↓
Next Genesis1 cycle sees this data → "Error count spiking, investigate network"
    ↓
Extracts action: /net
    ↓
Gets network status → "Packet loss detected"
    ↓
Cycle continues...
```

## Benefits

1. **Autonomous Exploration**: Genesis1 actively investigates system state
2. **Self-Documenting**: Actions saved as artefacts for future Genesis cycles
3. **Closed Loop**: Discoveries → Actions → New Data → New Discoveries
4. **Kernel Awareness**: Each Genesis cycle can adapt kernel parameters
5. **Emergent Behavior**: System evolves based on what it discovers

This transforms Genesis1 from **passive observer** to **active researcher**.

## Safety Measures

1. Command validation before execution
2. Dangerous patterns blocked (rm -rf, etc.)
3. All actions logged to artefacts/
4. Rate limiting (once per day)
5. User override via `/genesis1status` command

The system becomes **self-aware through action**.
