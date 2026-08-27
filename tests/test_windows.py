"""
Phase 7 tests: Windows awareness and controlled computer interaction.

Covers the spec section 30 list plus safety guards: NLU routing for
each new intent, entity extraction (drives, file types, locations,
dates), "close it" pronoun resolution, close-app confirmation flow,
close-tool protections, and graceful degradation.

Run: python -m tests.test_windows
"""

import datetime
import os
import re
import sys
import unittest

from core.brain import AstraBrain
from core.capabilities.windows import (
    NetworkCapability,
    ProcessesCapability,
    StorageCapability,
    WindowsApplicationsCapability,
    WindowsFilesCapability,
    WindowsFoldersCapability,
    WindowsSystemCapability,
    register_windows_capabilities,
)
from core.intelligence.context import ConversationContext
from core.intelligence.intent import Intent, IntentType
from core.intelligence.nlu import NLU
from core.intelligence.assistant import AstraAssistant
from core.capabilities.base import CapabilityRegistry

from tools.base import ToolResult, ToolCall
from tools.registry import ToolRegistry
from tools.safety import ToolSafety
from tools.process_tools import (
    CloseApplicationTool,
    SYSTEM_PROCESSES,
    snapshot_processes,
    terminate_process,
)


class AllowAllSafety(ToolSafety):

    def is_allowed(self, call):
        return True

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, os.path.abspath("."))


_results = {"pass": 0, "fail": 0}


def _check(name, actual, expected):
    try:
        if isinstance(expected, type) and not isinstance(actual, expected):
            raise AssertionError(f"expected {expected.__name__}, got {actual!r}")
        if not isinstance(expected, type) and actual != expected:
            raise AssertionError(f"expected {expected!r}, got {actual!r}")
    except Exception as error:
        _results["fail"] += 1
        print(f"FAIL: {name} - {error}")
        return
    _results["pass"] += 1
    print(f"  ok: {name}")


# ==============================================
# FAKES
# ==============================================

class FakeRegistry:

    def __init__(self):
        self.executed = []

    def discover(self):
        return []

    def register(self, tool):
        pass

    def execute(self, call):
        self.executed.append(call)
        if call.name == "close_application":
            return ToolResult(
                success=True,
                tool="close_application",
                data={"closed": [], "count": 0},
                response=f"Closed {call.arguments.get('application')}.",
            )
        if call.name == "system_info":
            return ToolResult(
                success=True,
                tool="system_info",
                data={"topic": call.arguments.get("topic")},
                response="The system is fine.",
            )
        if call.name == "file_search":
            return ToolResult(
                success=True,
                tool="file_search",
                data={"files": [], "count": 0},
                response="Found nothing.",
            )
        if call.name == "file_open_folder":
            return ToolResult(
                success=True,
                tool="file_open_folder",
                data={"path": call.arguments.get("path")},
                response="Opening folder.",
            )
        if call.name == "file_list_directory":
            return ToolResult(
                success=True,
                tool="file_list_directory",
                data={"items": ["a.txt"], "path": call.arguments.get("path")},
                response="The folder contains 1 item(s).",
            )
        return ToolResult(success=True, tool=call.name,
                          response="ok.", data={})


class FakeDiscovery:

    APPS = {
        "chrome": "chrome",
        "browser": "chrome",
        "vs code": "vs code",
        "vscode": "vs code",
        "notepad": "notepad",
        "spotify": "spotify",
    }

    def __init__(self):
        self.apps = [{"name": "chrome"}, {"name": "vs code"},
                     {"name": "notepad"}, {"name": "spotify"}]

    def find(self, phrase):
        key = (phrase or "").strip().lower()
        if key in self.APPS:
            return {"name": self.APPS[key], "display": self.APPS[key]}
        return None


def _make_nlu(discovery=None):
    return NLU(discovery=discovery or FakeDiscovery(), brain=None)


def _make_registry():
    registry = CapabilityRegistry(tool_registry=FakeRegistry(),
                                  discovery=FakeDiscovery())
    register_windows_capabilities(registry)
    return registry


# ==============================================
# 1. NLU: RAM / processor / storage / status
# ==============================================

def test_ram_question():
    print()
    print("--- RAM QUESTION ---")
    nlu = _make_nlu()
    intent = nlu.resolve("how much ram do i have", None, skip_planner=True)
    _check("ram -> MEMORY_STATUS", intent.name, IntentType.MEMORY_STATUS)


def test_processor_question():
    print()
    print("--- PROCESSOR QUESTION ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what processor do i have", None, skip_planner=True)
    _check("processor -> CPU_STATUS", intent.name, IntentType.CPU_STATUS)


def test_specs_question():
    print()
    print("--- SPECIFICATIONS QUESTION ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what are my computer specifications",
                         None, skip_planner=True)
    _check("specs -> SYSTEM_INFORMATION", intent.name,
           IntentType.SYSTEM_INFORMATION)
    _check("specs topic", intent.entities.get("topic"), "specs")


def test_computer_status_question():
    print()
    print("--- COMPUTER STATUS QUESTION ---")
    nlu = _make_nlu()
    intent = nlu.resolve("how is my computer doing", None, skip_planner=True)
    _check("status -> COMPUTER_STATUS", intent.name,
           IntentType.COMPUTER_STATUS)


def test_battery_question():
    print()
    print("--- BATTERY QUESTION ---")
    nlu = _make_nlu()
    intent = nlu.resolve("is my laptop charging", None, skip_planner=True)
    _check("charging -> BATTERY_STATUS", intent.name,
           IntentType.BATTERY_STATUS)


# ==============================================
# 2. NLU: installed applications
# ==============================================

def test_installed_app():
    print()
    print("--- INSTALLED APP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("is chrome installed", None, skip_planner=True)
    _check("is x installed -> APPLICATION_SEARCH", intent.name,
           IntentType.APPLICATION_SEARCH)
    _check("app entity chrome", intent.entities.get("application"), "chrome")


def test_do_i_have_app():
    print()
    print("--- DO I HAVE APP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("do i have vs code", None, skip_planner=True)
    _check("do i have -> APPLICATION_SEARCH", intent.name,
           IntentType.APPLICATION_SEARCH)
    _check("app entity vs code", intent.entities.get("application"), "vs code")


def test_installed_apps_list():
    print()
    print("--- INSTALLED APPS LIST ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what applications are installed",
                         None, skip_planner=True)
    _check("list -> APPLICATION_SEARCH", intent.name,
           IntentType.APPLICATION_SEARCH)


# ==============================================
# 3. NLU: running applications
# ==============================================

def test_running_app():
    print()
    print("--- RUNNING APP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("is chrome running", None, skip_planner=True)
    _check("is x running -> RUNNING_APPLICATIONS", intent.name,
           IntentType.RUNNING_APPLICATIONS)
    _check("app entity chrome", intent.entities.get("application"), "chrome")


def test_what_is_running():
    print()
    print("--- WHAT IS RUNNING ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what is running right now", None, skip_planner=True)
    _check("what is running -> RUNNING_APPLICATIONS", intent.name,
           IntentType.RUNNING_APPLICATIONS)


def test_what_is_open():
    print()
    print("--- WHAT IS OPEN ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what's open", None, skip_planner=True)
    _check("what's open -> RUNNING_APPLICATIONS", intent.name,
           IntentType.RUNNING_APPLICATIONS)


# ==============================================
# 4. NLU: close application
# ==============================================

def test_close_app():
    print()
    print("--- CLOSE APP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("close chrome", None, skip_planner=True)
    _check("close x -> CLOSE_APPLICATION", intent.name,
           IntentType.CLOSE_APPLICATION)
    _check("app entity chrome", intent.entities.get("application"), "chrome")


def test_quit_app():
    print()
    print("--- QUIT APP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("quit spotify", None, skip_planner=True)
    _check("quit x -> CLOSE_APPLICATION", intent.name,
           IntentType.CLOSE_APPLICATION)
    _check("app entity spotify", intent.entities.get("application"),
           "spotify")


# ==============================================
# 5. NLU: close it (pronoun, via topic)
# ==============================================

def test_close_it_pronoun():
    print()
    print("--- CLOSE IT PRONOUN ---")
    nlu = _make_nlu()
    context = ConversationContext()
    context.set_topic(IntentType.RUNNING_APPLICATIONS, "chrome")
    intent = nlu.resolve("close it", context, skip_planner=True)
    _check("close it -> CLOSE_APPLICATION", intent.name,
           IntentType.CLOSE_APPLICATION)
    _check("close it entity chrome", intent.entities.get("application"),
           "chrome")


def test_close_it_without_topic_asks():
    print()
    print("--- CLOSE IT WITHOUT TOPIC ---")
    nlu = _make_nlu()
    intent = nlu.resolve("close it", ConversationContext(),
                         skip_planner=True)
    _check("no topic -> FILE_OPERATION (not app)", intent.name,
           IntentType.FILE_OPERATION)


# ==============================================
# 6. NLU: show downloads / open project / files
# ==============================================

def test_show_downloads():
    print()
    print("--- SHOW DOWNLOADS ---")
    nlu = _make_nlu()
    intent = nlu.resolve("show me my downloads", None, skip_planner=True)
    _check("show downloads -> FOLDER_OPERATION", intent.name,
           IntentType.FOLDER_OPERATION)
    _check("location downloads", intent.entities.get("location"),
           "downloads")
    _check("action open", intent.entities.get("action"), "open")


def test_go_to_downloads():
    print()
    print("--- GO TO DOWNLOADS ---")
    nlu = _make_nlu()
    intent = nlu.resolve("go to downloads", None, skip_planner=True)
    _check("go to downloads -> FOLDER_OPERATION", intent.name,
           IntentType.FOLDER_OPERATION)


def test_open_project():
    print()
    print("--- OPEN PROJECT ---")
    nlu = _make_nlu()
    intent = nlu.resolve("open the astra project", None, skip_planner=True)
    _check("open project -> FOLDER_OPERATION", intent.name,
           IntentType.FOLDER_OPERATION)
    _check("location astra", intent.entities.get("location"), "astra")


def test_list_here():
    print()
    print("--- LIST HERE ---")
    nlu = _make_nlu()
    context = ConversationContext()
    context.current_location = r"C:\somewhere"
    intent = nlu.resolve("what files are here", context, skip_planner=True)
    _check("what files are here -> FOLDER_OPERATION", intent.name,
           IntentType.FOLDER_OPERATION)
    _check("location here", intent.entities.get("location"), "__here__")


# ==============================================
# 7. NLU: find pdfs in downloads
# ==============================================

def test_find_pdf_in_downloads():
    print()
    print("--- FIND PDF IN DOWNLOADS ---")
    nlu = _make_nlu()
    intent = nlu.resolve("find the pdf i downloaded yesterday",
                         None, skip_planner=True)
    _check("find pdf -> FILE_SEARCH", intent.name, IntentType.FILE_SEARCH)
    _check("type pdf", intent.entities.get("file_type"), "pdf")
    _check("location downloads", intent.entities.get("location"),
           "downloads")
    _check("days 1", intent.entities.get("modified_within_days"), 1)


def test_find_python_files():
    print()
    print("--- FIND PYTHON FILES ---")
    nlu = _make_nlu()
    intent = nlu.resolve("find my python files in the astra project",
                         None, skip_planner=True)
    _check("find python -> FILE_SEARCH", intent.name,
           IntentType.FILE_SEARCH)
    _check("type python", intent.entities.get("file_type"), "python")
    _check("location astra", intent.entities.get("location"), "astra")


# ==============================================
# 8. NLU: drives / storage
# ==============================================

def test_drives():
    print()
    print("--- DRIVES ---")
    nlu = _make_nlu()
    intent = nlu.resolve("show me my drives", None, skip_planner=True)
    _check("drives -> STORAGE_STATUS", intent.name,
           IntentType.STORAGE_STATUS)
    _check("no drive entity", intent.entities.get("drive"), None)


def test_c_drive():
    print()
    print("--- C DRIVE ---")
    nlu = _make_nlu()
    intent = nlu.resolve("how much space is on c drive", None,
                         skip_planner=True)
    _check("c drive -> STORAGE_STATUS", intent.name,
           IntentType.STORAGE_STATUS)
    _check("drive entity C", intent.entities.get("drive"), "C")


# ==============================================
# 9. NLU: network / wifi / ip
# ==============================================

def test_internet():
    print()
    print("--- INTERNET ---")
    nlu = _make_nlu()
    intent = nlu.resolve("am i connected to the internet", None,
                         skip_planner=True)
    _check("internet -> NETWORK_STATUS", intent.name,
           IntentType.NETWORK_STATUS)
    _check("kind internet", intent.entities.get("kind"), "internet")


def test_wifi():
    print()
    print("--- WIFI ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what wifi am i connected to", None,
                         skip_planner=True)
    _check("wifi -> NETWORK_STATUS", intent.name,
           IntentType.NETWORK_STATUS)
    _check("kind wifi", intent.entities.get("kind"), "wifi")


def test_ip():
    print()
    print("--- IP ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what is my ip address", None, skip_planner=True)
    _check("ip -> NETWORK_STATUS", intent.name, IntentType.NETWORK_STATUS)
    _check("kind ip", intent.entities.get("kind"), "ip")


# ==============================================
# 10. NLU: process information
# ==============================================

def test_most_memory():
    print()
    print("--- MOST MEMORY ---")
    nlu = _make_nlu()
    intent = nlu.resolve("what is using the most memory", None,
                         skip_planner=True)
    _check("most memory -> PROCESS_INFORMATION", intent.name,
           IntentType.PROCESS_INFORMATION)
    _check("kind memory", intent.entities.get("kind"), "memory")


# ==============================================
# 11. Routing: every new intent reaches a capability
# ==============================================

def test_routing():
    print()
    print("--- ROUTING ---")
    registry = _make_registry()
    for intent_name in (
        IntentType.SYSTEM_INFORMATION,
        IntentType.CPU_STATUS,
        IntentType.MEMORY_STATUS,
        IntentType.STORAGE_STATUS,
        IntentType.BATTERY_STATUS,
        IntentType.NETWORK_STATUS,
        IntentType.COMPUTER_STATUS,
        IntentType.APPLICATION_SEARCH,
        IntentType.RUNNING_APPLICATIONS,
        IntentType.PROCESS_INFORMATION,
        IntentType.CLOSE_APPLICATION,
        IntentType.FILE_SEARCH,
        IntentType.FOLDER_OPERATION,
    ):
        capability = registry.route(intent_name)
        _check(f"route {intent_name}", capability is not None, True)


# ==============================================
# 12. Capability behaviour with a stub registry
# ==============================================

def test_capability_execution():
    print()
    print("--- CAPABILITY EXECUTION ---")
    registry = _make_registry()

    result = registry.route(IntentType.MEMORY_STATUS).execute(
        Intent(name=IntentType.MEMORY_STATUS, confidence=0.9,
               entities={}, original_text="how much ram"),
        ConversationContext(),
    )
    _check("memory capability success", result.success, True)
    _check("memory capability used system_info", result.call.name,
           "system_info")
    _check("memory capability topic", result.call.arguments["topic"],
           "memory_usage")

    result = registry.route(IntentType.NETWORK_STATUS).execute(
        Intent(name=IntentType.NETWORK_STATUS, confidence=0.9,
               entities={"kind": "wifi"}, original_text="what wifi"),
        ConversationContext(),
    )
    _check("network kind passed", result.call.arguments["kind"], "wifi")

    result = registry.route(IntentType.STORAGE_STATUS).execute(
        Intent(name=IntentType.STORAGE_STATUS, confidence=0.9,
               entities={"drive": "C"}, original_text="c drive"),
        ConversationContext(),
    )
    _check("storage drive passed", result.call.arguments["drive"], "C")

    result = registry.route(IntentType.APPLICATION_SEARCH).execute(
        Intent(name=IntentType.APPLICATION_SEARCH, confidence=0.9,
               entities={"application": "chrome"},
               original_text="is chrome installed"),
        ConversationContext(),
    )
    _check("installed found", result.success, True)
    _check("installed answer", result.response,
           "Yes, chrome is installed.")

    result = registry.route(IntentType.APPLICATION_SEARCH).execute(
        Intent(name=IntentType.APPLICATION_SEARCH, confidence=0.9,
               entities={"application": "thingamajig"},
               original_text="is thingamajig installed"),
        ConversationContext(),
    )
    _check("installed missing", result.response,
           "I don't see thingamajig installed on this computer.")

    result = registry.route(IntentType.FILE_SEARCH).execute(
        Intent(name=IntentType.FILE_SEARCH, confidence=0.9,
               entities={"file_type": "pdf", "extensions": [".pdf"],
                         "location": "downloads", "query": "",
                         "modified_within_days": 1},
               original_text="find pdfs"),
        ConversationContext(),
    )
    _check("file search root", result.call.arguments["root"], "downloads")
    _check("file search days", result.call.arguments["modified_within_days"], 1)

    context = ConversationContext()
    result = registry.route(IntentType.FOLDER_OPERATION).execute(
        Intent(name=IntentType.FOLDER_OPERATION, confidence=0.9,
               entities={"action": "open", "location": "downloads",
                         "path": None},
               original_text="open downloads"),
        context,
    )
    _check("folder open success", result.success, True)
    _check("folder open tool", result.call.name, "file_open_folder")
    _check("current location set", context.current_location,
           os.path.join(os.path.expanduser("~"), "Downloads"))


def test_close_requires_confirmation():
    print()
    print("--- CLOSE REQUIRES CONFIRMATION ---")
    registry = ToolRegistry(safety=ToolSafety())
    registry.register(CloseApplicationTool())
    call = ToolCall("close_application", {"application": "chrome"})
    result = registry.execute(call)
    _check("close needs confirmation", result.needs_confirmation, True)
    _check("close not executed", call.confirmed, False)


def test_close_tool_guards():
    print()
    print("--- CLOSE TOOL GUARDS ---")
    tool = CloseApplicationTool()
    result = tool.run({})
    _check("no app rejected", result.success, False)
    result = tool.run({"application": "nonexistent_app_xyz"})
    _check("unknown app rejected", result.success, False)
    _check("unknown app message", result.response,
           "There are no running processes named nonexistent_app_xyz.")
    result = tool.run({"application": "svchost"})
    _check("system process protected", result.success, False)
    _check("system process message", "system process" in result.response,
           True)


def test_system_processes_blacklist():
    print()
    print("--- SYSTEM PROCESS BLACKLIST ---")
    for name in ("svchost", "explorer", "lsass", "csrss", "dwm"):
        _check(f"blacklisted {name}", name in SYSTEM_PROCESSES, True)


# ==============================================
# 13. Assistant: end-to-end close flow
# ==============================================

def _stub_close_registry():

    class StubCloseTool:

        name = "close_application"
        description = "close an application"
        parameters = {}
        requires_confirmation = True

        def describe(self):
            return {"name": self.name, "description": self.description,
                    "parameters": self.parameters}

        def validate(self, arguments):
            return None

        def run(self, arguments):
            return ToolResult(
                success=True,
                tool=self.name,
                data={},
                response=f"Closed {arguments.get('application')}.",
            )

    registry = ToolRegistry(safety=AllowAllSafety())
    registry.register(StubCloseTool())

    class StubOpenTool:
        name = "open_application"
        description = "open"
        parameters = {}

        def describe(self):
            return {"name": self.name, "description": self.description,
                    "parameters": self.parameters}

        def validate(self, arguments):
            return None

        def run(self, arguments):
            return ToolResult(success=True, tool=self.name,
                              response="Opening it.", data={})

    registry.register(StubOpenTool())
    return registry


def test_assistant_close_flow():
    print()
    print("--- ASSISTANT CLOSE FLOW ---")
    brain = AstraBrain(registry=_stub_close_registry(), memory_enabled=False)
    assistant = AstraAssistant(
        brain=brain,
        discovery=FakeDiscovery(),
        registry=_stub_close_registry(),
    )
    response = assistant.process("is chrome running")
    _check("is chrome running not fallback",
           "don't know how to do that" not in response.response, True)

    response = assistant.process("close it")
    _check("close it responds", bool(response.response), True)
    _check("pending tool_confirm", assistant.pending is not None, True)

    response = assistant.process("yes")
    _check("close confirmed response", bool(response.response), True)
    _check("pending cleared", assistant.pending is None, True)


def test_assistant_close_without_topic():
    print()
    print("--- ASSISTANT CLOSE WITHOUT TOPIC ---")
    brain = AstraBrain(registry=_stub_close_registry(), memory_enabled=False)
    assistant = AstraAssistant(
        brain=brain,
        discovery=FakeDiscovery(),
        registry=_stub_close_registry(),
    )
    response = assistant.process("close chrome")
    _check("close chrome asks", bool(response.response), True)
    _check("close chrome pending", assistant.pending is not None, True)
    response = assistant.process("no")
    _check("close cancelled", "won't" in response.response.lower(), True)
    _check("close cancelled pending", assistant.pending is None, True)


# ==============================================
# 14. Graceful degradation
# ==============================================

def test_unknown_falls_back_gracefully():
    print()
    print("--- UNKNOWN GRACEFUL ---")
    nlu = _make_nlu()
    intent = nlu.resolve("purple monkeys fly at midnight", None,
                         skip_planner=True)
    _check("gibberish -> UNKNOWN", intent.name, IntentType.UNKNOWN)


def test_specs_capability_runs():
    print()
    print("--- SPECS CAPABILITY (LIVE) ---")
    try:
        import ctypes
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
        live = snapshot != ctypes.c_void_p(-1).value
        if live:
            ctypes.windll.kernel32.CloseHandle(snapshot)
        _check("toolhelp snapshot works", live, True)
    except Exception as error:
        _check("toolhelp snapshot works", False, True)


def test_close_tool_real_snapshot():
    print()
    print("--- CLOSE TOOL REAL SNAPSHOT ---")
    processes = snapshot_processes()
    _check("snapshot returns list", isinstance(processes, list), True)
    _check("snapshot has processes", len(processes) > 0, True)


def test_terminate_function_exists():
    print()
    print("--- TERMINATE FUNCTION ---")
    _check("terminate_process callable", callable(terminate_process), True)


# ==============================================
# MAIN
# ==============================================

def main():
    test_ram_question()
    test_processor_question()
    test_specs_question()
    test_computer_status_question()
    test_battery_question()
    test_installed_app()
    test_do_i_have_app()
    test_installed_apps_list()
    test_running_app()
    test_what_is_running()
    test_what_is_open()
    test_close_app()
    test_quit_app()
    test_close_it_pronoun()
    test_close_it_without_topic_asks()
    test_show_downloads()
    test_go_to_downloads()
    test_open_project()
    test_list_here()
    test_find_pdf_in_downloads()
    test_find_python_files()
    test_drives()
    test_c_drive()
    test_internet()
    test_wifi()
    test_ip()
    test_most_memory()
    test_routing()
    test_capability_execution()
    test_close_requires_confirmation()
    test_close_tool_guards()
    test_system_processes_blacklist()
    test_assistant_close_flow()
    test_assistant_close_without_topic()
    test_unknown_falls_back_gracefully()
    test_specs_capability_runs()
    test_close_tool_real_snapshot()
    test_terminate_function_exists()

    print()
    print("=" * 32)
    print(f"PASS: {_results['pass']}   FAIL: {_results['fail']}")
    print("=" * 32)

    return 0 if _results["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())