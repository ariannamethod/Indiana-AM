import asyncio
from pathlib import Path
import sys
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

import utils.context_neural_processor as cnp  # noqa: E402
from utils.context_neural_processor import FileHandler, parse_and_store_file  # noqa: E402


@pytest.mark.asyncio
async def test_parse_and_store_text(tmp_path):
    file = tmp_path / "example.txt"
    file.write_text("Hello Indiana")
    result = await parse_and_store_file(str(file))
    assert "Tags:" in result
    assert "Summary:" in result


@pytest.mark.asyncio
async def test_truncates_large_text(tmp_path, monkeypatch):
    file = tmp_path / "big.txt"
    file.write_text("a" * 15)
    handler = FileHandler(max_text_size=10)

    read_sizes = []
    orig_open = open

    def mock_open(*args, **kwargs):
        f = orig_open(*args, **kwargs)
        if args[0] == str(file):
            original_read = f.read

            def read(size=-1, *a, **k):
                read_sizes.append(size)
                return original_read(size, *a, **k)

            f.read = read
        return f

    monkeypatch.setattr(cnp, "open", mock_open, raising=False)
    text = await handler.extract_async(str(file))
    assert text == "a" * 10 + "\n[Truncated]"
    assert handler.max_text_size + 1 in read_sizes
