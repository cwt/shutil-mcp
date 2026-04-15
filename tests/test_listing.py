import json
from pathlib import Path

import pytest

from shutil_mcp.tools.listing import disk_usage, ls


@pytest.mark.asyncio
async def test_ls(tmp_path: Path) -> None:
    # Create some files and directories
    (tmp_path / "file1.txt").write_text("hello")
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file2.txt").write_text("world")

    # List the directory
    result = await ls(str(tmp_path))

    # Check JSON output
    entries = json.loads(result[0].text)
    assert len(entries) == 2

    # Check entry content
    names = [e["name"] for e in entries]
    assert "file1.txt" in names
    assert "dir1" in names

    # Check directory type
    dir_entry = next(e for e in entries if e["name"] == "dir1")
    assert dir_entry["type"] == "directory"

    # Check file type
    file_entry = next(e for e in entries if e["name"] == "file1.txt")
    assert file_entry["type"] == "file"
    assert file_entry["size"] == 5


@pytest.mark.asyncio
async def test_disk_usage(tmp_path: Path) -> None:
    result = await disk_usage(str(tmp_path))
    data = json.loads(result[0].text)

    assert "total" in data
    assert "used" in data
    assert "free" in data
    assert data["path"] == str(tmp_path.absolute())
