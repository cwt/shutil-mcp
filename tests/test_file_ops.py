import json
from pathlib import Path

import pytest

from shutil_mcp.tools.file_ops import (
    cat,
    chmod,
    chown,
    cp,
    mkdir,
    mv,
    rm,
    touch,
    which,
)


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
    rm_result = await rm(str(renamed_dir))
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


@pytest.mark.asyncio
async def test_mkdir_basic(tmp_path: Path) -> None:
    new_dir = tmp_path / "newdir"

    result = await mkdir(str(new_dir))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "mkdir"
    assert new_dir.exists()
    assert new_dir.is_dir()


@pytest.mark.asyncio
async def test_mkdir_with_parents(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "c"

    result = await mkdir(str(nested), parents=True)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert nested.exists()
    assert nested.is_dir()


@pytest.mark.asyncio
async def test_mkdir_existing(tmp_path: Path) -> None:
    existing = tmp_path / "existing"
    existing.mkdir()

    result = await mkdir(str(existing), parents=True)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert existing.exists()


@pytest.mark.asyncio
async def test_touch_create(tmp_path: Path) -> None:
    new_file = tmp_path / "new.txt"

    result = await touch(str(new_file))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "touch"
    assert new_file.exists()
    assert new_file.stat().st_size == 0


@pytest.mark.asyncio
async def test_touch_existing(tmp_path: Path) -> None:
    existing = tmp_path / "existing.txt"
    existing.write_text("content")

    result = await touch(str(existing))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert existing.exists()
    assert existing.read_text() == "content"


@pytest.mark.asyncio
async def test_rm_file_symlink(tmp_path: Path) -> None:
    import os

    original = tmp_path / "original.txt"
    original.write_text("important data")

    link = tmp_path / "link.txt"
    link.symlink_to(original)

    result = await rm(str(link))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "trash"
    assert not os.path.lexists(link)
    # Original file must NOT be deleted
    assert original.exists()
    assert original.read_text() == "important data"


@pytest.mark.asyncio
async def test_rm_broken_symlink(tmp_path: Path) -> None:
    import os

    broken = tmp_path / "broken_link.txt"
    broken.symlink_to(tmp_path / "does_not_exist.txt")

    result = await rm(str(broken))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "trash"
    assert not os.path.lexists(broken)


@pytest.mark.asyncio
async def test_rm_dir_symlink(tmp_path: Path) -> None:
    import os

    original_dir = tmp_path / "original_dir"
    original_dir.mkdir()
    (original_dir / "file.txt").write_text("hello")

    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(original_dir)

    result = await rm(str(link_dir))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "trash"
    assert not os.path.lexists(link_dir)
    # Original directory and contents must NOT be deleted
    assert original_dir.exists()
    assert (original_dir / "file.txt").exists()


@pytest.mark.asyncio
async def test_chmod_octal_modes(tmp_path: Path) -> None:
    test_file = tmp_path / "chmod_test.txt"
    test_file.write_text("mode test")

    # Octal integer
    result = await chmod(str(test_file), 0o644)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["mode"] == oct(0o644)

    # Octal string "0755"
    result = await chmod(str(test_file), "0755")
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["mode"] == oct(0o755)

    # Octal string "0o700"
    result = await chmod(str(test_file), "0o700")
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["mode"] == oct(0o700)


@pytest.mark.asyncio
async def test_chown_basic(tmp_path: Path) -> None:
    import os

    test_file = tmp_path / "chown_test.txt"
    test_file.write_text("owner test")

    current_uid = os.getuid()
    result = await chown(str(test_file), user=str(current_uid))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "chown"


@pytest.mark.asyncio
async def test_cp_symlink_verification(tmp_path: Path) -> None:
    """Verify that symlink copies are size-verified even when follow_symlinks=True."""
    original = tmp_path / "original.txt"
    original.write_text("symlink target content")
    link = tmp_path / "link.txt"
    link.symlink_to(original)

    dst = tmp_path / "copied_link.txt"
    result = await cp(str(link), str(dst), follow_symlinks=True)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["verified"] is True
    assert dst.exists()
    assert dst.read_text() == "symlink target content"


@pytest.mark.asyncio
async def test_cp_symlink_no_follow_verification(tmp_path: Path) -> None:
    """Verify symlink copy with follow_symlinks=False is still checked."""
    original = tmp_path / "original.txt"
    original.write_text("target")
    link = tmp_path / "link.txt"
    link.symlink_to(original)

    dst = tmp_path / "copied_link_nofollow.txt"
    result = await cp(str(link), str(dst), follow_symlinks=False)
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["verified"] is True
    assert dst.is_symlink()
    assert str(dst.readlink()) == str(original.resolve())


@pytest.mark.asyncio
async def test_cp_directory_copy_verification(tmp_path: Path) -> None:
    """Verify directory copy checks all file sizes recursively."""
    src_dir = tmp_path / "src_dir"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("content a")
    sub = src_dir / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("content b deep")

    dst_dir = tmp_path / "dst_dir"
    result = await cp(str(src_dir), str(dst_dir))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["verified"] is True
    assert (dst_dir / "a.txt").read_text() == "content a"
    assert (dst_dir / "sub" / "b.txt").read_text() == "content b deep"


@pytest.mark.asyncio
async def test_mv_directory_overwrite_protection(tmp_path: Path) -> None:
    """Verify mv with overwrite=False preserves source when dest dir exists."""
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "file.txt").write_text("source data")
    dst = tmp_path / "dst_dir"
    dst.mkdir()
    (dst / "existing.txt").write_text("existing")

    # Destination directory already exists, overwrite=False should fail
    result = await mv(str(src), str(dst), overwrite=False)
    text = result[0].text
    assert text.startswith("Error:")
    assert "already exists" in text
    assert src.exists()
    assert (src / "file.txt").read_text() == "source data"
