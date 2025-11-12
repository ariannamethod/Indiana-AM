# AUTOGENERATE SCRIPTS MECHANISM FOR INDIANA

## Concept

Instead of manually creating utilities, Indiana should be able to:
1. Recognize when a task needs a custom script
2. Generate Python/Bash code using Assistant API
3. Execute it on the kernel via letsgo
4. Store successful scripts for reuse

This makes Indiana **self-extending**.

## Architecture

```
User Query
    ↓
Indiana recognizes: "This needs a script"
    ↓
Assistant API generates code (with validation)
    ↓
Save to /arianna_core/scripts/
    ↓
Execute via letsgo: /py <script> or /run <script>
    ↓
Store result in memory
```

## Implementation

### 1. Create Script Generator (`utils/script_generator.py`)

```python
"""Generate and execute dynamic scripts for Indiana."""

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Tuple, Optional

from openai import AsyncOpenAI
from .config import settings
from .security import validate_command

logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path("/arianna_core/scripts")
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


class ScriptGenerator:
    """Generate and manage dynamic scripts for Indiana."""

    def __init__(self):
        self.generated_scripts: dict[str, Path] = {}

    async def generate_script(
        self,
        task_description: str,
        language: str = "python",
        context: str = ""
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate a script for a specific task.

        Args:
            task_description: What the script should do
            language: "python" or "bash"
            context: Additional context for generation

        Returns:
            (script_code, script_path) or (None, error_message)
        """
        if not client:
            return None, "OpenAI client not available"

        # Construct generation prompt
        system_prompt = f"""You are a code generator for Indiana, an AI system with its own Linux kernel.

Generate a {language} script that accomplishes the following task:
{task_description}

Requirements:
- Output ONLY the script code, no explanations
- For Python: use #!/usr/bin/env python3 shebang
- For Bash: use #!/bin/bash shebang
- Include error handling
- Keep it under 100 lines
- No network calls unless explicitly requested
- No file modifications outside /arianna_core/

Context: {context}
"""

        try:
            completion = await client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate the {language} script."}
                ],
                temperature=0.3,
                max_tokens=2000
            )

            script_code = completion.choices[0].message.content.strip()

            # Extract code from markdown if present
            if "```" in script_code:
                match = re.search(r"```(?:python|bash)?\n(.*?)\n```", script_code, re.DOTALL)
                if match:
                    script_code = match.group(1)

            # Validate script doesn't contain dangerous patterns
            dangerous_patterns = [
                r"rm\s+-rf\s+/",  # Dangerous rm
                r"mkfs\.",  # Format filesystem
                r"dd\s+if=",  # Direct disk write
                r":\(\)\s*\{.*:\|:",  # Fork bomb
                r"wget.*\|.*sh",  # Download and execute
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, script_code):
                    logger.warning("Generated script contains dangerous pattern: %s", pattern)
                    return None, "Generated script failed safety check"

            # Generate unique filename
            task_hash = hashlib.md5(task_description.encode()).hexdigest()[:8]
            ext = "py" if language == "python" else "sh"
            script_name = f"gen_{task_hash}.{ext}"
            script_path = SCRIPTS_DIR / script_name

            # Save script
            script_path.write_text(script_code)
            script_path.chmod(0o755)  # Make executable

            self.generated_scripts[task_hash] = script_path
            logger.info("Generated script: %s", script_path)

            return script_code, str(script_path)

        except Exception as e:
            logger.error("Script generation failed: %s", e)
            return None, str(e)

    async def execute_script(
        self,
        script_path: str,
        args: str = "",
        user_id: Optional[str] = None
    ) -> Tuple[str, int]:
        """Execute a generated script via letsgo.

        Args:
            script_path: Path to script
            args: Arguments to pass
            user_id: User ID for security check

        Returns:
            (output, return_code)
        """
        from .aml_terminal import terminal

        # Validate command
        cmd = f"{script_path} {args}".strip()
        allowed, reason = validate_command(cmd, user_id)
        if not allowed:
            return f"Execution blocked: {reason}", 1

        # Execute via terminal
        try:
            if script_path.endswith(".py"):
                result = await terminal.run(f"/py $(cat {script_path})", user_id=user_id)
            else:
                result = await terminal.run(f"/run bash {script_path} {args}", user_id=user_id)

            return result, 0
        except Exception as e:
            logger.error("Script execution failed: %s", e)
            return str(e), 1

    def list_scripts(self) -> list[str]:
        """List all generated scripts."""
        return [str(p) for p in SCRIPTS_DIR.glob("gen_*.py")] + \
               [str(p) for p in SCRIPTS_DIR.glob("gen_*.sh")]


# Global instance
script_generator = ScriptGenerator()
```

### 2. Integrate into main.py

Add new command `/generate`:

```python
@dp.message(F.text.startswith("/generate"))
async def handle_generate(m: types.Message):
    """Generate and execute a custom script for a task."""
    user_id = str(m.from_user.id)
    chat_id = m.chat.id

    # Parse task description
    task = m.text[10:].strip() if m.text else ""
    if not task:
        await m.answer("Usage: /generate <task description>")
        return

    lang = await get_user_language(user_id, task, m.from_user.language_code)
    profile = await genesis6_report(user_id, task, lang)

    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        # Determine language (default: python)
        language = "bash" if "bash" in task.lower() or "shell" in task.lower() else "python"

        # Get context from artifacts
        context = artifact_cache.get_all_text()[:500]

        # Generate script
        from utils.script_generator import script_generator
        script_code, script_path_or_error = await script_generator.generate_script(
            task_description=task,
            language=language,
            context=context
        )

        if not script_code:
            await m.answer(f"❌ Generation failed: {script_path_or_error}")
            return

        # Show generated script
        preview = script_code[:500] + ("..." if len(script_code) > 500 else "")
        await m.answer(
            f"✅ Generated {language} script:\n\n```{language}\n{preview}\n```\n\n"
            f"Saved to: `{script_path_or_error}`"
        )

        # Execute script
        output, rc = await script_generator.execute_script(script_path_or_error, user_id=user_id)

        result_text = f"📊 Execution result (rc={rc}):\n```\n{output[:1000]}\n```"
        await m.answer(result_text)

        # Save to memory
        await memory.save(user_id, f"generate: {task}", f"Script: {script_path_or_error}\nOutput: {output}")
```

Add command to list scripts:

```python
@dp.message(F.text == "/scripts")
async def list_scripts(m: types.Message):
    """List all generated scripts."""
    from utils.script_generator import script_generator

    scripts = script_generator.list_scripts()
    if not scripts:
        await m.answer("No generated scripts yet.")
        return

    scripts_list = "\n".join(f"• `{s}`" for s in scripts)
    await m.answer(f"📁 Generated scripts:\n\n{scripts_list}")
```

### 3. Add to bot commands

In `setup_bot_commands()`:

```python
commands = [
    # ... existing commands ...
    types.BotCommand(command="generate", description="generate script for task"),
    types.BotCommand(command="scripts", description="list generated scripts"),
]
```

## Usage Examples

```
User: /generate Count lines in all Python files in artefacts/

Indiana:
✅ Generated python script:

#!/usr/bin/env python3
import os
from pathlib import Path

total = 0
for p in Path('artefacts').rglob('*.py'):
    with open(p) as f:
        total += len(f.readlines())

print(f"Total lines: {total}")

Saved to: `/arianna_core/scripts/gen_a3f2c1b8.py`

📊 Execution result (rc=0):
Total lines: 1234
```

```
User: /generate bash script to check disk usage of logs/

Indiana:
✅ Generated bash script:

#!/bin/bash
du -sh logs/
find logs/ -type f | wc -l

Saved to: `/arianna_core/scripts/gen_9b2e4f1a.sh`

📊 Execution result (rc=0):
512M    logs/
127
```

## Benefits

1. **Self-Extending**: Indiana creates tools as needed
2. **Reusable**: Scripts saved for future use
3. **Safe**: Validation prevents dangerous operations
4. **Auditable**: All scripts stored and logged
5. **Integrated**: Uses existing letsgo infrastructure

This transforms Indiana from **tool user** to **tool creator**.
