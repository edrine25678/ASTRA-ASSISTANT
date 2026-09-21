"""
Unit tests for AstraTaskEngine (core/task_engine.py): lifecycle,
confirmation gate, retries, replanning, follow-ups and cancellation.

Tool execution is stubbed with a scripted fake registry so nothing
is launched or modified on the real machine.

Run from the project root:

    python tests/test_task_engine.py
    (or: .venv/Scripts/python.exe tests/test_task_engine.py)
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.confirmation import ConfirmationManager
from core.task_engine import AstraTaskEngine, TaskState, TaskStep
from memory.context import ConversationContext
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


class FakeRegistry:

    def __init__(self, script=None):
        self.script = list(script or [])
        self.calls = []

    def execute(self, call):
        self.calls.append(call)

        if self.script:
            result = self.script.pop(0)
        else:
            result = ToolResult(success=True, response="Done.", data={})

        result.tool = call.name

        return result


class FakePlanner:

    def __init__(self, steps=None, replacement=None):
        self.steps = steps or []
        self.replacement = replacement

    def plan(self, goal):
        result = []

        for step in self.steps:

            if isinstance(step, str):
                result.append(
                    TaskStep(description=step, kind="tool", tool=step)
                )
            else:
                result.append(step)

        return result

    def replan(self, task, failed_step, observation):
        return self.replacement


def _engine(registry, planner, memory=None):

    return AstraTaskEngine(
        registry=registry,
        planner=planner,
        confirmation=ConfirmationManager(),
        memory=memory,
        context=ConversationContext(),
    )


def _step(tool, description="do something"):

    return TaskStep(description=description, kind="tool", tool=tool)


def test_completes_single_step():

    print()
    print("--- SINGLE STEP ---")

    registry = FakeRegistry([
        ToolResult(success=True, response="The current time is 12:00."),
    ])

    engine = _engine(registry, FakePlanner(steps=["get_time"]))

    response = engine.start_new("tell me the time")

    _check("completed response", response,
           "Done. The current time is 12:00.")
    _check("status completed", engine.current_task.status,
           TaskState.COMPLETED)
    _check("tool called", registry.calls[0].name, "get_time")


def test_confirmation_gate_round_trip():

    print()
    print("--- CONFIRMATION GATE ---")

    registry = FakeRegistry([
        ToolResult(success=True, response="Deleted notes.txt."),
    ])

    engine = _engine(registry, FakePlanner(steps=["file_delete"]))

    response = engine.start_new("delete notes.txt")

    _check("confirmation asked", "Are you sure you want me to" in response,
           True)
    _check("status waiting", engine.current_task.status,
           TaskState.WAITING_FOR_USER)
    _check("tool not yet called", len(registry.calls), 0)

    response = engine.continue_with_input("yes")

    _check("confirmed response", response, "Done. Deleted notes.txt.")
    _check("confirmed status", engine.current_task.status,
           TaskState.COMPLETED)
    _check("tool called once", len(registry.calls), 1)


def test_confirmation_declined():

    print()
    print("--- CONFIRMATION DECLINED ---")

    registry = FakeRegistry()

    engine = _engine(registry, FakePlanner(steps=["file_delete"]))

    engine.start_new("delete notes.txt")

    response = engine.continue_with_input("no")

    _check("declined completes", "skipped 1 step" in response, True)
    _check("no tool call", len(registry.calls), 0)


def test_unclear_confirmation_keeps_waiting():

    print()
    print("--- UNCLEAR CONFIRMATION ---")

    registry = FakeRegistry()

    engine = _engine(registry, FakePlanner(steps=["file_delete"]))

    engine.start_new("delete notes.txt")

    question = engine.continue_with_input("maybe")

    _check("re-asks question", question, engine.current_task.pending_question)
    _check("still waiting", engine.current_task.status,
           TaskState.WAITING_FOR_USER)
    _check("still no tool call", len(registry.calls), 0)


def test_cancel():

    print()
    print("--- CANCEL ---")

    registry = FakeRegistry()

    engine = _engine(registry, FakePlanner(steps=["file_delete"]))

    engine.start_new("delete notes.txt")

    response = engine.cancel()

    _check("cancel response", response, "Okay, I stopped the task.")
    _check("cancelled status", engine.current_task.status,
           TaskState.CANCELLED)

    response = engine.cancel()

    _check("second cancel controlled", response,
           "There's no active task to stop.")


def test_status():

    print()
    print("--- STATUS ---")

    registry = FakeRegistry()

    engine = _engine(registry, FakePlanner(steps=["file_delete"]))

    _check("no task status", engine.status_description(),
           "I'm not working on anything right now.")

    engine.start_new("delete notes.txt")

    _check("waiting status", engine.status_description(),
           engine.current_task.pending_question)

    engine.cancel()

    _check("cancelled status", engine.status_description(),
           "The last task was cancelled: delete notes.txt.")


def test_transient_retry_then_success():

    print()
    print("--- TRANSIENT RETRY ---")

    registry = FakeRegistry([
        ToolResult(success=False, error="Connection timed out."),
        ToolResult(success=True, response="The current time is 12:00."),
    ])

    engine = _engine(registry, FakePlanner(steps=["get_time"]))

    response = engine.start_new("tell me the time")

    _check("retried and completed", response,
           "Done. The current time is 12:00.")
    _check("status completed", engine.current_task.status,
           TaskState.COMPLETED)
    _check("retried once", engine.current_task.current_step() is None, True)


def test_transient_exhaustion():

    print()
    print("--- TRANSIENT EXHAUSTION ---")

    registry = FakeRegistry([
        ToolResult(success=False, error="Connection timed out."),
        ToolResult(success=False, error="Connection timed out."),
        ToolResult(success=False, error="Connection timed out."),
    ])

    engine = _engine(registry, FakePlanner(steps=["get_time"]))

    response = engine.start_new("tell me the time")

    _check("failed after retries", response.startswith(
        "I couldn't finish that task."), True)
    _check("status failed", engine.current_task.status, TaskState.FAILED)
    _check("attempts", len(registry.calls), 3)


def test_replan_recovers():

    print()
    print("--- REPLAN ---")

    registry = FakeRegistry([
        ToolResult(success=False, error="boom"),
        ToolResult(success=True, response="Today is a good day."),
    ])

    planner = FakePlanner(steps=["get_time"])
    planner.replacement = [TaskStep(description="fallback",
                                    kind="tool", tool="get_date")]

    engine = _engine(registry, planner)

    response = engine.start_new("tell me the time")

    _check("replanned and completed", response,
           "Done. Today is a good day.")
    _check("status completed", engine.current_task.status,
           TaskState.COMPLETED)
    _check("fallback used",
           registry.calls[1].name, "get_date")


def test_tool_denied():

    print()
    print("--- TOOL DENIED ---")

    registry = FakeRegistry([
        ToolResult(success=False, denied=True,
                   response="That action is not permitted."),
    ])

    engine = _engine(registry, FakePlanner(steps=["get_time"]))

    response = engine.start_new("tell me the time")

    _check("denied controlled", "That action is not permitted." in response,
           True)
    _check("status failed", engine.current_task.status, TaskState.FAILED)


def test_follow_up_no_results():

    print()
    print("--- FOLLOW-UP WITHOUT RESULTS ---")

    registry = FakeRegistry()

    step = TaskStep(description="open the first one",
                    kind="follow_up", arguments={"index": 0})

    planner = FakePlanner()
    planner.steps = [step]

    engine = _engine(registry, planner)

    response = engine.start_new("open the first one")

    _check("honest failure", "I can't do that yet" in response, True)
    _check("status failed", engine.current_task.status, TaskState.FAILED)


def test_follow_up_with_captured_results():

    print()
    print("--- FOLLOW-UP WITH RESULTS ---")

    registry = FakeRegistry([
        ToolResult(success=True, response="I found 2 matching file(s).",
                   data={"files": ["C:\\tmp\\notes.txt",
                                   "C:\\tmp\\report.txt"]}),
        ToolResult(success=True, response="Opening notes.txt."),
    ])

    planner = FakePlanner()
    planner.steps = [
        TaskStep(description="find my files", kind="tool",
                 tool="file_search"),
        TaskStep(description="open the first one",
                 kind="follow_up", arguments={"index": 0}),
    ]

    engine = _engine(registry, planner)

    response = engine.start_new("find my files then open the first one")

    _check("follow-up completed", response,
           "Done. I found 2 matching file(s). Opening notes.txt.")
    _check("status completed", engine.current_task.status,
           TaskState.COMPLETED)
    _check("opened captured", registry.calls[1].name, "file_open_file")
    _check("opened path", registry.calls[1].arguments["path"],
           "C:\\tmp\\notes.txt")


def test_follow_up_ask_selection():

    print()
    print("--- FOLLOW-UP ASK ---")

    registry = FakeRegistry([
        ToolResult(success=True, response="I found 2 matching file(s).",
                   data={"files": ["C:\\tmp\\notes.txt",
                                   "C:\\tmp\\report.txt"]}),
        ToolResult(success=True, response="Opening report.txt."),
    ])

    planner = FakePlanner()
    planner.steps = [
        TaskStep(description="find my files", kind="tool",
                 tool="file_search"),
        TaskStep(description="open the first one",
                 kind="follow_up", arguments={"index": None}),
    ]

    engine = _engine(registry, planner)

    response = engine.start_new("find my files then open the first one")

    _check("selection asked", "Which one should I use?" in response, True)
    _check("waiting", engine.current_task.status,
           TaskState.WAITING_FOR_USER)

    response = engine.continue_with_input("the second one")

    _check("selection completed", response,
           "Done. I found 2 matching file(s). Opening report.txt.")
    _check("opened second", registry.calls[1].arguments["path"],
           "C:\\tmp\\report.txt")


def test_parse_ordinal():

    print()
    print("--- PARSE ORDINAL ---")

    _check("first", AstraTaskEngine._parse_ordinal("the first one"), 0)
    _check("second", AstraTaskEngine._parse_ordinal("the second"), 1)
    _check("third", AstraTaskEngine._parse_ordinal("third"), 2)
    _check("last", AstraTaskEngine._parse_ordinal("the last one"), "last")
    _check("bare one", AstraTaskEngine._parse_ordinal("one"), 0)
    _check("bare two", AstraTaskEngine._parse_ordinal("two"), 1)
    _check("the third one", AstraTaskEngine._parse_ordinal("the third one"), 2)
    _check("none", AstraTaskEngine._parse_ordinal("whatever"), None)


def test_unplannable_goal():

    print()
    print("--- UNPLANNABLE GOAL ---")

    registry = FakeRegistry()

    engine = _engine(registry, FakePlanner())

    response = engine.start_new("dance for me")

    _check("controlled plan failure",
           "I couldn't plan that task" in response, True)
    _check("failed status", engine.current_task.status, TaskState.FAILED)


def main():

    print("================================")
    print("     ASTRA TASK ENGINE TESTS")
    print("================================")

    test_completes_single_step()
    test_confirmation_gate_round_trip()
    test_confirmation_declined()
    test_unclear_confirmation_keeps_waiting()
    test_cancel()
    test_status()
    test_transient_retry_then_success()
    test_transient_exhaustion()
    test_replan_recovers()
    test_tool_denied()
    test_follow_up_no_results()
    test_follow_up_with_captured_results()
    test_follow_up_ask_selection()
    test_parse_ordinal()
    test_unplannable_goal()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()