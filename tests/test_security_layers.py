import io
import json
import os
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from shutil_mcp.tools.archive import make_archive, unpack_archive
from shutil_mcp.tools.file_ops import (
    chmod,
    chown,
    cp,
    empty_trash,
    gc_trash,
    mv,
    restore,
    rm,
)


@pytest.mark.asyncio
async def test_mv_file_verification_and_origin_removal(tmp_path: Path) -> None:
    src = tmp_path / "origin.txt"
    src.write_text("critical data to move")
    dst = tmp_path / "target.txt"

    result = await mv(str(src), str(dst))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["verified"] is True
    assert dst.exists()
    assert dst.read_text() == "critical data to move"
    assert not src.exists()


@pytest.mark.asyncio
async def test_mv_to_existing_directory_target(tmp_path: Path) -> None:
    src = tmp_path / "doc.txt"
    src.write_text("file content")
    target_dir = tmp_path / "folder"
    target_dir.mkdir()

    result = await mv(str(src), str(target_dir))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert (target_dir / "doc.txt").exists()
    assert (target_dir / "doc.txt").read_text() == "file content"
    assert not src.exists()


@pytest.mark.asyncio
async def test_mv_same_file_safety(tmp_path: Path) -> None:
    src = tmp_path / "same.txt"
    src.write_text("safe content")

    result = await mv(str(src), str(src))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert src.exists()
    assert src.read_text() == "safe content"


@pytest.mark.asyncio
async def test_mv_overwrite_protection(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    src.write_text("new content")
    dst = tmp_path / "dst.txt"
    dst.write_text("existing content")

    # With overwrite=False, should fail and preserve both files
    result = await mv(str(src), str(dst), overwrite=False)
    text = result[0].text
    assert text.startswith("Error:")
    assert "already exists" in text
    assert src.exists()
    assert src.read_text() == "new content"
    assert dst.exists()
    assert dst.read_text() == "existing content"

    # With overwrite=True (default), should succeed
    result2 = await mv(str(src), str(dst), overwrite=True)
    data = json.loads(result2[0].text)
    assert data["status"] == "success"
    assert not src.exists()
    assert dst.read_text() == "new content"


@pytest.mark.asyncio
async def test_mv_directory_into_self_rejected(tmp_path: Path) -> None:
    parent = tmp_path / "parent_dir"
    parent.mkdir()
    child = parent / "sub_dir"

    result = await mv(str(parent), str(child))
    text = result[0].text
    assert text.startswith("Error:")
    assert "into itself or its subdirectory" in text
    assert parent.exists()


@pytest.mark.asyncio
async def test_mv_directory_verified_success(tmp_path: Path) -> None:
    src_dir = tmp_path / "dir_src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text("aaa")
    (src_dir / "sub").mkdir()
    (src_dir / "sub" / "b.txt").write_text("bbb")

    dst_dir = tmp_path / "dir_dst"

    result = await mv(str(src_dir), str(dst_dir))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["verified"] is True
    assert not src_dir.exists()
    assert (dst_dir / "a.txt").read_text() == "aaa"
    assert (dst_dir / "sub" / "b.txt").read_text() == "bbb"


@pytest.mark.asyncio
async def test_mv_preserves_source_on_verification_failure(
    tmp_path: Path,
) -> None:
    src = tmp_path / "valuable.txt"
    src.write_text("do not lose this")
    dst = tmp_path / "dest.txt"

    def _broken_replace(src_p: Path, dst_p: Path) -> None:
        raise OSError("Simulated disk I/O error during finalization")

    with patch("os.replace", side_effect=_broken_replace):
        result = await mv(str(src), str(dst))
        text = result[0].text
        assert text.startswith("Error:")
        assert "Simulated disk I/O error" in text

    # Source file MUST still exist intact
    assert src.exists()
    assert src.read_text() == "do not lose this"


@pytest.mark.asyncio
async def test_mv_symlink(tmp_path: Path) -> None:
    original = tmp_path / "real.txt"
    original.write_text("real content")
    sym = tmp_path / "sym_link.txt"
    sym.symlink_to(original)

    dest_link = tmp_path / "moved_sym.txt"
    result = await mv(str(sym), str(dest_link))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert dest_link.is_symlink()
    assert dest_link.read_text() == "real content"
    assert not sym.exists()
    assert original.exists()


@pytest.mark.asyncio
async def test_chmod_previous_mode_and_undo(tmp_path: Path) -> None:
    test_file = tmp_path / "permissions.txt"
    test_file.write_text("permissions test")

    # Set initial mode
    os.chmod(test_file, 0o644)

    # Change to 0o755
    res1 = await chmod(str(test_file), "0755")
    data1 = json.loads(res1[0].text)
    assert data1["status"] == "success"
    assert data1["mode"] == oct(0o755)
    assert data1["previous_mode"] == oct(0o644)

    # Undo using previous_mode
    res2 = await chmod(str(test_file), data1["previous_mode"])
    data2 = json.loads(res2[0].text)
    assert data2["status"] == "success"
    assert data2["mode"] == oct(0o644)
    assert data2["previous_mode"] == oct(0o755)


@pytest.mark.asyncio
async def test_chmod_rollback_on_failure(tmp_path: Path) -> None:
    test_file = tmp_path / "rollback.txt"
    test_file.write_text("rollback test")
    os.chmod(test_file, 0o600)

    def _failing_chmod(target: Path, mode: int) -> None:
        raise PermissionError("Simulated permission error")

    with patch("os.chmod", side_effect=_failing_chmod):
        result = await chmod(str(test_file), "0777")
        text = result[0].text
        assert text.startswith("Error:")
        assert "Simulated permission error" in text


@pytest.mark.asyncio
async def test_chown_previous_owner_and_undo(tmp_path: Path) -> None:
    test_file = tmp_path / "ownership.txt"
    test_file.write_text("owner test")

    uid = os.getuid()
    gid = os.getgid()

    res = await chown(str(test_file), user=str(uid), group=str(gid))
    data = json.loads(res[0].text)
    assert data["status"] == "success"
    assert data["previous_user"] == uid
    assert data["previous_group"] == gid


@pytest.mark.asyncio
async def test_cp_verification_and_overwrite(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    src.write_text("copy content")
    dst = tmp_path / "copied.txt"

    # Successful verified copy
    res = await cp(str(src), str(dst))
    data = json.loads(res[0].text)
    assert data["status"] == "success"
    assert data["verified"] is True
    assert dst.exists()
    assert dst.read_text() == "copy content"

    # Overwrite protection
    res_no_ovw = await cp(str(src), str(dst), overwrite=False)
    text = res_no_ovw[0].text
    assert text.startswith("Error:")
    assert "already exists" in text

    # Overwrite allowed
    src.write_text("updated copy content")
    res_ovw = await cp(str(src), str(dst), overwrite=True)
    data_ovw = json.loads(res_ovw[0].text)
    assert data_ovw["status"] == "success"
    assert dst.read_text() == "updated copy content"


@pytest.mark.asyncio
async def test_cp_directory_into_self_rejected(tmp_path: Path) -> None:
    parent = tmp_path / "parent_cp"
    parent.mkdir()
    child = parent / "sub_cp"

    result = await cp(str(parent), str(child))
    text = result[0].text
    assert text.startswith("Error:")
    assert "into itself or its subdirectory" in text


@pytest.mark.asyncio
async def test_rm_trash_soft_delete_and_restore(tmp_path: Path) -> None:
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    file_to_trash = work_dir / "trash_me.txt"
    file_to_trash.write_text("restore me later")

    # Soft delete to trash
    rm_result = await rm(str(file_to_trash))
    rm_data = json.loads(rm_result[0].text)
    assert rm_data["status"] == "success"
    assert rm_data["operation"] == "trash"
    trash_path = rm_data["trash_path"]
    assert Path(trash_path).exists()
    assert not file_to_trash.exists()

    # The response must report trash size, storage share, and contents.
    assert "trash" in rm_data
    assert rm_data["trash"]["item_count"] >= 1
    assert rm_data["trash"]["total_bytes"] >= 0
    assert rm_data["trash"]["storage"]["trash_used_percent"] >= 0
    trashed = [
        c
        for c in rm_data["trash"]["contents"]
        if c["original_path"] == str(file_to_trash)
    ]
    assert trashed, "trashed item should be listed with its original path"

    # Restore from trash
    restored_dest = work_dir / "trash_me.txt"
    restore_result = await restore(trash_path, str(restored_dest))
    restore_data = json.loads(restore_result[0].text)
    assert restore_data["status"] == "success"
    assert restore_data["verified"] is True
    assert restored_dest.exists()
    assert restored_dest.read_text() == "restore me later"
    assert not Path(trash_path).exists()


@pytest.mark.asyncio
async def test_restore_overwrite_protection(tmp_path: Path) -> None:
    work_dir = tmp_path / "work_restore"
    work_dir.mkdir()
    file_to_trash = work_dir / "file.txt"
    file_to_trash.write_text("original in trash")

    rm_res = await rm(str(file_to_trash))
    trash_path = json.loads(rm_res[0].text)["trash_path"]

    # Recreate existing file at destination
    file_to_trash.write_text("blocking existing file")

    # Attempt restore without overwrite
    res_no_ovw = await restore(trash_path, str(file_to_trash), overwrite=False)
    text = res_no_ovw[0].text
    assert text.startswith("Error:")
    assert "already exists" in text

    # Attempt restore with overwrite
    res_ovw = await restore(trash_path, str(file_to_trash), overwrite=True)
    data = json.loads(res_ovw[0].text)
    assert data["status"] == "success"
    assert file_to_trash.read_text() == "original in trash"


@pytest.mark.asyncio
async def test_restore_defaults_to_original_path(tmp_path: Path) -> None:
    work_dir = tmp_path / "work_default"
    work_dir.mkdir()
    file_to_trash = work_dir / "original.txt"
    file_to_trash.write_text("come back home")

    await rm(str(file_to_trash))
    assert not file_to_trash.exists()

    # Restore without dst -> should return to its recorded original path.
    trash_path = work_dir / ".trash"
    trashed_items = [
        p
        for p in trash_path.iterdir()
        if p.name != ".meta" and not p.name.startswith(".meta")
    ]
    assert trashed_items
    result = await restore(str(trashed_items[0]))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert file_to_trash.exists()
    assert file_to_trash.read_text() == "come back home"


@pytest.mark.asyncio
async def test_empty_trash_purges(tmp_path: Path) -> None:
    work_dir = tmp_path / "work_empty"
    work_dir.mkdir()
    victim = work_dir / "victim.txt"
    victim.write_text("delete me")

    await rm(str(victim))
    trash_path = work_dir / ".trash"
    assert any(p.name != ".meta" for p in trash_path.iterdir())

    result = await empty_trash(str(work_dir))
    data = json.loads(result[0].text)
    assert data["status"] == "success"
    assert data["operation"] == "empty_trash"
    assert data["item_count"] >= 1
    # Everything is gone, but the (empty) trash folder remains.
    remaining = [p for p in trash_path.iterdir() if p.name != ".meta"]
    assert remaining == []


@pytest.mark.asyncio
async def test_zip_slip_relative_attack_prevention(tmp_path: Path) -> None:
    extract_dir = tmp_path / "safe_extract"
    extract_dir.mkdir()
    malicious_zip = tmp_path / "malicious.zip"

    # Create a malicious zip file containing path traversal
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")

    result = await unpack_archive(
        filename=str(malicious_zip),
        extract_dir=str(extract_dir),
        format="zip",
    )
    text = result[0].text
    assert text.startswith("Error:")
    assert "Unsafe" in text
    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.asyncio
async def test_zip_slip_absolute_attack_prevention(tmp_path: Path) -> None:
    extract_dir = tmp_path / "safe_extract_abs"
    extract_dir.mkdir()
    malicious_zip = tmp_path / "malicious_abs.zip"

    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("/tmp/abs_evil.txt", "abs pwned")

    result = await unpack_archive(
        filename=str(malicious_zip),
        extract_dir=str(extract_dir),
        format="zip",
    )
    text = result[0].text
    assert text.startswith("Error:")
    assert "Unsafe" in text


@pytest.mark.asyncio
async def test_tar_traversal_attack_prevention(tmp_path: Path) -> None:
    extract_dir = tmp_path / "safe_tar_extract"
    extract_dir.mkdir()
    malicious_tar = tmp_path / "malicious.tar"

    # Create a malicious tar file with directory traversal member
    with tarfile.open(malicious_tar, "w") as tf:
        tar_info = tarfile.TarInfo(name="../../traversal.txt")
        data = b"malicious data"
        tar_info.size = len(data)
        tf.addfile(tar_info, io.BytesIO(data))

    result = await unpack_archive(
        filename=str(malicious_tar),
        extract_dir=str(extract_dir),
        format="tar",
    )
    text = result[0].text
    assert text.startswith("Error:")
    assert "Unsafe" in text
    assert not (tmp_path / "traversal.txt").exists()


@pytest.mark.asyncio
async def test_tar_absolute_attack_prevention(tmp_path: Path) -> None:
    extract_dir = tmp_path / "safe_tar_abs"
    extract_dir.mkdir()
    malicious_tar = tmp_path / "malicious_abs.tar"

    with tarfile.open(malicious_tar, "w") as tf:
        tar_info = tarfile.TarInfo(name="/tmp/abs_tar.txt")
        data = b"abs tar data"
        tar_info.size = len(data)
        tf.addfile(tar_info, io.BytesIO(data))

    result = await unpack_archive(
        filename=str(malicious_tar),
        extract_dir=str(extract_dir),
        format="tar",
    )
    text = result[0].text
    assert text.startswith("Error:")
    assert "Unsafe" in text


@pytest.mark.asyncio
async def test_tar_symlink_traversal_attack_prevention(tmp_path: Path) -> None:
    """Tar symlink with relative traversal must be rejected."""
    extract_dir = tmp_path / "safe_tar_sym"
    extract_dir.mkdir()
    malicious_tar = tmp_path / "malicious_sym.tar"

    # Create a tar with a symlink member pointing outside via relative path
    with tarfile.open(malicious_tar, "w") as tf:
        link_info = tarfile.TarInfo(name="evil_link")
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "../../outside.txt"
        tf.addfile(link_info)

    result = await unpack_archive(
        filename=str(malicious_tar),
        extract_dir=str(extract_dir),
        format="tar",
    )
    text = result[0].text
    assert text.startswith("Error:")
    assert "Unsafe" in text
    assert not (tmp_path / "outside.txt").exists()


@pytest.mark.asyncio
async def test_make_archive_overwrite_protection(tmp_path: Path) -> None:
    src_dir = tmp_path / "archive_src"
    src_dir.mkdir()
    (src_dir / "file.txt").write_text("archive data")

    archive_base = tmp_path / "test_arch"

    # First creation
    res1 = await make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(src_dir),
    )
    data1 = json.loads(res1[0].text)
    assert data1["status"] == "success"

    # Second creation with overwrite=False should fail
    res2 = await make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(src_dir),
        overwrite=False,
    )
    text2 = res2[0].text
    assert text2.startswith("Error:")
    assert "already exists" in text2


@pytest.mark.asyncio
async def test_restore_rejects_non_trash_path(tmp_path: Path) -> None:
    """restore() must reject paths that are not inside a .trash directory."""
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("not in trash")

    result = await restore(str(regular_file), str(tmp_path / "restored.txt"))
    text = result[0].text
    assert text.startswith("Error:")
    assert "not inside a .trash directory" in text


@pytest.mark.asyncio
async def test_gc_trash_removes_old_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """gc_trash removes entries older than max_age_seconds."""
    import time

    # Set jail to tmp_path so gc_trash scans the right location
    from shutil_mcp import server

    monkeypatch.setattr(server.mcp, "_jail_path", tmp_path.resolve())

    trash_dir = tmp_path / ".trash"
    trash_dir.mkdir()

    # Create an old entry (pretend it's 2 days old)
    old_entry = trash_dir / "1000000_abc12345_old.txt"
    old_entry.write_text("old data")
    # Set mtime to 2 days ago
    old_time = time.time() - 172800
    os.utime(str(old_entry), (old_time, old_time))

    # Create a fresh entry (should NOT be removed)
    fresh_entry = trash_dir / f"{int(time.time())}_fresh1234_fresh.txt"
    fresh_entry.write_text("fresh data")

    result = await gc_trash(max_age_seconds=86400)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["removed_count"] == 1
    assert not old_entry.exists()
    assert fresh_entry.exists()
