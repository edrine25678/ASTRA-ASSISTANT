"""
Integration tests for the AI brain + tool pipeline: intent types,
tool selection, natural-language variations and backward
compatibility with every existing command.

Run from the project root:

    python tests/test_brain.py
    (or: .venv/Scripts/python.exe tests/test_brain.py)

Note: app/browser commands really launch the applications.
"""

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from ai.brain import AIBrain
from ai.intent import (
    APPLICATION_ACTION,
    BROWSER_ACTION,
    CLARIFICATION,
    CONVERSATION,
    EXIT,
    FILE_ACTION,
    FOLLOW_UP,
    MEMORY_ACTION,
    SYSTEM_QUERY,
    TASK,
    TASK_CONTROL,
    UNKNOWN,
)
from tools import build_default_registry

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


BRAIN = AIBrain()
REGISTRY = build_default_registry()


def _run(text):
    """Full pipeline: brain -> tools.  Returns (intent, response)."""

    intent = BRAIN.process(text)

    if intent.type == EXIT:
        return intent, "__EXIT__"

    if intent.tool_call is not None:

        result = REGISTRY.execute(intent.tool_call)

        return intent, result.response

    return intent, intent.response or "I don't know how to do that yet."


def _expect(text, expected_type, expected_response):
    """Run the pipeline and assert type and response."""

    intent, response = _run(text)

    _check(f"type({text!r})", intent.type, expected_type)
    _check(f"response({text!r})", response, expected_response)


def _expect_startswith(text, expected_type, prefix):

    intent, response = _run(text)

    _check(f"type({text!r})", intent.type, expected_type)
    _check(
        f"response({text!r}) starts with {prefix!r}",
        response.startswith(prefix),
        True,
    )


def test_existing_commands():

    print()
    print("--- EXISTING COMMANDS ---")

    _expect("open chrome", APPLICATION_ACTION, "Opening Chrome.")
    _expect("open youtube", BROWSER_ACTION, "Opening YouTube.")
    _expect("open notepad", APPLICATION_ACTION, "Opening Notepad.")
    _expect("open calculator", APPLICATION_ACTION, "Opening Calculator.")
    _expect("open file explorer", APPLICATION_ACTION, "Opening File Explorer.")
    _expect("open vs code", APPLICATION_ACTION, "Opening Visual Studio Code.")
    _expect("open google", BROWSER_ACTION, "Opening Google.")
    _expect("open gmail", BROWSER_ACTION, "Opening Gmail.")
    _expect("open chatgpt", BROWSER_ACTION, "Opening ChatGPT.")
    _expect_startswith("what time is it", SYSTEM_QUERY, "The current time is")
    _expect_startswith("what's today's date", SYSTEM_QUERY, "Today is")
    _expect("hello astra", CONVERSATION, "Hello Edrine. How can I help you?")
    _expect("how are you", CONVERSATION, "I'm doing great, Edrine. I'm ready to help.")
    _expect("thank you", CONVERSATION, "You're welcome, Edrine.")
    _expect("exit astra", EXIT, "__EXIT__")


def test_natural_variations():

    print()
    print("--- NATURAL VARIATIONS ---")

    _expect("could you open chrome for me", APPLICATION_ACTION, "Opening Chrome.")
    _expect("please launch chrome", APPLICATION_ACTION, "Opening Chrome.")
    _expect("can you start notepad", APPLICATION_ACTION, "Opening Notepad.")
    _expect("i need the calculator", APPLICATION_ACTION, "Opening Calculator.")
    _expect("take me to youtube", BROWSER_ACTION, "Opening YouTube.")
    _expect_startswith("what time is it right now", SYSTEM_QUERY, "The current time is")
    _expect("hi astra", CONVERSATION, "Hello Edrine. How can I help you?")
    _expect("astra start my browser", APPLICATION_ACTION, "Opening Chrome.")
    _expect("open github.com", BROWSER_ACTION, "Opening github.com.")
    _expect("search google for distributed systems", BROWSER_ACTION,
            "Searching google for distributed systems.")
    _expect("search for python tutorials", BROWSER_ACTION,
            "Searching google for python tutorials.")


def test_system_queries():

    print()
    print("--- SYSTEM QUERIES ---")

    _, response = _run("what operating system am i using")
    _check("os query has response", response.startswith("You are running"), True)

    _, response = _run("how much ram do i have")
    _check("memory query has response", "GB of RAM" in response, True)

    _, response = _run("what processor do i have")
    _check("cpu query has response", response.startswith("Your processor"), True)

    _, response = _run("how much disk space is available")
    _check("disk query has response", "GB free" in response, True)

    _, response = _run("what applications are running")
    _check("processes query has response", response.startswith("The main running"), True)


def test_tool_selection():

    print()
    print("--- TOOL SELECTION ---")

    intent, _ = _run("open chrome")
    _check("chrome -> open_application", intent.tool_call.name, "open_application")

    intent, _ = _run("what time is it")
    _check("time -> get_time", intent.tool_call.name, "get_time")

    intent, _ = _run("search google for distributed systems")
    _check("search -> search_web", intent.tool_call.name, "search_web")

    intent, _ = _run("open youtube")
    _check("youtube -> open_url", intent.tool_call.name, "open_url")

    intent, _ = _run("how much ram do i have")
    _check("ram -> system_info", intent.tool_call.name, "system_info")

    _, response = _run("open fortnite")
    _check("unavailable tool -> controlled response",
           response, "I couldn't find an application called fortnite.")


def test_conversation_vs_action():

    print()
    print("--- CONVERSATION VS ACTION ---")

    intent, _ = _run("hello astra")
    _check("greeting is conversation", intent.type, CONVERSATION)
    _check("greeting has no tool", intent.tool_call, None)

    intent, _ = _run("how are you")
    _check("how are you is conversation", intent.type, CONVERSATION)

    intent, _ = _run("open chrome")
    _check("open chrome is an action", intent.type, APPLICATION_ACTION)

    intent, _ = _run("what time is it")
    _check("time is a system query", intent.type, SYSTEM_QUERY)


def test_unknown_and_file():

    print()
    print("--- UNKNOWN AND FILE ---")

    _, response = _run("dance for me")
    _check("unknown -> controlled response",
           response, "I don't know how to do that yet.")

    _, response = _run("open fortnite")
    _check("unknown app -> controlled response",
           response, "I couldn't find an application called fortnite.")

    intent, response = _run("i want you to help me find a file")
    _check("file request -> FILE_ACTION", intent.type, FILE_ACTION)
    _check("file request has controlled response", bool(response), True)
    _check(
        "file request suggests real commands",
        response,
        "I can search for files. Try something like "
        "'find my python files' or 'show me files "
        "modified today'.",
    )

    intent, response = _run("")
    _check("empty text -> UNKNOWN", intent.type, UNKNOWN)
    _check("empty text controlled", response, "I don't know how to do that yet.")


def test_phase5_intents():

    print()
    print("--- PHASE 5 INTENTS ---")

    intent, _ = _run("open chrome and open youtube")
    _check("multi-step -> TASK", intent.type, TASK)

    intent, _ = _run("open notepad and calculator")
    _check("verb group -> TASK", intent.type, TASK)

    intent, _ = _run("cancel that")
    _check("cancel -> TASK_CONTROL", intent.type, TASK_CONTROL)
    _check("cancel action", intent.action, "cancel")

    intent, _ = _run("what are you doing")
    _check("status -> TASK_CONTROL", intent.type, TASK_CONTROL)
    _check("status action", intent.action, "status")

    intent, _ = _run("the first one")
    _check("follow-up -> FOLLOW_UP", intent.type, FOLLOW_UP)
    _check("follow-up index", intent.parameters.get("index"), 0)

    intent, _ = _run("open the last one")
    _check("last follow-up -> FOLLOW_UP", intent.type, FOLLOW_UP)
    _check("last index", intent.parameters.get("index"), "last")

    intent, _ = _run("yes")
    _check("yes -> CLARIFICATION", intent.type, CLARIFICATION)
    _check("yes action", intent.action, "yes")

    intent, _ = _run("no")
    _check("no -> CLARIFICATION", intent.type, CLARIFICATION)
    _check("no action", intent.action, "no")

    intent, _ = _run("what did i just ask you")
    _check("task recall -> MEMORY_ACTION", intent.type, MEMORY_ACTION)
    _check("task recall category", intent.parameters.get("category"), "tasks")


def test_phase5_file_planning():

    print()
    print("--- PHASE 5 FILE PLANNING ---")

    intent, _ = _run("find my python files")
    _check("find python -> file_search", intent.tool_call.name, "file_search")
    _check("python extension", intent.parameters["extensions"], [".py"])

    intent, _ = _run("show me files modified today")
    _check("modified today -> file_search", intent.tool_call.name, "file_search")
    _check("modified_since", intent.parameters["modified_since"], "today")

    intent, _ = _run("where are my downloads")
    _check("where -> file_list_directory",
           intent.tool_call.name, "file_list_directory")

    intent, _ = _run("open the astra folder")
    _check("open folder -> file_open_folder", intent.tool_call.name, "file_open_folder")

    intent, _ = _run("list the documents folder")
    _check("list folder -> file_list_directory",
           intent.tool_call.name, "file_list_directory")

    intent, _ = _run("write down python is cool")
    _check("write down -> file_create_text",
           intent.tool_call.name, "file_create_text")

    intent, _ = _run("delete C:\\temp\\notes.txt")
    _check("delete -> file_delete", intent.tool_call.name, "file_delete")


def test_phase5_system_usage():

    print()
    print("--- PHASE 5 SYSTEM USAGE ---")

    intent, _ = _run("how much battery is left")
    _check("battery -> battery topic",
           intent.parameters.get("topic"), "battery")

    intent, _ = _run("what is my cpu usage")
    _check("cpu usage -> cpu_usage topic",
           intent.parameters.get("topic"), "cpu_usage")

    intent, _ = _run("how much ram am i using")
    _check("memory usage -> memory_usage topic",
           intent.parameters.get("topic"), "memory_usage")

    intent, _ = _run("how much ram do i have")
    _check("total ram -> memory topic",
           intent.parameters.get("topic"), "memory")


def main():

    print("================================")
    print("       ASTRA BRAIN TESTS")
    print("================================")

    test_existing_commands()
    test_natural_variations()
    test_system_queries()
    test_tool_selection()
    test_conversation_vs_action()
    test_unknown_and_file()
    test_phase5_intents()
    test_phase5_file_planning()
    test_phase5_system_usage()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
