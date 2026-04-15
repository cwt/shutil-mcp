import json
from pathlib import Path

import pytest

from shutil_mcp.tools.file_ops import cp, mv, rm, which


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
