"""
Tests for the memory layer: remember, recall, forget, search,
summarize, pruning, sensitive-content rejection and persistence.

Run from the project root:

    python tests/test_memory.py
    (or: .venv/Scripts/python.exe tests/test_memory.py)

All tests use temporary databases; nothing touches the real
Astra memory.
"""

import os
import sys
import tempfile

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from memory.manager import MemoryManager

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


def _manager():

    directory = tempfile.mkdtemp()

    return MemoryManager(
        os.path.join(directory, "test.db")
    )


def test_remember_and_recall():

    print()
    print("--- REMEMBER AND RECALL ---")

    manager = _manager()

    ok, message, item = manager.remember(
        "my favorite color is blue"
    )

    _check("remember ok", ok, True)
    _check("remember message", message, "Remembered.")
    _check("remember returns item", bool(item["id"]), True)
    _check("remember defaults to long_term", item["category"], "long_term")

    ok, message, items = manager.recall("blue")

    _check("recall ok", ok, True)
    _check("recall finds item", len(items), 1)
    _check(
        "recall content",
        items[0]["content"],
        "my favorite color is blue",
    )

    ok, message, items = manager.recall()

    _check("recall all ok", ok, True)
    _check("recall all finds item", len(items), 1)

    ok, message, items = manager.recall("zebra")

    _check("recall miss not ok", ok, False)
    _check("recall miss message",
           message, "I have nothing matching that in memory.")


def test_categories():

    print()
    print("--- CATEGORIES ---")

    manager = _manager()

    manager.remember("use high contrast", category="preferences")
    manager.remember("meeting at noon", category="facts")

    counts = manager.database.count_by_category()

    _check("preferences stored", counts.get("preferences"), 1)
    _check("facts stored", counts.get("facts"), 1)

    ok, _message, items = manager.recall(
        None, category="preferences"
    )

    _check("recall by category ok", ok, True)
    _check("recall by category content", items[0]["content"], "use high contrast")


def test_forget():

    print()
    print("--- FORGET ---")

    manager = _manager()

    manager.remember("buy milk")

    ok, message, count = manager.forget("milk")

    _check("forget ok", ok, True)
    _check("forget message", message, "Forgot 1 matching memory item(s).")
    _check("forget count", count, 1)

    ok, message, _items = manager.recall("milk")

    _check("forgotten item gone", ok, False)

    ok, message, count = manager.forget("")

    _check("forget without query fails", ok, False)


def test_sensitive_rejection():

    print()
    print("--- SENSITIVE REJECTION ---")

    manager = _manager()

    for sensitive in [
        "my password is hunter2",
        "the api key is abc123",
        "my credit card number is 1234 5678",
        "remember the wifi token",
    ]:

        ok, message, _item = manager.remember(sensitive)

        _check(f"rejected: {sensitive}", ok, False)
        _check(
            "rejection message",
            message,
            "I will not store sensitive information like that.",
        )

    ok, message, _items = manager.recall()

    _check("nothing sensitive stored", ok, False)


def test_pruning():

    print()
    print("--- PRUNING ---")

    manager = _manager()

    for index in range(60):
        manager.remember(f"note number {index}", category="short_term")

    counts = manager.database.count_by_category()

    _check("short_term pruned to 50", counts.get("short_term"), 50)

    _ok, _message, items = manager.recall(None, category="short_term")

    _check("most recent kept", items[0]["content"], "note number 59")


def test_summarize():

    print()
    print("--- SUMMARIZE ---")

    manager = _manager()

    manager.remember("first note", category="short_term")
    manager.remember("second note", category="short_term")

    summary = manager.summarize(category="short_term")

    _check("summary has both notes",
           "first note" in summary and "second note" in summary, True)

    empty = MemoryManager(
        os.path.join(tempfile.mkdtemp(), "empty.db")
    )

    _check("summary empty", empty.summarize(), "I have no memories stored yet.")


def test_persistence():

    print()
    print("--- PERSISTENCE ---")

    path = os.path.join(tempfile.mkdtemp(), "persist.db")

    first = MemoryManager(path)

    first.remember("my birthday is january first")

    first.close()

    second = MemoryManager(path)

    ok, _message, items = second.recall("birthday")

    _check("survives reopen", ok, True)
    _check("content preserved", items[0]["content"], "my birthday is january first")

    second.close()


def test_disabled():

    print()
    print("--- DISABLED ---")

    manager = MemoryManager(None, enabled=False)

    ok, message, _item = manager.remember("anything")

    _check("remember disabled", ok, False)
    _check("disabled message", message, "Memory is disabled.")

    ok, message, _items = manager.recall()

    _check("recall disabled", ok, False)


def main():

    print("================================")
    print("      ASTRA MEMORY TESTS")
    print("================================")

    test_remember_and_recall()
    test_categories()
    test_forget()
    test_sensitive_rejection()
    test_pruning()
    test_summarize()
    test_persistence()
    test_disabled()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()