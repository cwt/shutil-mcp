import json
from pathlib import Path

import pytest

from shutil_mcp.tools.archive import (
    get_archive_formats,
    make_archive,
    unpack_archive,
)


@pytest.mark.asyncio
async def test_get_archive_formats() -> None:
    result = await get_archive_formats()
    data = json.loads(result[0].text)

    assert isinstance(data, list)
    assert len(data) > 0
    format_names = {item["name"] for item in data}
    assert "zip" in format_names
    assert "tar" in format_names


@pytest.mark.asyncio
async def test_make_and_unpack_archive(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("content1")
    (src_dir / "file2.txt").write_text("content2")

    archive_base = tmp_path / "my_archive"

    # Create archive
    make_result = await make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(src_dir),
    )
    make_data = json.loads(make_result[0].text)
    assert make_data["status"] == "success"
    archive_file = make_data["archive_file"]
    assert Path(archive_file).exists()

    # Unpack archive
    extract_dir = tmp_path / "extracted"
    unpack_result = await unpack_archive(
        filename=archive_file,
        extract_dir=str(extract_dir),
        format="zip",
    )
    unpack_data = json.loads(unpack_result[0].text)
    assert unpack_data["status"] == "success"

    assert (extract_dir / "file1.txt").exists()
    assert (extract_dir / "file1.txt").read_text() == "content1"
    assert (extract_dir / "file2.txt").exists()
    assert (extract_dir / "file2.txt").read_text() == "content2"


@pytest.mark.asyncio
async def test_make_archive_with_base_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sub = root / "sub"
    sub.mkdir()
    (sub / "nested.txt").write_text("nested data")

    archive_base = tmp_path / "nested_archive"

    # Create archive starting from sub directory relative to root
    make_result = await make_archive(
        base_name=str(archive_base),
        format="tar",
        root_dir=str(root),
        base_dir="sub",
    )
    make_data = json.loads(make_result[0].text)
    assert make_data["status"] == "success"

    extract_dir = tmp_path / "extracted_tar"
    unpack_result = await unpack_archive(
        filename=make_data["archive_file"],
        extract_dir=str(extract_dir),
        format="tar",
    )
    unpack_data = json.loads(unpack_result[0].text)
    assert unpack_data["status"] == "success"
    assert (extract_dir / "sub" / "nested.txt").exists()
