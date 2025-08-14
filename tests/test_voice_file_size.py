import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.voice import voice_to_text, MAX_FILE_SIZE  # noqa: E402


@pytest.mark.asyncio
async def test_voice_file_too_large(tmp_path):
    bigfile = tmp_path / "big.ogg"
    bigfile.write_bytes(b"0" * (MAX_FILE_SIZE + 1))
    with pytest.raises(ValueError):
        await voice_to_text(object(), bigfile)
