import json
from pathlib import Path

import pytest

from shutil_mcp.tools.file_ops import cat, cp, mv, rm, which


@pytest.mark.asyncio
async def test_cp_mv_rm(tmp_path: Path) -> None:
    # Set up source and destination
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file.txt").write_text("content")

    dst_dir = tmp_path / "dst"

    # Copy
    cp_result = await cp(str(src_dir), str(dst_dir))
    cp_data = json.loads(cp_result[0].text)
    assert cp_data["status"] == "success"
    assert (dst_dir / "file.txt").exists()
    assert (dst_dir / "file.txt").read_text() == "content"

    # Move
    renamed_dir = tmp_path / "renamed"
    mv_result = await mv(str(dst_dir), str(renamed_dir))
    mv_data = json.loads(mv_result[0].text)
    assert mv_data["status"] == "success"
    assert renamed_dir.exists()
    assert (renamed_dir / "file.txt").exists()
    assert not dst_dir.exists()

    # Remove
    rm_result = await rm(str(renamed_dir), recursive=True)
    rm_data = json.loads(rm_result[0].text)
    assert rm_data["status"] == "success"
    assert not renamed_dir.exists()


@pytest.mark.asyncio
async def test_which() -> None:
    # Test with a common command
    result = await which("python3")
    data = json.loads(result[0].text)
    assert data["status"] == "found"
    assert "python3" in data["path"]


@pytest.mark.asyncio
async def test_cat_whole_file(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    result = await cat(str(test_file))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line1\nline2\nline3\n"
    assert data["operation"] == "cat"
    assert "lines" not in data


@pytest.mark.asyncio
async def test_cat_with_start_line(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

    result = await cat(str(test_file), start_line=3)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line3\nline4\nline5\n"
    assert data["lines"] == "3-end"


@pytest.mark.asyncio
async def test_cat_with_end_line(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

    result = await cat(str(test_file), end_line=3)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line1\nline2\nline3\n"
    assert data["lines"] == "1-3"


@pytest.mark.asyncio
async def test_cat_with_start_and_end_line(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\nline4\nline5\n")

    result = await cat(str(test_file), start_line=2, end_line=4)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line2\nline3\nline4\n"
    assert data["lines"] == "2-4"


@pytest.mark.asyncio
async def test_cat_range_beyond_file_length(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\n")

    result = await cat(str(test_file), start_line=10, end_line=20)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == ""


@pytest.mark.asyncio
async def test_cat_end_line_beyond_file_length(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    result = await cat(str(test_file), start_line=2, end_line=100)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line2\nline3\n"


@pytest.mark.asyncio
async def test_cat_empty_file(tmp_path: Path) -> None:
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")

    result = await cat(str(test_file))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == ""


@pytest.mark.asyncio
async def test_cat_empty_file_with_range(tmp_path: Path) -> None:
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")

    result = await cat(str(test_file), start_line=1, end_line=5)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == ""


@pytest.mark.asyncio
async def test_cat_nonexistent_file(tmp_path: Path) -> None:
    result = await cat(str(tmp_path / "nonexistent.txt"))
    text = result[0].text
    assert text.startswith("Error:")


@pytest.mark.asyncio
async def test_cat_directory(tmp_path: Path) -> None:
    result = await cat(str(tmp_path))
    text = result[0].text
    assert text.startswith("Error:")


@pytest.mark.asyncio
async def test_cat_single_line_file(tmp_path: Path) -> None:
    test_file = tmp_path / "single.txt"
    test_file.write_text("only line\n")

    result = await cat(str(test_file))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "only line\n"

    result = await cat(str(test_file), start_line=1, end_line=1)
    data = json.loads(result[0].text)
    assert data["content"] == "only line\n"


@pytest.mark.asyncio
async def test_cat_file_without_trailing_newline(tmp_path: Path) -> None:
    test_file = tmp_path / "no_newline.txt"
    test_file.write_text("line1\nline2")

    result = await cat(str(test_file))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line1\nline2"


@pytest.mark.asyncio
async def test_cat_unicode_content(tmp_path: Path) -> None:
    test_file = tmp_path / "unicode.txt"
    test_file.write_text("こんにちは\n世界\n")

    result = await cat(str(test_file))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "こんにちは\n世界\n"


@pytest.mark.asyncio
async def test_cat_first_line_only(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    result = await cat(str(test_file), start_line=1, end_line=1)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line1\n"


@pytest.mark.asyncio
async def test_cat_last_line_only(tmp_path: Path) -> None:
    test_file = tmp_path / "test.txt"
    test_file.write_text("line1\nline2\nline3\n")

    result = await cat(str(test_file), start_line=3, end_line=3)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["content"] == "line3\n"
