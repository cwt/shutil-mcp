import json
from pathlib import Path

import pytest

from shutil_mcp.tools.search import glob, grep

pytestmark = pytest.mark.asyncio


async def test_glob_basic(tmp_path: Path) -> None:
    (tmp_path / "foo.py").write_text("x")
    (tmp_path / "bar.py").write_text("x")
    (tmp_path / "readme.md").write_text("x")

    result = await glob("*.py", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert len(data["matches"]) == 2
    assert "foo.py" in data["matches"]
    assert "bar.py" in data["matches"]


async def test_glob_recursive(tmp_path: Path) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "deep.py").write_text("x")
    (tmp_path / "root.py").write_text("x")

    result = await glob("**/*.py", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert len(data["matches"]) == 2
    assert "sub/deep.py" in data["matches"]
    assert "root.py" in data["matches"]


async def test_glob_no_matches(tmp_path: Path) -> None:
    result = await glob("*.xyz", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["matches"] == []
    assert data["count"] == 0


async def test_glob_default_path(tmp_path: Path) -> None:
    (tmp_path / "test.py").write_text("x")
    cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        result = await glob("*.py")
        data = json.loads(result[0].text)
        assert data["status"] == "success"
        assert "test.py" in data["matches"]
    finally:
        os.chdir(str(cwd))


async def test_grep_basic(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello world\nfoo bar\nbaz qux\n")

    result = await grep("foo", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 1
    assert data["matches"][0]["line"] == 2
    assert "foo" in data["matches"][0]["content"]


async def test_grep_single_file(tmp_path: Path) -> None:
    f = tmp_path / "target.txt"
    f.write_text("apple\nbanana\napple pie\n")

    result = await grep("apple", path=str(f))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 2
    assert data["matches"][0]["line"] == 1
    assert data["matches"][1]["line"] == 3


async def test_grep_case_insensitive(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("Hello\nHELLO\nhello\n")

    result = await grep("hello", path=str(tmp_path), case_sensitive=False)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 3


async def test_grep_case_sensitive(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("Hello\nHELLO\nhello\n")

    result = await grep("hello", path=str(tmp_path), case_sensitive=True)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 1


async def test_grep_include_filter(tmp_path: Path) -> None:
    (tmp_path / "foo.py").write_text("search me")
    (tmp_path / "foo.txt").write_text("search me")
    (tmp_path / "foo.md").write_text("search me")

    result = await grep("search", path=str(tmp_path), include="*.py")
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 1


async def test_grep_no_matches(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("nothing to see here")

    result = await grep("zzzzz", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["matches"] == []
    assert data["count"] == 0


async def test_grep_regex_pattern(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("abc123\ndef456\nabc789\n")

    result = await grep(r"abc\d+", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 2


async def test_grep_max_results(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("\n".join(f"line {i}" for i in range(50)))

    result = await grep("line", path=str(tmp_path), max_results=5)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 5
    assert data["truncated"] is True


async def test_grep_invalid_regex(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello")

    result = await grep(r"[invalid", path=str(tmp_path))
    text = result[0].text
    assert text.startswith("Error:")
