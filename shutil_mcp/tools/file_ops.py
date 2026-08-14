"""File operations tools.

Provides 'cp', 'mv', 'rm', 'restore', 'chown', 'chmod', 'which', and 'cat' tools.
"""

import asyncio
import json
import os
import stat as stat_module
import time
import uuid
from pathlib import Path

import aioshutil
from mcp.types import TextContent

from shutil_mcp.decorators import handle_errors, json_tool
from shutil_mcp.helpers import (
    get_trash_dir,
    is_trash_path,
    sanitize_trash_name,
    validate_path,
    validate_path_in_jail,
)
from shutil_mcp.server import mcp


@mcp.tool()
@handle_errors
@json_tool
async def cp(
    src: str,
    dst: str,
    follow_symlinks: bool = True,
    overwrite: bool = True,
) -> list[TextContent]:
    """Copy files or directories recursively with size verification and overwrite protection.

    Args:
        src: Source path
        dst: Destination path
        follow_symlinks: Whether to follow symlinks (default: True)
        overwrite: Whether to overwrite existing destination files (default: True)
    """
    source = validate_path(src)
    dest = Path(dst).absolute()
    dest = validate_path_in_jail(dest)

    target_dest = dest
    if dest.exists() and dest.is_dir() and not source.is_dir():
        target_dest = dest / source.name
        target_dest = validate_path_in_jail(target_dest)

    if target_dest.exists() and not overwrite:
        raise ValueError(
            f"Destination '{target_dest}' already exists. "
            f"Set overwrite=True to replace."
        )

    loop = asyncio.get_running_loop()

    if source.is_dir():
        if dest.resolve() == source.resolve() or dest.resolve().is_relative_to(
            source.resolve()
        ):
            raise ValueError(
                f"Cannot copy directory '{source}' into itself or its subdirectory '{dest}'."
            )
        await aioshutil.copytree(
            source,
            target_dest,
            symlinks=not follow_symlinks,
            dirs_exist_ok=overwrite,
        )
        op_type = "directory_copy"

        def _verify_dir_copy() -> None:
            if not target_dest.exists() or not target_dest.is_dir():
                raise IOError(
                    f"Copy verification failed: destination '{target_dest}' "
                    f"is not a directory"
                )

            def _compare_sizes(src: Path, dst: Path) -> None:
                for src_item in src.rglob("*"):
                    rel = src_item.relative_to(source)
                    dst_item = target_dest / rel
                    if src_item.is_file() and not src_item.is_symlink():
                        if not dst_item.exists():
                            raise IOError(
                                f"Copy verification failed: missing "
                                f"'{dst_item}'"
                            )
                        if dst_item.is_symlink():
                            continue
                        if src_item.stat().st_size != dst_item.stat().st_size:
                            raise IOError(
                                f"Copy verification failed: size mismatch "
                                f"for '{rel}' "
                                f"(source: {src_item.stat().st_size}, "
                                f"dest: {dst_item.stat().st_size})"
                            )
                    elif src_item.is_dir() and not src_item.is_symlink():
                        if not dst_item.is_dir():
                            raise IOError(
                                f"Copy verification failed: expected directory "
                                f"'{dst_item}'"
                            )

            _compare_sizes(source, target_dest)

        await loop.run_in_executor(None, _verify_dir_copy)
    else:
        await aioshutil.copy2(
            source, target_dest, follow_symlinks=follow_symlinks
        )
        op_type = "file_copy"

        def _verify_copy() -> None:
            if not target_dest.exists():
                raise IOError(
                    f"Copy verification failed: destination '{target_dest}' "
                    f"does not exist"
                )
            src_size = source.stat(follow_symlinks=follow_symlinks).st_size
            dst_size = target_dest.stat(follow_symlinks=follow_symlinks).st_size
            if src_size != dst_size:
                raise IOError(
                    f"Copy verification failed: size mismatch "
                    f"(source: {src_size}, dest: {dst_size})"
                )

        await loop.run_in_executor(None, _verify_copy)

    return json.dumps(
        {
            "operation": op_type,
            "src": str(source),
            "dst": str(target_dest),
            "verified": True,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def mv(
    src: str,
    dst: str,
    overwrite: bool = True,
) -> list[TextContent]:
    """Move or rename files or directories with destination verification and fault tolerance.

    Ensures the destination file is verified before deleting the origin. If any error
    or failure occurs during the move, the original source file remains preserved intact.

    Args:
        src: Source path
        dst: Destination path
        overwrite: Whether to overwrite existing destination files (default: True)
    """
    source = validate_path(src)
    dest = Path(dst).absolute()
    dest = validate_path_in_jail(dest)

    target_dest = dest
    if dest.exists() and dest.is_dir() and not source.is_dir():
        target_dest = dest / source.name
        target_dest = validate_path_in_jail(target_dest)

    if source.resolve() == target_dest.resolve():
        return json.dumps(
            {
                "operation": "move",
                "src": str(source),
                "dst": str(target_dest),
                "verified": True,
                "status": "success",
            },
            separators=(",", ":"),
        )  # type: ignore[return-value]

    if target_dest.exists() and not overwrite:
        raise ValueError(
            f"Destination '{target_dest}' already exists. "
            f"Set overwrite=True to replace."
        )

    loop = asyncio.get_running_loop()

    if source.is_dir():
        if (
            target_dest.resolve() == source.resolve()
            or target_dest.resolve().is_relative_to(source.resolve())
        ):
            raise ValueError(
                f"Cannot move directory '{source}' into itself or its subdirectory '{target_dest}'."
            )

        await aioshutil.copytree(
            source, target_dest, symlinks=True, dirs_exist_ok=overwrite
        )

        def _verify_dir() -> None:
            if not target_dest.exists() or not target_dest.is_dir():
                raise IOError(
                    f"Move verification failed: directory '{target_dest}' was not created properly"
                )

        try:
            await loop.run_in_executor(None, _verify_dir)
        except Exception:
            if target_dest.exists():
                await aioshutil.rmtree(target_dest)
            raise

        await aioshutil.rmtree(source)
    else:
        if source.is_symlink():
            link_target = os.readlink(source)

            def _move_symlink() -> None:
                if target_dest.exists() or target_dest.is_symlink():
                    target_dest.unlink()
                os.symlink(link_target, target_dest)
                if not target_dest.is_symlink():
                    raise IOError("Failed to create destination symlink")
                source.unlink()

            await loop.run_in_executor(None, _move_symlink)
        else:
            tmp_target = (
                target_dest.parent
                / f".tmp_mv_{uuid.uuid4().hex}_{target_dest.name}"
            )
            tmp_target = validate_path_in_jail(tmp_target)

            try:
                await aioshutil.copy2(source, tmp_target, follow_symlinks=True)

                def _verify_and_finalize() -> None:
                    if not tmp_target.exists():
                        raise IOError("Temporary destination file not found")
                    src_size = source.stat().st_size
                    dst_size = tmp_target.stat().st_size
                    if src_size != dst_size:
                        raise IOError(
                            f"Move verification failed: size mismatch (source: {src_size}, dest: {dst_size})"
                        )
                    os.replace(tmp_target, target_dest)
                    if not target_dest.exists():
                        raise IOError("Failed to finalize destination file")
                    os.remove(source)

                await loop.run_in_executor(None, _verify_and_finalize)
            except Exception:
                if tmp_target.exists():
                    try:
                        tmp_target.unlink()
                    except Exception:
                        pass
                raise

    return json.dumps(
        {
            "operation": "move",
            "src": str(source),
            "dst": str(target_dest),
            "verified": True,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def rm(
    path: str,
    recursive: bool = False,
    trash: bool = False,
) -> list[TextContent]:
    """Remove files or directories, with optional soft-delete (trash) support.

    Args:
        path: Path to remove
        recursive: Whether to remove recursively if it's a directory (default: False)
        trash: If True, move to .trash folder for undo capability instead of permanent deletion (default: False)
    """
    target = validate_path(path)
    loop = asyncio.get_running_loop()

    if trash:
        trash_dir = get_trash_dir(target)
        safe_name = sanitize_trash_name(target.name)
        trash_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_name}"
        trash_dest = trash_dir / trash_name
        trash_dest = validate_path_in_jail(trash_dest)

        await aioshutil.move(target, trash_dest)

        return json.dumps(
            {
                "operation": "trash",
                "path": str(target),
                "trash_path": str(trash_dest),
                "status": "success",
            },
            separators=(",", ":"),
        )  # type: ignore[return-value]

    if target.is_symlink():

        def _unlink_symlink() -> None:
            os.unlink(target)

        await loop.run_in_executor(None, _unlink_symlink)
        op_type = "symlink_removal"
    elif target.is_dir():
        if not recursive:
            raise ValueError(
                f"'{target}' is a directory. Use recursive=True to remove."
            )
        await aioshutil.rmtree(target)
        op_type = "directory_removal"
    else:

        def _remove_file() -> None:
            os.remove(target)

        await loop.run_in_executor(None, _remove_file)
        op_type = "file_removal"

    return json.dumps(
        {"operation": op_type, "path": str(target), "status": "success"},
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def restore(
    trash_path: str,
    dst: str,
    overwrite: bool = False,
) -> list[TextContent]:
    """Restore a file or directory from the trash folder.

    Args:
        trash_path: Path to the trashed item
        dst: Destination path to restore to
        overwrite: Whether to overwrite existing destination (default: False)
    """
    source = validate_path(trash_path)
    if not is_trash_path(source):
        raise ValueError(
            f"Source path '{source}' is not inside a .trash directory. "
            f"Only items moved to trash via rm(trash=True) can be restored."
        )
    dest = Path(dst).absolute()
    dest = validate_path_in_jail(dest)

    if dest.exists() and not overwrite:
        raise ValueError(
            f"Destination '{dest}' already exists. Set overwrite=True to replace."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)

    await aioshutil.move(source, dest)

    return json.dumps(
        {
            "operation": "restore",
            "src": str(source),
            "dst": str(dest),
            "verified": True,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def gc_trash(max_age_seconds: int = 86400) -> list[TextContent]:
    """Garbage-collect trash entries older than max_age_seconds.

    Scans all .trash directories inside the jail (or the default .trash
    location when no jail is set) and permanently deletes entries whose
    timestamp prefix is older than max_age_seconds.

    Args:
        max_age_seconds: Maximum age in seconds before deletion (default: 86400 = 24 h).
    """
    from shutil_mcp.server import mcp

    now = time.time()
    total_removed = 0
    total_freed = 0

    def _collect_trash_dirs(root: Path) -> list[Path]:
        dirs: list[Path] = []
        try:
            for child in root.iterdir():
                if child.name == ".trash" and child.is_dir():
                    dirs.append(child)
                elif child.is_dir() and not child.is_symlink():
                    dirs.extend(_collect_trash_dirs(child))
        except PermissionError:
            pass
        return dirs

    if mcp.jail_path is not None:
        trash_roots = [mcp.jail_path.resolve()]
    else:
        trash_roots = [Path(".").resolve()]

    for root in trash_roots:
        for trash_dir in _collect_trash_dirs(root):
            try:
                for entry in trash_dir.iterdir():
                    if entry.is_file() or (
                        entry.is_symlink() and not entry.exists()
                    ):
                        try:
                            mtime = entry.stat(follow_symlinks=False).st_mtime
                        except OSError:
                            continue
                        if now - mtime > max_age_seconds:
                            try:
                                total_freed += entry.stat(
                                    follow_symlinks=False
                                ).st_size
                                entry.unlink()
                                total_removed += 1
                            except OSError:
                                pass
                    elif entry.is_dir() and not entry.is_symlink():
                        try:
                            import shutil

                            size = 0
                            for sub in entry.rglob("*"):
                                try:
                                    size += sub.stat().st_size
                                except OSError:
                                    pass
                            shutil.rmtree(entry)
                            total_removed += 1
                            total_freed += size
                        except OSError:
                            pass
            except PermissionError:
                pass

    return json.dumps(
        {
            "operation": "gc_trash",
            "removed_count": total_removed,
            "freed_bytes": total_freed,
            "max_age_seconds": max_age_seconds,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def chmod(path: str, mode: int | str) -> list[TextContent]:
    """Change file or directory permissions with automatic rollback on failure and previous mode tracking.

    If the operation fails, permissions stay intact or rollback to the original state.
    The response JSON includes 'previous_mode' to enable immediate 1-step undo.

    Args:
        path: Path to modify
        mode: Numeric mode (e.g., 0o755, 493, "755", "0755", "0o755")
    """
    target = validate_path(path)

    if isinstance(mode, str):
        mode_str = mode.strip()
        if mode_str.startswith(("0o", "0O")):
            numeric_mode = int(mode_str, 8)
        elif len(mode_str) <= 4 and all(c in "01234567" for c in mode_str):
            numeric_mode = int(mode_str, 8)
        else:
            numeric_mode = int(mode_str)
    else:
        numeric_mode = mode

    loop = asyncio.get_running_loop()

    def _get_mode() -> int:
        return stat_module.S_IMODE(target.stat(follow_symlinks=False).st_mode)

    prev_mode_int = await loop.run_in_executor(None, _get_mode)
    previous_mode_oct = oct(prev_mode_int)

    def _apply_chmod() -> None:
        try:
            os.chmod(target, numeric_mode)
        except Exception as err:
            try:
                os.chmod(target, prev_mode_int)
            except Exception:
                pass
            raise err

    await loop.run_in_executor(None, _apply_chmod)

    return json.dumps(
        {
            "operation": "chmod",
            "path": str(target),
            "mode": oct(numeric_mode),
            "previous_mode": previous_mode_oct,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def chown(
    path: str, user: str | int | None = None, group: str | int | None = None
) -> list[TextContent]:
    """Change file or directory ownership with automatic rollback on failure and previous ownership tracking.

    If the operation fails, ownership stays intact or rolls back to previous user and group.
    The response JSON includes 'previous_user' and 'previous_group' to enable immediate 1-step undo.

    Args:
        path: Path to modify
        user: Username or numeric UID (default: None)
        group: Group name or numeric GID (default: None)
    """
    target = validate_path(path)
    loop = asyncio.get_running_loop()

    def _get_owner() -> tuple[int, int]:
        st = target.stat(follow_symlinks=False)
        return (st.st_uid, st.st_gid)

    prev_uid, prev_gid = await loop.run_in_executor(None, _get_owner)

    final_user = int(user) if isinstance(user, str) and user.isdigit() else user
    final_group = (
        int(group) if isinstance(group, str) and group.isdigit() else group
    )

    try:
        await aioshutil.chown(str(target), user=final_user, group=final_group)  # type: ignore[arg-type]
    except Exception as err:
        try:
            await aioshutil.chown(str(target), user=prev_uid, group=prev_gid)
        except Exception:
            pass
        raise err

    return json.dumps(
        {
            "operation": "chown",
            "path": str(target),
            "user": user,
            "group": group,
            "previous_user": prev_uid,
            "previous_group": prev_gid,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def which(cmd: str, path: str | None = None) -> list[TextContent]:
    """Find the path to an executable.

    Args:
        cmd: Executable name
        path: Search path (default: None, uses system PATH)
    """
    found_path = await aioshutil.which(cmd, path=path)

    return json.dumps(
        {
            "command": cmd,
            "path": found_path,
            "status": "found" if found_path else "not_found",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def mkdir(path: str, parents: bool = True) -> list[TextContent]:
    """Create a directory.

    Args:
        path: Directory path to create
        parents: Create parent directories if they don't exist (default: True)
    """
    target = Path(path).absolute()
    target = validate_path_in_jail(target)

    def _create_dir() -> None:
        target.mkdir(parents=parents, exist_ok=True)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _create_dir)

    return json.dumps(
        {
            "operation": "mkdir",
            "path": str(target),
            "parents": parents,
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


@mcp.tool()
@handle_errors
@json_tool
async def touch(path: str) -> list[TextContent]:
    """Create an empty file or update file timestamps.

    Args:
        path: File path to create or update
    """
    target = Path(path).absolute()
    target = validate_path_in_jail(target)

    def _touch_file() -> None:
        target.touch(exist_ok=True)

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _touch_file)

    return json.dumps(
        {
            "operation": "touch",
            "path": str(target),
            "status": "success",
        },
        separators=(",", ":"),
    )  # type: ignore[return-value]


def _read_file_lines(
    filepath: Path, start_line: int | None, end_line: int | None
) -> str:
    """Read file content, optionally limited to a line range."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        if start_line is None and end_line is None:
            return f.read()
        lines: list[str] = []
        for i, line in enumerate(f, 1):
            if start_line and i < start_line:
                continue
            if end_line and i > end_line:
                break
            lines.append(line)
        return "".join(lines)


@mcp.tool()
@handle_errors
@json_tool
async def cat(
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> list[TextContent]:
    """Read file content, optionally limited to a specific line range.

    Args:
        path: File path to read
        start_line: First line to include (1-based, inclusive). None for start of file.
        end_line: Last line to include (1-based, inclusive). None for end of file.
    """
    target = validate_path(path)
    if target.is_dir():
        raise ValueError(f"Cannot read directory: {target}")

    loop = asyncio.get_running_loop()
    content = await loop.run_in_executor(
        None, _read_file_lines, target, start_line, end_line
    )

    result: dict[str, object] = {
        "operation": "cat",
        "path": str(target),
        "status": "success",
        "content": content,
    }
    if start_line is not None or end_line is not None:
        result["lines"] = f"{start_line or 1}-{end_line or 'end'}"

    return json.dumps(result, separators=(",", ":"))  # type: ignore[return-value]
