import json
from pathlib import Path

import pytest

from shutil_mcp.tools.search import glob, grep, tree

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


async def test_tree_basic(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("deep")

    result = await tree(str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["operation"] == "tree"
    children = data["tree"]["children"]
    assert len(children) == 3
    names = {c["name"] for c in children}
    assert names == {"a.txt", "b.txt", "sub"}


async def test_tree_max_depth(tmp_path: Path) -> None:
    sub1 = tmp_path / "a" / "b" / "c"
    sub1.mkdir(parents=True)
    (sub1 / "deep.txt").write_text("x")

    result = await tree(str(tmp_path), max_depth=1)
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["tree"]["children"][0]["children"][0].get("truncated") is True


async def test_tree_file_sizes(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("x" * 100)

    result = await tree(str(tmp_path))
    data = json.loads(result[0].text)

    child = data["tree"]["children"][0]
    assert child["name"] == "f.txt"
    assert child["size"] == 100


async def test_tree_with_symlinks(tmp_path: Path) -> None:
    target_file = tmp_path / "target.txt"
    target_file.write_text("hello")
    link_file = tmp_path / "link.txt"
    link_file.symlink_to(target_file)

    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    link_dir = tmp_path / "link_dir"
    link_dir.symlink_to(target_dir)

    result = await tree(str(tmp_path))
    data = json.loads(result[0].text)
    assert data["status"] == "success"

    children = {c["name"]: c for c in data["tree"]["children"]}
    assert children["link.txt"]["type"] == "symlink"
    assert children["link_dir"]["type"] == "symlink"
    assert children["target_dir"]["type"] == "directory"


async def test_grep_binary_file_skipped(tmp_path: Path) -> None:
    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"hello\x00world\x00pattern")

    txt_file = tmp_path / "text.txt"
    txt_file.write_text("hello world pattern\n")

    result = await grep("pattern", path=str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    assert data["count"] == 1
    assert data["matches"][0]["file"] == str(txt_file)


async def test_tree_cycle_detection(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    (parent / "file.txt").write_text("hello")

    # Create cyclic symlink inside parent pointing back to parent
    loop_link = parent / "loop"
    loop_link.symlink_to(parent)

    result = await tree(str(tmp_path))
    data = json.loads(result[0].text)

    assert data["status"] == "success"
    parent_entry = data["tree"]["children"][0]
    assert parent_entry["name"] == "parent"


async def test_tree_symlink_cycle_detection(tmp_path: Path) -> None:
    """Test that tree() handles symlink cycles without infinite recursion."""
    target = tmp_path / "cycle" / "a"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("test")

    # Create a symlink that points back to its parent, forming a cycle
    cycle_link = target / "cycle"
    cycle_link.symlink_to("..")

    result = await tree(str(tmp_path / "cycle" / "a"))
    data = json.loads(result[0].text)

    # Should not crash — should have detected cycle or truncated
    assert data["status"] == "success"
    # Verify we didn't recurse infinitely
    children = data["tree"]["children"][0].get("children", [])
    assert len(children) < 100  # Should not have recursed deeply


async def test_tree_invalid_max_depth(tmp_path: Path) -> None:
    """Test that tree() rejects negative max_depth values."""
    result = await tree(str(tmp_path), max_depth=-1)
    text = result[0].text
    assert text.startswith("Error:")
    assert "max_depth" in text.lower()
