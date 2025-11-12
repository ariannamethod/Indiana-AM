# DYNAMIC LINUX KERNEL PARAMETERS

## Concept

Link kernel behavior to cognitive metrics (entropy, perplexity, chaos pulse):
- **High entropy** → increase timeout, reduce rate limits
- **High perplexity** → allocate more CPU to genesis processing
- **High chaos pulse** → adaptive resource scaling

This makes the kernel **cognitively responsive**.

## Implementation

### 1. Create Kernel Metrics Bridge (`utils/kernel_bridge.py`)

```python
"""Bridge between cognitive metrics and kernel parameters."""

import os
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class KernelBridge:
    """Adapt kernel parameters based on cognitive metrics."""

    def __init__(self, base_cgroup: str = "/sys/fs/cgroup/arianna"):
        self.base_cgroup = Path(base_cgroup)
        self.baseline_cpu = 100000  # 100ms per 100ms period
        self.baseline_mem = 512 * 1024 * 1024  # 512 MB
        self.baseline_timeout = 10  # seconds

    def _write_cgroup(self, subsystem: str, value: str) -> bool:
        """Write value to cgroup file."""
        try:
            path = self.base_cgroup / subsystem
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
            return True
        except (OSError, PermissionError) as e:
            logger.warning("Cannot write to cgroup %s: %s", subsystem, e)
            return False

    def adapt_to_metrics(
        self,
        entropy: float,
        perplexity: float,
        chaos_pulse: float
    ) -> Dict[str, Any]:
        """Adjust kernel parameters based on cognitive metrics.

        Args:
            entropy: Markov entropy (0-10 typical range)
            perplexity: Model perplexity (1-100+ typical range)
            chaos_pulse: Chaos pulse value (0.0-1.0)

        Returns:
            Dict of applied changes
        """
        changes = {}

        # === CPU SCALING ===
        # Higher entropy → more CPU for processing complex patterns
        entropy_factor = min(2.0, 1.0 + (entropy / 10.0))
        new_cpu = int(self.baseline_cpu * entropy_factor)

        if self._write_cgroup("cpu.max", f"{new_cpu} 100000"):
            changes["cpu.max"] = f"{new_cpu} μs per 100ms"
            logger.info("CPU quota scaled by entropy: %.2f → %d μs", entropy, new_cpu)

        # === MEMORY SCALING ===
        # Higher perplexity → more memory for uncertain processing
        perplexity_factor = min(2.0, 1.0 + (perplexity / 50.0))
        new_mem = int(self.baseline_mem * perplexity_factor)

        if self._write_cgroup("memory.high", str(new_mem)):
            changes["memory.high"] = f"{new_mem // (1024**2)} MB"
            logger.info("Memory limit scaled by perplexity: %.2f → %d MB",
                       perplexity, new_mem // (1024**2))

        # === TIMEOUT ADAPTATION ===
        # Higher chaos pulse → longer timeouts (system is in flux)
        timeout_factor = 1.0 + chaos_pulse
        new_timeout = int(self.baseline_timeout * timeout_factor)
        # Store in environment for letsgo to read
        os.environ["LETSGO_COMMAND_TIMEOUT"] = str(new_timeout)
        changes["command_timeout"] = f"{new_timeout}s"
        logger.info("Command timeout scaled by chaos: %.2f → %ds",
                   chaos_pulse, new_timeout)

        # === RATE LIMIT ADAPTATION ===
        # High entropy/chaos → relax rate limits (system needs freedom)
        if entropy > 5.0 or chaos_pulse > 0.7:
            rate_factor = 0.5  # Halve rate limit when high entropy/chaos
        else:
            rate_factor = 1.0
        new_rate = self.baseline_timeout * rate_factor
        os.environ["RATE_LIMIT_SEC"] = str(new_rate)
        changes["rate_limit"] = f"{new_rate:.1f}s"

        return changes

    def reset_to_baseline(self) -> None:
        """Reset all parameters to baseline."""
        self._write_cgroup("cpu.max", f"{self.baseline_cpu} 100000")
        self._write_cgroup("memory.high", str(self.baseline_mem))
        os.environ["LETSGO_COMMAND_TIMEOUT"] = str(self.baseline_timeout)
        logger.info("Kernel parameters reset to baseline")


# Global instance
kernel_bridge = KernelBridge()
```

### 2. Integrate into main.py

Add after line 149 (LAST_MARKOV_ENTROPY):

```python
from utils.kernel_bridge import kernel_bridge

# Adapt kernel on startup
kernel_bridge.adapt_to_metrics(
    entropy=LAST_MARKOV_ENTROPY,
    perplexity=0.0,  # Will be updated later
    chaos_pulse=0.5
)
```

Update `reload_artifacts()` to adapt kernel when metrics change:

```python
def reload_artifacts() -> None:
    """Clear artefact cache when repository changes."""
    artifact_cache.clear()
    logger.info("Artifact cache cleared after repository change")

    # Update GENESIS metrics whenever repository content changes
    update_and_train()
    global LAST_MARKOV_ENTROPY
    LAST_MARKOV_ENTROPY = report_entropy()

    # === ADAPT KERNEL TO NEW METRICS ===
    try:
        # Get perplexity from GENESIS
        from GENESIS_orchestrator.entropy import model_perplexity
        sample_text = artifact_cache.get_all_text()[:1000]  # Sample
        perplexity = model_perplexity(sample_text) if sample_text else 1.0

        # Get chaos pulse
        from utils.context_neural_processor import chaos_pulse
        pulse = chaos_pulse.get()

        # Adapt kernel
        changes = kernel_bridge.adapt_to_metrics(
            entropy=LAST_MARKOV_ENTROPY,
            perplexity=perplexity,
            chaos_pulse=pulse
        )
        logger.info("Kernel adapted to new metrics: %s", changes)
    except Exception as e:
        logger.error("Failed to adapt kernel: %s", e)
```

### 3. Update letsgo.py to read dynamic timeout

In `letsgo.py`, line 79:

```python
@dataclass
class Settings:
    prompt: str = ">> "
    green: str = "\033[32m"
    red: str = "\033[31m"
    cyan: str = "\033[36m"
    reset: str = "\033[0m"
    max_log_files: int = 100
    command_timeout: int = int(os.getenv("LETSGO_COMMAND_TIMEOUT", "10"))  # DYNAMIC!
    use_color: bool = True
```

### 4. Add monitoring endpoint

In `main.py`, add command to check current kernel state:

```python
@dp.message(F.text == "/kernelstatus")
async def kernel_status(m: types.Message):
    """Show current kernel parameters influenced by cognitive metrics."""
    user_id = str(m.from_user.id)
    lang = await get_user_language(user_id, m.text or "", m.from_user.language_code)

    status_lines = [
        f"🧠 **Cognitive Kernel Status**",
        f"",
        f"📊 Metrics:",
        f"  • Entropy: {LAST_MARKOV_ENTROPY:.2f}",
        f"  • Chaos Pulse: {chaos_pulse.get():.2f}",
        f"",
        f"⚙️ Kernel Adaptations:",
        f"  • Command Timeout: {os.getenv('LETSGO_COMMAND_TIMEOUT', '10')}s",
        f"  • Rate Limit: {os.getenv('RATE_LIMIT_SEC', '1.0')}s",
    ]

    await m.answer("\n".join(status_lines))
```

## Benefits

1. **Self-Adapting System**: Kernel responds to cognitive load
2. **Resource Optimization**: CPU/memory scale with processing needs
3. **Chaos Resilience**: System relaxes constraints during high-flux periods
4. **Feedback Loop**: Metrics → Kernel → Performance → New Metrics

This creates a **living OS** that breathes with Indiana's cognitive state.
