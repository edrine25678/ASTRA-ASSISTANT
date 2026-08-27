"""
Unit tests for ConfirmationManager (core/confirmation.py):
risk levels and the confirmation gate.

Run from the project root:

    python tests/test_confirmation.py
    (or: .venv/Scripts/python.exe tests/test_confirmation.py)
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.confirmation import ConfirmationManager, RiskLevels

from tools.base import ToolCall

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


def test_risk_levels():

    print()
    print("--- RISK LEVELS ---")

    manager = ConfirmationManager()

    _check("get_time is low", manager.risk_of(ToolCall("get_time", {})),
           RiskLevels.LOW)

    _check("open_application is low",
           manager.risk_of(ToolCall("open_application", {})),
           RiskLevels.LOW)

    _check("file_search is low",
           manager.risk_of(ToolCall("file_search", {})),
           RiskLevels.LOW)

    _check("file_create_text is medium",
           manager.risk_of(ToolCall("file_create_text", {})),
           RiskLevels.MEDIUM)

    _check("file_delete is high",
           manager.risk_of(ToolCall("file_delete", {})),
           RiskLevels.HIGH)

    _check("unknown tool is high",
           manager.risk_of(ToolCall("mystery_tool", {})),
           RiskLevels.HIGH)

    _check("non-call is high", manager.risk_of("not a call"),
           RiskLevels.HIGH)


def test_confirmation_gate():

    print()
    print("--- CONFIRMATION GATE ---")

    manager = ConfirmationManager()

    _check("low risk runs", manager.needs_confirmation(ToolCall("get_time", {})),
           False)

    _check("medium risk asks",
           manager.needs_confirmation(ToolCall("file_create_text", {})),
           True)

    _check("high risk asks",
           manager.needs_confirmation(ToolCall("file_delete", {})),
           True)

    _check("unknown tool asks",
           manager.needs_confirmation(ToolCall("mystery_tool", {})),
           True)


def test_custom_threshold():

    print()
    print("--- CUSTOM THRESHOLD ---")

    strict = ConfirmationManager(ask_from=RiskLevels.HIGH)

    _check("medium below threshold",
           strict.needs_confirmation(ToolCall("file_create_text", {})),
           False)

    _check("high at threshold",
           strict.needs_confirmation(ToolCall("file_delete", {})),
           True)


def test_describe():

    print()
    print("--- DESCRIBE ---")

    manager = ConfirmationManager()

    _check(
        "describe includes tool and risk",
        manager.describe(ToolCall("file_delete", {})),
        "file_delete (high risk)",
    )


def main():

    print("================================")
    print("   ASTRA CONFIRMATION TESTS")
    print("================================")

    test_risk_levels()
    test_confirmation_gate()
    test_custom_threshold()
    test_describe()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()