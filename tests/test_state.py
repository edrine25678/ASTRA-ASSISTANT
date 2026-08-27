"""
Tests for the conversation state machine (core/state.py).

Run from the project root:

    python tests/test_state.py
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.state import (
    CONVERSATION,
    EXECUTING,
    IDLE,
    LISTENING_FOR_COMMAND,
    LISTENING_FOR_WAKE_WORD,
    RESPONDING,
    AstraState,
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


def test_full_conversation_flow():

    print()
    print("--- FULL CONVERSATION FLOW ---")

    state = AstraState()

    _check("starts idle", state.current, IDLE)

    _check(
        "idle -> wake word",
        state.transition(LISTENING_FOR_WAKE_WORD),
        True,
    )

    _check(
        "wake word -> command",
        state.transition(LISTENING_FOR_COMMAND),
        True,
    )

    _check(
        "command -> executing",
        state.transition(EXECUTING),
        True,
    )

    _check(
        "executing -> responding",
        state.transition(RESPONDING),
        True,
    )

    _check(
        "responding -> conversation",
        state.transition(CONVERSATION),
        True,
    )

    _check_true = None  # placeholder, unused

    _check("conversing", state.is_conversing(), True)


def test_invalid_transitions_rejected():

    print()
    print("--- INVALID TRANSITIONS ---")

    state = AstraState()

    _check(
        "idle -> executing rejected",
        state.transition(EXECUTING),
        False,
    )

    _check("state unchanged", state.current, IDLE)

    _check(
        "idle -> responding rejected",
        state.transition(RESPONDING),
        False,
    )

    state.transition(LISTENING_FOR_WAKE_WORD)

    _check(
        "wake word -> conversation rejected",
        state.transition(CONVERSATION),
        False,
    )

    _check(
        "wake word state kept",
        state.current,
        LISTENING_FOR_WAKE_WORD,
    )


def test_conversation_timeout_returns_to_wake_word():

    print()
    print("--- CONVERSATION TIMEOUT ---")

    state = AstraState()

    state.transition(LISTENING_FOR_WAKE_WORD)
    state.transition(LISTENING_FOR_COMMAND)
    state.transition(EXECUTING)
    state.transition(RESPONDING)
    state.transition(CONVERSATION)

    _check(
        "conversation -> wake word",
        state.transition(LISTENING_FOR_WAKE_WORD),
        True,
    )

    _check(
        "waiting for wake word",
        state.is_waiting_for_wake_word(),
        True,
    )

    state.transition(IDLE)

    _check("conversation -> idle", state.current, IDLE)


def main():

    print("================================")
    print("       STATE MACHINE")
    print("================================")

    test_full_conversation_flow()
    test_invalid_transitions_rejected()
    test_conversation_timeout_returns_to_wake_word()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()