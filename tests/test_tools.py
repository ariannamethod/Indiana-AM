import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.tools import split_message  # noqa: E402


def test_split_message_short_text():
    text = "hello"
    parts = split_message(text, max_length=10)
    assert parts == [text]
    assert len(parts) == 1


def test_split_message_long_paragraph():
    p1 = "A" * 30
    p2 = "B" * 30
    text = f"{p1}\n\n{p2}"
    parts = split_message(text, max_length=50)
    assert len(parts) == 2
    assert parts[0] == p1
    assert parts[1] == p2


def test_split_message_sentence_split():
    s1 = "A" * 20 + "."
    s2 = "B" * 20 + "."
    s3 = "C" * 20 + "."
    text = f"{s1} {s2} {s3}"
    parts = split_message(text, max_length=50)
    assert len(parts) == 2
    assert parts[0] == f"{s1}\n\n{s2}"
    assert parts[1] == s3
    assert len(parts[0]) <= 50
    assert len(parts[1]) <= 50


def test_split_message_word_split_overlong_sentence():
    text = " ".join(["word"] * 20)
    parts = split_message(text, max_length=40)
    assert len(parts) == 3
    assert all(len(p) <= 40 for p in parts)
    assert " ".join(parts) == text
    assert all(not p.startswith(" ") and not p.endswith(" ") for p in parts)


def test_split_message_long_code_block_preserved():
    code = "\n".join([f"print({i})" for i in range(50)])
    text = f"```python\n{code}\n```"
    parts = split_message(text, max_length=120, preserve_markdown=True)
    assert len(parts) > 1
    for part in parts:
        assert part.startswith("```")
        assert part.endswith("```")
    reconstructed = "\n".join(
        "\n".join(part.splitlines()[1:-1]) for part in parts
    )
    assert reconstructed.strip() == code.strip()


def test_split_message_long_code_block_not_preserved():
    code = "\n".join([f"print({i})" for i in range(50)])
    text = f"```python\n{code}\n```"
    parts = split_message(text, max_length=120, preserve_markdown=False)
    assert len(parts) > 1
    assert any(not p.startswith("```") or not p.endswith("```") for p in parts)
