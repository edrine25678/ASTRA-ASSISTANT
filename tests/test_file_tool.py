"""
Unit tests for the scoped file tools (tools/file_tool.py).

All tests use temporary allowed roots: nothing touches the real
Desktop, Documents or Downloads folders, and nothing opens files
with their default applications.

Run from the project root:

    python tests/test_file_tool.py
    (or: .venv/Scripts/python.exe tests/test_file_tool.py)
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from tools.file_tool import (
    FileCreateTextTool,
    FileDeleteTool,
    FileListDirectoryTool,
    FileOpenFileTool,
    FileReadTextTool,
    FileSearchTool,
)

_PASS = 0
_FAIL = 0


def _check(label, actual, expected):

    global _PASS, _FAIL

    if actual == expected:

        _PASS += 1

        return True

    _FAIL += 1

    print(f"FAIL: {label}")
    print(f"  expected: {expected!r}")
    print(f"  actual:   {actual!r}")

    return False


def _setup():
    """Create a temp workspace with a few files."""

    root = tempfile.mkdtemp(prefix="astra_file_test_")

    with open(os.path.join(root, "notes.txt"), "w", encoding="utf-8") as file:
        file.write("hello world\n")

    with open(os.path.join(root, "report.txt"), "w", encoding="utf-8") as file:
        file.write("quarterly report\n")

    with open(os.path.join(root, "python_code.py"), "w", encoding="utf-8") as file:
        file.write("print('hi')\n")

    return root


def _cleanup(root):
    shutil.rmtree(root, ignore_errors=True)


def test_search():

    print()
    print("--- FILE SEARCH ---")

    root = _setup()

    try:

        tool = FileSearchTool(allowed_roots=[root])

        result = tool.run({"query": "notes"})

        _check("search finds notes", result.success, True)
        _check("search found 1", result.data["count"], 1)
        _check("search path correct",
               result.data["files"][0].endswith("notes.txt"), True)

        result = tool.run({"query": "python", "extensions": [".py"]})

        _check("search by extension", result.success, True)
        _check("search found py", result.data["count"], 1)
        _check("search py path",
               result.data["files"][0].endswith("python_code.py"), True)

        result = tool.run({"query": "zzz_not_there"})

        _check("search miss controlled", result.success, False)

        result = tool.run({})

        _check("search without query controlled", result.success, False)

        result = tool.run({"query": "", "modified_since": "today"})

        _check("search modified today", result.success, True)

    finally:
        _cleanup(root)


def test_list_directory():

    print()
    print("--- LIST DIRECTORY ---")

    root = _setup()

    try:

        tool = FileListDirectoryTool(allowed_roots=[root])

        result = tool.run({"path": root})

        _check("list success", result.success, True)

        names = set(result.data["items"])

        _check("list contains notes", "notes.txt" in names, True)
        _check("list contains report", "report.txt" in names, True)

        result = tool.run({"path": "C:\\No\\Such\\Folder"})

        _check("list missing folder controlled", result.success, False)

    finally:
        _cleanup(root)


def test_read_text():

    print()
    print("--- READ TEXT ---")

    root = _setup()

    try:

        tool = FileReadTextTool(allowed_roots=[root])

        result = tool.run({"path": os.path.join(root, "notes.txt")})

        _check("read success", result.success, True)
        _check("read content", result.data["content"], "hello world\n")

        result = tool.run({"path": os.path.join(root, "missing.txt")})

        _check("read missing controlled", result.success, False)

    finally:
        _cleanup(root)


def test_create_text():

    print()
    print("--- CREATE TEXT ---")

    root = _setup()

    try:

        tool = FileCreateTextTool(allowed_roots=[root])

        target = os.path.join(root, "sub", "made.txt")

        result = tool.run({"path": target, "content": "created by test"})

        _check("create success", result.success, True)
        _check("create file exists", os.path.isfile(target), True)

        with open(target, "r", encoding="utf-8") as file:
            _check("create content", file.read().strip(), "created by test")

        outside = os.path.join(
            os.path.dirname(root), "outside.txt"
        )

        result = tool.run({"path": outside, "content": "x"})

        _check("create outside refused", result.success, False)
        _check("outside not created", os.path.isfile(outside), False)

    finally:
        _cleanup(root)


def test_delete():

    print()
    print("--- DELETE ---")

    root = _setup()

    try:

        tool = FileDeleteTool(allowed_roots=[root])

        target = os.path.join(root, "report.txt")

        result = tool.run({"path": target})

        _check("delete success", result.success, True)
        _check("delete removed file", os.path.isfile(target), False)

        result = tool.run({"path": os.path.join(root, "gone.txt")})

        _check("delete missing controlled", result.success, False)

    finally:
        _cleanup(root)


def test_open_file_validation():

    print()
    print("--- OPEN FILE VALIDATION ---")

    root = _setup()

    try:

        tool = FileOpenFileTool(allowed_roots=[root])

        result = tool.run({"path": os.path.join(root, "missing.txt")})

        _check("open missing controlled", result.success, False)

        outside = os.path.join(os.path.dirname(root), "secret.txt")

        result = tool.run({"path": outside})

        _check("open outside refused", result.success, False)

    finally:
        _cleanup(root)


def test_project_root_protection():

    print()
    print("--- PROJECT ROOT PROTECTION ---")

    from config.settings import PROJECT_ROOT

    create = FileCreateTextTool(allowed_roots=[PROJECT_ROOT])

    result = create.run(
        {"path": os.path.join(PROJECT_ROOT, "pwned.txt"), "content": "x"}
    )

    _check("write into project refused", result.success, False)
    _check("project file not created",
           os.path.isfile(os.path.join(PROJECT_ROOT, "pwned.txt")), False)

    delete = FileDeleteTool(allowed_roots=[PROJECT_ROOT])

    result = delete.run({"path": PROJECT_ROOT})

    _check("delete project refused", result.success, False)


def main():

    print("================================")
    print("    ASTRA FILE TOOL TESTS")
    print("================================")

    test_search()
    test_list_directory()
    test_read_text()
    test_create_text()
    test_delete()
    test_open_file_validation()
    test_project_root_protection()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()