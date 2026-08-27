"""
Unit tests for AstraPlanner (core/planner.py): goal -> plan.

Run from the project root:

    python tests/test_planner.py
    (or: .venv/Scripts/python.exe tests/test_planner.py)

These tests never execute any tool; they only inspect the plan.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.planner import AstraPlanner
from core.task_engine import TaskStep

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


PLANNER = AstraPlanner()


def _plan_ok(goal):
    """A goal must produce at least one step."""

    steps = PLANNER.plan(goal)

    return _check(f"plan({goal!r}) non-empty", bool(steps), True)


def test_multi_step_plans():

    print()
    print("--- MULTI-STEP PLANS ---")

    steps = PLANNER.plan("open chrome and open youtube")

    _check("two steps", len(steps), 2)
    _check("step 1 tool", steps[0].tool, "open_application")
    _check("step 1 args", steps[0].arguments, {"application": "chrome"})
    _check("step 2 tool", steps[1].tool, "open_url")
    _check("step 2 args", steps[1].arguments, {"url": "youtube"})

    steps = PLANNER.plan("open notepad and calculator")

    _check("verb group steps", len(steps), 2)
    _check("verb group 1", steps[0].tool, "open_application")
    _check("verb group 1 arg", steps[0].arguments["application"], "notepad")
    _check("verb group 2 arg", steps[1].arguments["application"], "calculator")

    steps = PLANNER.plan("open chrome then search for python tutorials")

    _check("then-chain steps", len(steps), 2)
    _check("then step 1", steps[0].tool, "open_application")
    _check("then step 2", steps[1].tool, "search_web")
    _check("then step 2 engine", steps[1].arguments["engine"], "google")

    for step in steps:
        _check(f"step {step.tool} has description", bool(step.description), True)


def test_single_step_plans():

    print()
    print("--- SINGLE-STEP PLANS ---")

    _plan_ok("open chrome")

    steps = PLANNER.plan("find my python files")

    _check("file search step", steps[0].tool, "file_search")
    _check("python extension", steps[0].arguments["extensions"], [".py"])

    steps = PLANNER.plan("what time is it")

    _check("time step", steps[0].tool, "get_time")

    steps = PLANNER.plan("what is python")

    _check("knowledge step", steps[0].tool, "knowledge")
    _check("knowledge query", steps[0].arguments["query"], "python")


def test_follow_up_plan():

    print()
    print("--- FOLLOW-UP PLAN ---")

    steps = PLANNER.plan("open the first one")

    _check("follow-up step kind", steps[0].kind, "follow_up")
    _check("follow-up index", steps[0].arguments.get("index"), 0)


def test_unplannable_goals():

    print()
    print("--- UNPLANNABLE GOALS ---")

    _check("empty goal", PLANNER.plan(""), [])
    _check("gibberish goal", PLANNER.plan("dance for me"), [])


def test_replan_returns_none():

    print()
    print("--- REPLAN ---")

    step = TaskStep(description="x", kind="tool", tool="get_time")

    _check("replan default", PLANNER.replan(None, step, ""), None)


def main():

    print("================================")
    print("     ASTRA PLANNER TESTS")
    print("================================")

    test_multi_step_plans()
    test_single_step_plans()
    test_follow_up_plan()
    test_unplannable_goals()
    test_replan_returns_none()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()