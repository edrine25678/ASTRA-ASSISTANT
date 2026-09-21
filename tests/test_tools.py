"""
Unit-style tests for the tool architecture: registration, safety,
validation, execution and error handling.

Run from the project root:

    python tests/test_tools.py
    (or: .venv/Scripts/python.exe tests/test_tools.py)

Note: valid tool calls really launch applications and open the
browser.
"""

import os
import sys
from typing import ClassVar

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from tools import ToolCall, build_default_registry
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


def test_discovery():

    print()
    print("--- TOOL DISCOVERY ---")

    registry = build_default_registry()

    tools = registry.discover()

    _check("registry has 13 tools", len(tools), 13)

    names = {tool["name"] for tool in tools}

    _check(
        "tool names",
        names,
        {
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
        },
    )

    for tool in tools:
        _check(
            f"tool {tool['name']} has description",
            bool(tool["description"]),
            True,
        )


def test_unknown_tool_is_controlled():

    print()
    print("--- UNKNOWN / DANGEROUS TOOLS ---")

    registry = build_default_registry()

    result = registry.execute(
        ToolCall("delete_files", {"path": "C:\\Windows"})
    )

    _check("unknown tool denied", result.denied, True)
    _check("unknown tool response", result.response, "I don't know how to do that yet.")

    result = registry.execute(ToolCall("format_drive", {}))

    _check("dangerous tool denied", result.denied, True)
    _check("dangerous tool response", result.response, "I don't know how to do that yet.")

    result = registry.execute("not a tool call")

    _check("invalid call denied", result.denied, True)


def test_safety_policy_denies():

    print()
    print("--- SAFETY POLICY ---")

    class StrictSafety(ToolSafety):
        ALLOWED_TOOLS: ClassVar[set] = {"get_time"}

    registry = build_default_registry(safety=StrictSafety())

    result = registry.execute(
        ToolCall("open_application", {"application": "notepad"})
    )

    _check("disallowed tool denied", result.denied, True)
    _check(
        "disallowed tool response",
        result.response,
        "That action is not permitted.",
    )

    result = registry.execute(ToolCall("get_time", {}))

    _check("allowed tool still runs", result.success, True)


def test_validation():

    print()
    print("--- ARGUMENT VALIDATION ---")

    registry = build_default_registry()

    result = registry.execute(
        ToolCall("open_application", {"application": "fortnite"})
    )

    _check("unknown application handled gracefully", result.success, False)
    _check(
        "unknown application response",
        result.response,
        "I couldn't find an application called fortnite.",
    )

    result = registry.execute(ToolCall("open_application", {}))

    _check("missing argument rejected", result.success, False)

    result = registry.execute(ToolCall("system_info", {"topic": "bogus"}))

    _check("unknown topic rejected", result.success, False)

    result = registry.execute(
        ToolCall("search_web", {"query": "python", "engine": "yahoo"})
    )

    _check("unknown engine rejected", result.success, False)

    result = registry.execute(ToolCall("open_url", {"url": "not a url"}))

    _check("unresolvable url rejected", result.success, False)


def test_application_discovery():

    print()
    print("--- APPLICATION DISCOVERY ---")

    registry = build_default_registry()

    tool = registry.get("open_application")

    launcher = tool.find_application("notepad")

    _check("notepad discoverable", launcher is not None, True)

    launcher = tool.find_application("xyz_not_a_real_app_123")

    _check("nonsense app not found", launcher, None)

    result = registry.execute(
        ToolCall("open_application", {"application": "xyz_not_a_real_app_123"})
    )

    _check("discovery failure controlled", result.success, False)
    _check(
        "discovery failure response",
        result.response,
        "I couldn't find an application called xyz_not_a_real_app_123.",
    )


def test_system_tools():

    print()
    print("--- SYSTEM TOOLS ---")

    registry = build_default_registry()

    result = registry.execute(ToolCall("get_time", {}))

    _check("get_time success", result.success, True)
    _check(
        "get_time response",
        result.response.startswith("The current time is"),
        True,
    )

    result = registry.execute(ToolCall("get_date", {}))

    _check("get_date success", result.success, True)
    _check(
        "get_date response",
        result.response.startswith("Today is"),
        True,
    )

    result = registry.execute(ToolCall("system_info", {"topic": "os"}))

    _check("os query success", result.success, True)
    _check("os query is windows", "Windows" in result.data["os"], True)

    result = registry.execute(ToolCall("system_info", {"topic": "memory"}))

    _check("memory query success", result.success, True)
    _check("memory total > 0", result.data["total_gb"] > 0, True)

    result = registry.execute(ToolCall("system_info", {"topic": "cpu"}))

    _check("cpu query success", result.success, True)
    _check("cpu logical count > 0", result.data["logical_processors"] > 0, True)

    result = registry.execute(ToolCall("system_info", {"topic": "disk"}))

    _check("disk query success", result.success, True)
    _check("disk total > 0", result.data["total_gb"] > 0, True)

    result = registry.execute(ToolCall("system_info", {"topic": "processes"}))

    _check("processes query success", result.success, True)
    _check("processes non-empty", len(result.data["processes"]) > 0, True)

    result = registry.execute(ToolCall("system_info", {"topic": "battery"}))

    _check("battery query success", result.success, True)

    result = registry.execute(ToolCall("system_info", {"topic": "cpu_usage"}))

    _check("cpu usage query success", result.success, True)

    result = registry.execute(ToolCall("system_info", {"topic": "memory_usage"}))

    _check("memory usage query success", result.success, True)


def test_browser_tools():

    print()
    print("--- BROWSER TOOLS ---")

    registry = build_default_registry()

    result = registry.execute(ToolCall("open_url", {"url": "youtube"}))

    _check("open_url youtube success", result.success, True)
    _check("open_url youtube response", result.response, "Opening YouTube.")

    result = registry.execute(ToolCall("open_url", {"url": "github.com"}))

    _check("open_url domain success", result.success, True)
    _check("open_url domain response", result.response, "Opening github.com.")

    result = registry.execute(
        ToolCall("search_web", {"query": "python", "engine": "google"})
    )

    _check("search_web success", result.success, True)
    _check(
        "search_web url",
        result.data["url"].startswith("https://www.google.com/search"),
        True,
    )

    result = registry.execute(
        ToolCall("search_web", {"query": "python", "engine": "youtube"})
    )

    _check("youtube engine success", result.success, True)
    _check(
        "youtube engine url",
        result.data["url"].startswith("https://www.youtube.com/results"),
        True,
    )


def test_application_tool():

    print()
    print("--- APPLICATION TOOL ---")

    registry = build_default_registry()

    for application, response in [
        ("chrome", "Opening Chrome."),
        ("notepad", "Opening Notepad."),
        ("calculator", "Opening Calculator."),
        ("file explorer", "Opening File Explorer."),
        ("vs code", "Opening Visual Studio Code."),
    ]:

        result = registry.execute(
            ToolCall("open_application", {"application": application})
        )

        _check(
            f"open_application {application}",
            result.response,
            response,
        )


def main():

    print("================================")
    print("      ASTRA TOOL TESTS")
    print("================================")

    test_discovery()
    test_unknown_tool_is_controlled()
    test_safety_policy_denies()
    test_validation()
    test_application_discovery()
    test_system_tools()
    test_browser_tools()
    test_application_tool()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()
