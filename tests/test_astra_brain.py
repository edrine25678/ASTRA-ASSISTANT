"""
Integration tests for AstraBrain (core/brain.py): conversation,
tool selection, response variation, follow-up search, memory,
confirmation flow, knowledge fallback and exit handling.

Run from the project root:

    python tests/test_astra_brain.py
    (or: .venv/Scripts/python.exe tests/test_astra_brain.py)

Note: app/browser commands really launch applications and open
the browser.
"""

import os
import sys
import tempfile
from typing import ClassVar

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from ai.intent import SYSTEM_QUERY, Intent
from ai.provider import AIProviderError
from core.brain import AstraBrain
from tools.base import AstraTool, ToolCall, ToolResult
from tools.safety import ToolSafety

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


# ==============================================
# TEST DOUBLES
# ==============================================

class AllowAllSafety(ToolSafety):
    ALLOWED_TOOLS: ClassVar[set] = {
        "open_application",
        "open_url",
        "search_web",
        "get_time",
        "get_date",
        "system_info",
        "file_search",
        "file_list_directory",
        "file_open_file",
        "file_open_folder",
        "file_read_text",
        "file_create_text",
        "file_delete",
        "confirm_me",
    }


class ConfirmationTool(AstraTool):

    name = "confirm_me"
    description = "Test tool that always asks for confirmation"
    parameters: ClassVar[dict] = {"value": {"type": "str", "required": True}}
    requires_confirmation = True

    def run(self, arguments):
        return ToolResult(
            success=True,
            response=f"Done {arguments['value']}.",
        )


class ConfirmationPlanner:

    def plan(self, text):
        return Intent(
            type=SYSTEM_QUERY,
            tool_call=ToolCall("confirm_me", {"value": "42"}),
            raw_text=text,
        )


class FailingProvider:

    name = "failing"

    def available(self):
        return True

    def generate(self, messages):
        raise AIProviderError("boom")

    def close(self):
        pass


def _memory_path():
    return os.path.join(tempfile.mkdtemp(), "brain.db")


def _brain(planner=None, provider=None, memory=True):

    from tools import build_default_registry

    registry = build_default_registry(safety=AllowAllSafety())
    registry.register(ConfirmationTool())

    return AstraBrain(
        planner=planner,
        registry=registry,
        provider=provider,
        memory_enabled=memory,
        memory_path=_memory_path(),
    )


# ==============================================
# TESTS
# ==============================================

def test_conversation():

    print()
    print("--- CONVERSATION ---")

    brain = _brain()

    _check(
        "greeting",
        brain.process("hello astra").response,
        "Hello Edrine. How can I help you?",
    )

    _check(
        "how are you",
        brain.process("how are you").response,
        "I'm doing great, Edrine. I'm ready to help.",
    )

    _check(
        "thanks",
        brain.process("thank you").response,
        "You're welcome, Edrine.",
    )

    _check(
        "tired",
        brain.process("i am tired").response,
        "Then you should get some rest, Edrine. "
        "I'll be here when you need me.",
    )

    _check(
        "love",
        brain.process("i love you").response,
        "That's very kind of you, Edrine. "
        "I'm here whenever you need me.",
    )

    _check(
        "empty",
        brain.process("").response,
        "I didn't catch that.",
    )

    _check(
        "unknown",
        brain.process("dance for me").response,
        "I don't know how to do that yet.",
    )


def test_app_open_variation():

    print()
    print("--- RESPONSE VARIATION ---")

    brain = _brain()

    result = brain.process("open chrome")

    variants = {
        "Sure. Opening Chrome.",
        "Got it. Launching Chrome now.",
        "Chrome is open.",
    }

    _check("chrome response varied", result.response in variants, True)
    _check("chrome not exit", result.exit, False)


def test_system_queries_passthrough():

    print()
    print("--- SYSTEM QUERIES ---")

    brain = _brain()

    result = brain.process("what time is it")

    _check(
        "time starts correctly",
        result.response.startswith("The current time is"),
        True,
    )

    result = brain.process("what's today's date")

    _check(
        "date starts correctly",
        result.response.startswith("Today is"),
        True,
    )


def test_follow_up_search_uses_last_site():

    print()
    print("--- FOLLOW-UP SEARCH ---")

    brain = _brain()

    result = brain.process("open youtube")

    _check("open youtube", result.response, "Opening YouTube.")

    result = brain.process("search for python tutorials")

    _check(
        "follow-up search on youtube",
        result.response,
        "Searching youtube for python tutorials.",
    )


def test_memory_through_brain():

    print()
    print("--- MEMORY THROUGH BRAIN ---")

    brain = _brain()

    result = brain.process("remember that i like dark mode")

    _check("remembered", result.response, "Remembered.")

    result = brain.process("what do you remember about dark mode")

    _check(
        "recalled",
        result.response.startswith(
            "Here's what I remember: i like dark mode"
        ),
        True,
    )

    result = brain.process(
        "remember that my password is hunter2"
    )

    _check(
        "sensitive rejected",
        result.response,
        "I will not store sensitive information like that.",
    )

    result = brain.process("what do you remember about hunter2")

    _check("sensitive never stored", "password" in result.response, False)


def test_knowledge_fallback():

    print()
    print("--- KNOWLEDGE FALLBACK ---")

    brain = _brain(provider=None)

    result = brain.process("what is python")

    _check(
        "knowledge fallback message",
        result.response,
        brain.KNOWLEDGE_FALLBACK,
    )

    brain = _brain(provider=FailingProvider())

    result = brain.process("why is the sky blue")

    _check(
        "failing provider controlled",
        result.response,
        brain.KNOWLEDGE_FALLBACK,
    )


class EchoProvider:

    name = "echo"

    def available(self):
        return True

    def generate(self, messages):
        return "Knowledge answer."

    def close(self):
        pass


def test_knowledge_with_provider():

    print()
    print("--- KNOWLEDGE WITH PROVIDER ---")

    brain = _brain(provider=EchoProvider())

    result = brain.process("what is python")

    _check(
        "provider answer used",
        result.response,
        "Knowledge answer.",
    )


def test_confirmation_flow():

    print()
    print("--- CONFIRMATION FLOW ---")

    brain = _brain(planner=ConfirmationPlanner())

    first = brain.process("do it")

    _check(
        "asks for confirmation",
        first.response,
        "Are you sure you want me to do that?",
    )

    second = brain.process("yes")

    _check("confirmed action runs", second.response, "Done 42.")

    first = brain.process("do it")

    _check("asks again", first.response, "Are you sure you want me to do that?")

    declined = brain.process("no")

    _check("declined", declined.response, "Okay, I won't do that.")

    first = brain.process("do it")

    _check("asks again after decline", first.response,
           "Are you sure you want me to do that?")


def test_exit():

    print()
    print("--- EXIT ---")

    brain = _brain()

    result = brain.process("exit astra")

    _check("exit response", result.response, "Goodbye Edrine.")
    _check("exit flag", result.exit, True)


def test_task_through_brain():

    print()
    print("--- TASK THROUGH BRAIN ---")

    brain = _brain()

    result = brain.process("open chrome and open youtube")

    _check(
        "task completes",
        result.response,
        "Done. Opening Chrome. Opening YouTube.",
    )
    _check("task not exit", result.exit, False)

    result = brain.process("what are you doing")

    _check(
        "task status after completion",
        result.response,
        "The last task is finished: open chrome and open youtube.",
    )

    result = brain.process("what did i just ask you")

    _check(
        "task recall from memory",
        result.response.startswith(
            "Recently: Task (completed): open chrome and open youtube"
        ),
        True,
    )


def test_task_cancel_through_brain():

    print()
    print("--- TASK CANCEL THROUGH BRAIN ---")

    brain = _brain()

    # A task whose first step requires confirmation pauses and asks.
    result = brain.process("write down meeting at three and open chrome")

    _check(
        "task asks for approval",
        result.response.startswith(
            "Are you sure you want me to write down meeting at three?"
        ),
        True,
    )

    result = brain.process("cancel that")

    _check("task cancelled", result.response, "Okay, I stopped the task.")

    result = brain.process("what are you doing")

    _check(
        "cancelled status",
        result.response,
        "The last task was cancelled: write down meeting at three and open chrome.",
    )


def test_single_command_file_confirmation():

    print()
    print("--- SINGLE FILE COMMAND CONFIRMATION ---")

    brain = _brain()

    result = brain.process("write down hello world")

    _check(
        "file create asks first",
        result.response,
        "Are you sure you want me to do that?",
    )

    result = brain.process("no")

    _check("file create declined", result.response, "Okay, I won't do that.")


def test_honest_follow_up_after_search_task():

    print()
    print("--- HONEST FOLLOW-UP AFTER SEARCH ---")

    brain = _brain()

    brain.process("open chrome and search for python tutorials")

    result = brain.process("the first one")

    _check(
        "follow-up cannot read results",
        result.response,
        "I opened the search page, but I can't read the results yet.",
    )


def test_clarification_ack():

    print()
    print("--- CLARIFICATION ACK ---")

    brain = _brain()

    _check("yes ack", brain.process("yes").response, "Okay.")
    _check("no ack", brain.process("no").response, "Alright.")


def test_memory_relevance_answer():

    print()
    print("--- MEMORY RELEVANCE ---")

    brain = _brain(provider=None)

    brain.process("remember that i prefer dark mode for astra")

    result = brain.process("how does dark mode work")

    _check(
        "knowledge answered from memory",
        result.response,
        "You prefer dark mode for astra.",
    )


def main():

    print("================================")
    print("    ASTRA BRAIN ORCHESTRATOR")
    print("================================")

    test_conversation()
    test_app_open_variation()
    test_system_queries_passthrough()
    test_follow_up_search_uses_last_site()
    test_memory_through_brain()
    test_knowledge_fallback()
    test_knowledge_with_provider()
    test_confirmation_flow()
    test_exit()
    test_task_through_brain()
    test_task_cancel_through_brain()
    test_single_command_file_confirmation()
    test_honest_follow_up_after_search_task()
    test_clarification_ack()
    test_memory_relevance_answer()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()