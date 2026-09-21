"""
Unit tests for AstraObserver (core/observer.py): result interpretation.

Run from the project root:

    python tests/test_observer.py
    (or: .venv/Scripts/python.exe tests/test_observer.py)
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.observer import AstraObserver
from tools.base import ToolResult

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


OBSERVER = AstraObserver()


def test_success():

    print()
    print("--- SUCCESS ---")

    result = ToolResult(success=True, tool="get_time", response="The current time is 12:00.")

    observation = OBSERVER.interpret(result)

    _check("success uses response", observation, "The current time is 12:00.")

    result = ToolResult(success=True, tool="get_time", response="")

    observation = OBSERVER.interpret(result)

    _check("success fallback", observation, "get_time succeeded.")

    structured = OBSERVER.observe(result)

    _check("structured success", structured["success"], True)
    _check("structured tool", structured["tool"], "get_time")


def test_failure():

    print()
    print("--- FAILURE ---")

    result = ToolResult(success=False, tool="file_search", response="I couldn't find any matching files.")

    observation = OBSERVER.interpret(result)

    _check("failure uses response", observation, "I couldn't find any matching files.")

    result = ToolResult(success=False, tool="file_search", response="")

    observation = OBSERVER.interpret(result)

    _check("failure fallback", observation, "file_search failed.")

    _check("structured failure", OBSERVER.observe(result)["success"], False)


def test_denied_and_confirmation():

    print()
    print("--- DENIED / CONFIRMATION ---")

    result = ToolResult(success=False, denied=True, tool="file_delete",
                        response="That action is not permitted.")

    observation = OBSERVER.interpret(result)

    _check("denied uses response", observation, "That action is not permitted.")

    result = ToolResult(success=False, needs_confirmation=True, tool="file_delete",
                        response="")

    observation = OBSERVER.interpret(result)

    _check("confirmation fallback", observation, "Confirmation requested.")


def main():

    print("================================")
    print("      ASTRA OBSERVER TESTS")
    print("================================")

    test_success()
    test_failure()
    test_denied_and_confirmation()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()