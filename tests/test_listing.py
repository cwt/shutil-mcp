import json
from pathlib import Path

import pytest

from shutil_mcp.tools.listing import disk_usage, ls, stat


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

    # Check that symlinks have their own size (not target size)
    (tmp_path / "file2.txt").write_text("hello world")
    symlink = tmp_path / "symlink_to_file2"
    symlink.symlink_to("file2.txt")

    result = await ls(str(tmp_path))
    entries = json.loads(result[0].text)
    symlink_entry = next(e for e in entries if e["name"] == "symlink_to_file2")
    assert symlink_entry["type"] == "symlink"
    # Symlink size should be the link length, not target file size
    assert symlink_entry["size"] != 11  # Should not be target file size


@pytest.mark.asyncio
async def test_disk_usage(tmp_path: Path) -> None:
    result = await disk_usage(str(tmp_path))
    data = json.loads(result[0].text)

    assert "total" in data
    assert "used" in data
    assert "free" in data
    assert data["path"] == str(tmp_path.absolute())


@pytest.mark.asyncio
async def test_stat_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")

    result = await stat(str(test_file))
    data = json.loads(result[0].text)

    assert data["type"] == "file"
    assert data["size"] == 11
    assert "mode" in data
    assert "mtime" in data
    assert "inode" in data


@pytest.mark.asyncio
async def test_stat_directory(tmp_path: Path) -> None:
    result = await stat(str(tmp_path))
    data = json.loads(result[0].text)

    assert data["type"] == "directory"
