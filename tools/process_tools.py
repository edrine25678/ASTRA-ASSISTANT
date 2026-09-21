"""
Controlled process inspection and closing.

Processes are read through the Win32 Toolhelp snapshot API and
terminated through OpenProcess / TerminateProcess directly - no
shell command is ever built or executed (spec section 26).  System
processes are blacklisted and Astra never terminates itself.

Closing is destructive, so the tool always requires confirmation.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
from typing import ClassVar

from core.logger import get_logger
from tools.base import AstraTool, ToolResult

logger = get_logger("tools.process")

PROCESS_TERMINATE = 0x0001

TH32CS_SNAPPROCESS = 0x00000002

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

# Processes Windows itself needs; Astra will never terminate these.
SYSTEM_PROCESSES = {
    "system", "registry", "csrss", "wininit", "winlogon", "services",
    "lsass", "lsm", "smss", "svchost", "dwm", "explorer", "spoolsv",
    "sihost", "taskhostw", "runtimebroker", "fontdrvhost", "conhost",
    "searchindexer", "shellexperiencehost", "startmenuexperiencehost",
    "dllhost", "backgroundtaskhost", "ctfmon", "regsvc", "msmpeng",
    "audiodg", "winsrv", "sessmgr", "logonui",
}


class PROCESSENTRY32(ctypes.Structure):

    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def snapshot_processes():
    """All running processes as a list of {"pid", "name"} dicts."""

    processes = []

    kernel32 = ctypes.windll.kernel32

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)

    if snapshot == INVALID_HANDLE_VALUE:
        return processes

    try:

        entry = PROCESSENTRY32()

        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

        if not kernel32.Process32First(snapshot, ctypes.byref(entry)):
            return processes

        while True:

            name = entry.szExeFile.decode(
                "utf-8", errors="replace"
            ).lower()

            processes.append({
                "pid": int(entry.th32ProcessID),
                "name": name,
            })

            if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                break

    finally:

        kernel32.CloseHandle(snapshot)

    return processes


def terminate_process(pid):
    """Terminate one process.  Returns True on success."""

    kernel32 = ctypes.windll.kernel32

    handle = kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)

    if not handle:
        return False

    try:

        result = kernel32.TerminateProcess(handle, 1)

        return bool(result)

    finally:

        kernel32.CloseHandle(handle)


def matching_processes(application):
    """Running processes whose name matches the application name."""

    app = (application or "").strip().lower()

    if not app:
        return []

    stem = app.rsplit(".", 1)[0].strip()

    matches = []

    for process in snapshot_processes():

        name = process["name"]

        exe_stem = name.rsplit(".", 1)[0]

        if not exe_stem:
            continue

        if (
            exe_stem == stem
            or exe_stem in stem
            or stem in exe_stem
            or stem in name
        ):
            matches.append(process)

    return matches


class CloseApplicationTool(AstraTool):

    name = "close_application"
    description = "Close a running application (confirmation required)"
    parameters: ClassVar[dict] = {"application": {"type": "str", "required": True}}

    requires_confirmation = True

    def run(self, arguments):

        application = (arguments.get("application") or "").strip()

        if not application:
            return ToolResult(
                success=False,
                tool=self.name,
                response="Which application would you like me to close?",
            )

        matches = matching_processes(application)

        if not matches:
            return ToolResult(
                success=False,
                tool=self.name,
                data={"closed": []},
                response=(
                    f"There are no running processes named "
                    f"{application}."
                ),
            )

        protected = [
            process for process in matches
            if process["name"].rsplit(".", 1)[0] in SYSTEM_PROCESSES
        ]

        if protected:
            return ToolResult(
                success=False,
                tool=self.name,
                data={"closed": []},
                response=(
                    f"I won't close {application} - it is a Windows "
                    "system process."
                ),
            )

        closed = []
        failed = []

        for process in matches:

            if process["pid"] == ctypes.windll.kernel32.GetCurrentProcessId():
                continue

            if terminate_process(process["pid"]):
                closed.append(process)
            else:
                failed.append(process)

        count = len(closed) + len(failed)

        if closed and not failed:

            response = (
                f"Closed {application} "
                f"({' '.join(str(p['pid']) for p in closed)})."
            )

            logger.info("closed %s: %s", application, closed)

        elif closed:

            response = (
                f"I closed some windows of {application}, but a few "
                "could not be terminated."
            )

        elif len(matches) == 1:

            response = (
                f"I couldn't close {application} - the process "
                "refused to terminate."
            )

        else:

            response = (
                f"I couldn't close {application} - none of its "
                "processes could be terminated."
            )

        return ToolResult(
            success=bool(closed),
            tool=self.name,
            data={"closed": closed, "failed": failed, "count": count},
            response=response,
        )