from pathlib import Path

import pytest

from shutil_mcp.helpers import validate_path, validate_path_in_jail
from shutil_mcp.server import SHUTIL_MCP


def test_jail_path_immutability(tmp_path: Path) -> None:
    server = SHUTIL_MCP(name="test_jail_server")
    jail_dir = tmp_path / "jail"
    jail_dir.mkdir()

    server.jail_path = str(jail_dir)
    assert server.jail_path == jail_dir.resolve()

    # Setting the exact same path should succeed without error
    server.jail_path = str(jail_dir)

    # Setting None should do nothing
    server.jail_path = None

    # Attempting to change to a different path must raise RuntimeError
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    with pytest.raises(RuntimeError, match="jail_path is immutable once set"):
        server.jail_path = str(other_dir)


def test_jail_path_prefix_collision_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shutil_mcp import server

    jail_dir = tmp_path / "jail"
    jail_dir.mkdir()
    sibling_dir = tmp_path / "jail_sibling"
    sibling_dir.mkdir()
    sibling_file = sibling_dir / "secret.txt"
    sibling_file.write_text("secret")

    # Set jail path on server
    monkeypatch.setattr(server.mcp, "_jail_path", jail_dir.resolve())

    # Valid file inside jail passes
    inside_file = jail_dir / "allowed.txt"
    inside_file.write_text("hello")
    assert validate_path(str(inside_file)) == inside_file.resolve()

    # Sibling directory starting with same prefix must fail validation
    with pytest.raises(ValueError, match="outside the allowed jail directory"):
        validate_path(str(sibling_file))

    with pytest.raises(ValueError, match="outside the allowed jail directory"):
        validate_path_in_jail(sibling_file)


def test_jail_symlink_escape_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shutil_mcp import server

    jail_dir = tmp_path / "jail"
    jail_dir.mkdir()
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside data")

    symlink_inside = jail_dir / "link_to_outside.txt"
    symlink_inside.symlink_to(outside_file)

    monkeypatch.setattr(server.mcp, "_jail_path", jail_dir.resolve())

    # Accessing symlink pointing outside jail must be blocked
    with pytest.raises(ValueError, match="outside the allowed jail directory"):
        validate_path(str(symlink_inside))


def test_jail_parent_traversal_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from shutil_mcp import server

    jail_dir = tmp_path / "jail"
    jail_dir.mkdir()

    monkeypatch.setattr(server.mcp, "_jail_path", jail_dir.resolve())

    with pytest.raises(ValueError, match="outside the allowed jail directory"):
        validate_path(str(jail_dir / ".." / "other.txt"), must_exist=False)
