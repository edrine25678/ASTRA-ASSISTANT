"""
System-information capabilities.

Everything here is read-only and obtained directly from Windows /
Python system APIs.  No AI model is needed to answer these.
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import shutil
import socket
import subprocess
import time
import urllib.request
import winreg
from datetime import datetime, timezone
from typing import ClassVar

from tools.base import Tool, ToolResult
from tools.process_tools import SYSTEM_PROCESSES, snapshot_processes


class _MemoryStatusEx(ctypes.Structure):

    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _format_gb(value):
    """Format gigabytes, dropping the decimal when it is .0."""

    return f"{value:.1f}".replace(".0", "")


class _ProcessEntry32(ctypes.Structure):

    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _running_processes():
    """Return running process executable names (Toolhelp API).

    Much faster and more reliable than spawning `tasklist`, and it
    needs no subprocess at all.
    """

    TH32CS_SNAPPROCESS = 0x00000002

    snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPPROCESS, 0
    )

    if snapshot == -1:
        raise OSError("CreateToolhelp32Snapshot failed")

    names = []

    try:

        entry = _ProcessEntry32()
        entry.dwSize = ctypes.sizeof(entry)

        ok = ctypes.windll.kernel32.Process32FirstW(
            snapshot, ctypes.byref(entry)
        )

        while ok:

            names.append(entry.szExeFile)

            ok = ctypes.windll.kernel32.Process32NextW(
                snapshot, ctypes.byref(entry)
            )

    finally:

        ctypes.windll.kernel32.CloseHandle(snapshot)

    return names


class _SystemPowerStatus(ctypes.Structure):

    _fields_ = [
        ("ACLineStatus", ctypes.c_ubyte),
        ("BatteryFlag", ctypes.c_ubyte),
        ("BatteryLifePercent", ctypes.c_ubyte),
        ("SystemStatusFlag", ctypes.c_ubyte),
        ("BatteryLifeTime", ctypes.c_ulong),
        ("BatteryFullLifeTime", ctypes.c_ulong),
    ]


class _ProcessMemoryCounters(ctypes.Structure):

    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class _FileTime(ctypes.Structure):

    _fields_ = [
        ("dwLowDateTime", ctypes.c_ulong),
        ("dwHighDateTime", ctypes.c_ulong),
    ]


def _filetime_value(file_time):
    """Convert a FILETIME to a single 64-bit counter value."""

    return (
        (file_time.dwHighDateTime << 32)
        | file_time.dwLowDateTime
    )


def _system_times():
    """Return (idle, kernel, user) counters as 64-bit values."""

    idle = _FileTime()
    kernel = _FileTime()
    user = _FileTime()

    ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )

    return (
        _filetime_value(idle),
        _filetime_value(kernel),
        _filetime_value(user),
    )


def _cpu_usage_percent(sample_seconds=0.8):
    """Estimate current CPU busy percentage from two samples."""

    idle_1, kernel_1, user_1 = _system_times()

    time.sleep(sample_seconds)

    idle_2, kernel_2, user_2 = _system_times()

    total_delta = (kernel_2 + user_2) - (kernel_1 + user_1)
    idle_delta = idle_2 - idle_1

    if total_delta <= 0:
        return 0.0

    busy = total_delta - idle_delta

    return max(0.0, min(100.0, busy / total_delta * 100.0))


def _memory_gb():
    """Return (total GB, available GB) of physical RAM."""

    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)

    ctypes.windll.kernel32.GlobalMemoryStatusEx(
        ctypes.byref(status)
    )

    total = status.ullTotalPhys / (1024 ** 3)
    available = status.ullAvailPhys / (1024 ** 3)

    return total, available


def _memory_usage():
    """Return (used GB, total GB, percent used)."""

    total, available = _memory_gb()

    used = max(0.0, total - available)

    percent = used / total * 100.0 if total > 0 else 0.0

    return used, total, percent


# ==============================================
# NETWORK (read-only, Phase 7)

def _internet_available():
    """True when an HTTPS connection to a probe host succeeds."""

    try:
        with urllib.request.urlopen(
            "https://www.msftconnecttest.com/connecttest.txt",
            timeout=3,
        ) as response:
            return response.status == 200

    except OSError as e:
        logging.getLogger(__name__).warning("Internet check failed: %s", e)
        return False


def _wifi_ssid():
    """Current Wi-Fi SSID via the fixed read-only netsh query."""

    try:

        output = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )

        for line in output.stdout.splitlines():

            if line.strip().lower().startswith("ssid"):

                ssid = line.split(":", 1)[1].strip()

                if ssid:
                    return ssid

    except (OSError, subprocess.SubprocessError):

        pass

    return None


def _local_ip():
    """Local IPv4 address without sending any network traffic."""

    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]

        finally:
            sock.close()

    except OSError:

        return None


# ==============================================
# GPU (registry, read-only)
# ==============================================

def _cpu_name():
    """Human-friendly processor name from the registry."""

    try:

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        ) as key:

            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")

            return str(name).strip() or None

    except OSError:

        return None


def _gpu_name():
    """Graphics adapter name from the display class registry key."""

    base = ("SYSTEM\\CurrentControlSet\\Control\\Class\\"
            "{4d36e968-e325-11ce-bfc1-08002be10318}")

    try:

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as key:

            index = 0

            while True:

                try:
                    subkey_name = winreg.EnumKey(key, index)
                    index += 1
                except OSError:
                    break

                try:

                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, base + "\\" + subkey_name
                    ) as subkey:

                        description, _ = winreg.QueryValueEx(
                            subkey, "DriverDesc"
                        )

                except OSError:
                    continue

                if description and "display" not in str(description).lower():
                    return str(description)

    except OSError:

        pass

    return None


class GetTimeTool(Tool):

    name = "get_time"
    description = "Return the current local time"
    parameters: ClassVar[dict] = {}

    def run(self, arguments):

        now = datetime.now(tz=timezone.utc).strftime("%I:%M %p")

        return ToolResult(
            success=True,
            data={"time": now},
            response=f"The current time is {now}.",
        )


class GetDateTool(Tool):

    name = "get_date"
    description = "Return today's date"
    parameters: ClassVar[dict] = {}

    def run(self, arguments):

        today = datetime.now(tz=timezone.utc).strftime("%A, %B %d, %Y")

        return ToolResult(
            success=True,
            data={"date": today},
            response=f"Today is {today}.",
        )


class SystemInfoTool(Tool):

    name = "system_info"
    description = "Return information about this computer"
    parameters: ClassVar[dict] = {
        "topic": {
            "type": "str",
            "required": True,
            "choices": [
                "os",
                "memory",
                "cpu",
                "disk",
                "processes",
                "battery",
                "cpu_usage",
                "memory_usage",
                "specs",
                "storage",
                "network",
                "computer_status",
                "top_process",
            ],
        }
    }

    TOPICS = (
        "os",
        "memory",
        "cpu",
        "disk",
        "processes",
        "battery",
        "cpu_usage",
        "memory_usage",
        "specs",
        "storage",
        "network",
        "computer_status",
        "top_process",
    )

    def validate(self, arguments):

        topic = (arguments.get("topic") or "").strip().lower()

        if topic not in self.TOPICS:
            return f"Unknown system topic: {topic}"

        return None

    def run(self, arguments):

        topic = (arguments.get("topic") or "").strip().lower()

        if topic == "storage":

            data, response = self._query_storage(arguments.get("drive"))

        elif topic == "top_process":

            data, response = self._query_top_process(
                arguments.get("kind") or "memory"
            )

        elif topic == "network":

            data, response = self._query_network(
                arguments.get("kind") or "all"
            )

        else:

            handler = getattr(self, f"_query_{topic}")

            data, response = handler()

        return ToolResult(
            success=True,
            data=data,
            response=response,
        )

    def _query_os(self):

        system = platform.system() or "unknown"
        release = platform.release() or ""

        response = f"You are running {system}."

        if release:
            response = f"You are running {system} {release}."

        return {"os": system, "release": release}, response

    def _query_memory(self):

        total, available = _memory_gb()

        response = (
            f"Your computer has {_format_gb(total)} GB of RAM, "
            f"with about {_format_gb(available)} GB available."
        )

        return {
            "total_gb": round(total, 1),
            "available_gb": round(available, 1),
        }, response

    def _query_cpu(self):

        processor = platform.processor() or ""
        logical = os.cpu_count() or 0

        if processor:

            response = (
                f"Your processor is {processor} "
                f"with {logical} logical processors."
            )

        else:

            response = (
                f"Your computer has {logical} logical processors."
            )

        return {
            "name": processor,
            "logical_processors": logical,
        }, response

    def _query_disk(self):

        usage = shutil.disk_usage("C:\\")

        free = usage.free / (1024 ** 3)
        total = usage.total / (1024 ** 3)

        response = (
            f"You have {_format_gb(free)} GB free of "
            f"{_format_gb(total)} GB on your main drive."
        )

        return {
            "free_gb": round(free, 1),
            "total_gb": round(total, 1),
        }, response

    def _query_processes(self):

        names = []

        for name in _running_processes():

            if name and name not in names:
                names.append(name)

        main = ", ".join(names[:12])

        response = f"The main running processes are: {main}."

        return {"processes": names}, response

    def _query_battery(self):

        status = _SystemPowerStatus()

        ctypes.windll.kernel32.GetSystemPowerStatus(
            ctypes.byref(status)
        )

        plugged = status.ACLineStatus == 1

        percent = (
            status.BatteryLifePercent
            if status.BatteryLifePercent <= 100
            else None
        )

        if plugged:

            if percent is None:
                response = "You're plugged in."
            else:
                response = (
                    f"You're plugged in with {percent}% battery."
                )

        else:

            if percent is None:
                response = "You're on battery."
            else:
                response = (
                    f"You're on battery with {percent}% left."
                )

        return {
            "plugged_in": plugged,
            "battery_percent": percent,
        }, response

    def _query_cpu_usage(self):

        percent = round(_cpu_usage_percent(), 1)

        response = (
            f"Your CPU is about {_format_gb(percent)}% busy "
            f"right now."
        )

        return {"cpu_percent": percent}, response

    def _query_memory_usage(self):

        used, total, percent = _memory_usage()

        response = (
            f"You're using about {_format_gb(percent)}% of your "
            f"RAM ({_format_gb(used)} of {_format_gb(total)} GB)."
        )

        return {
            "used_gb": round(used, 1),
            "total_gb": round(total, 1),
            "percent": round(percent, 1),
        }, response

    # ==============================================
    # PHASE 7 TOPICS
    # ==============================================

    def _query_specs(self):

        info = {
            "computer": os.environ.get("COMPUTERNAME", "this computer"),
            "os": platform.platform(),
            "processor": _cpu_name() or platform.processor() or "",
            "logical_processors": os.cpu_count() or 0,
            "gpu": _gpu_name(),
        }

        total, _ = _memory_gb()

        info["memory_gb"] = round(total, 1)

        usage = shutil.disk_usage("C:\\")

        info["free_gb"] = round(usage.free / (1024 ** 3), 1)

        parts = [
            f"computer '{info['computer']}'",
            f"running {info['os']}",
            "with a " + (info["processor"] or "processor")
            + f" and {info['logical_processors']} logical processors",
        ]

        if info["gpu"]:
            parts.append(f"a {info['gpu']} graphics card")

        parts.append(f"{_format_gb(info['memory_gb'])} GB of RAM")
        parts.append(f"about {_format_gb(info['free_gb'])} GB free on C:")

        response = "This is a " + ", ".join(parts) + "."

        return info, response

    def _query_storage(self, drive=None):

        kernel32 = ctypes.windll.kernel32

        bits = kernel32.GetLogicalDrives()

        drives = []

        for index in range(26):

            if not (bits >> index) & 1:
                continue

            letter = chr(65 + index)

            root = f"{letter}:\\"

            if kernel32.GetDriveTypeW(root) not in (2, 3):
                continue

            if drive and letter != drive.upper():
                continue

            total = ctypes.c_ulonglong()
            free = ctypes.c_ulonglong()

            if kernel32.GetDiskFreeSpaceExW(
                root, None, ctypes.byref(total), ctypes.byref(free)
            ):

                drives.append({
                    "drive": letter,
                    "free_gb": round(free.value / (1024 ** 3), 1),
                    "total_gb": round(total.value / (1024 ** 3), 1),
                })

        if not drives:

            return {"drives": []}, (
                "I couldn't read any storage drives."
            )

        if len(drives) == 1:

            d = drives[0]

            response = (
                f"{d['drive']}: has {_format_gb(d['free_gb'])} GB "
                f"free of {_format_gb(d['total_gb'])} GB."
            )

        else:

            response = "Your drives: " + ", ".join(
                f"{d['drive']}: {_format_gb(d['free_gb'])} free of "
                f"{_format_gb(d['total_gb'])} GB"
                for d in drives
            ) + "."

        return {"drives": drives}, response

    def _query_network(self, kind="all"):

        data = {}
        parts = []

        if kind in ("all", "internet"):

            online = _internet_available()

            data["online"] = online

            parts.append(
                "You are connected to the internet."
                if online
                else "You are not connected to the internet."
            )

        if kind in ("all", "wifi"):

            ssid = _wifi_ssid()

            data["wifi_ssid"] = ssid

            if ssid:
                parts.append(
                    f"You are connected to Wi-Fi network '{ssid}'."
                )
            elif kind != "all":
                parts.append(
                    "I couldn't detect a Wi-Fi connection."
                )

        if kind in ("all", "ip"):

            ip = _local_ip()

            data["local_ip"] = ip

            if ip:
                parts.append(
                    f"Your local IP address is {ip}."
                )

        if not parts:

            return data, "I couldn't gather network information."

        return data, " ".join(parts)

    def _query_computer_status(self):

        cpu = round(_cpu_usage_percent(), 1)

        used, total, percent = _memory_usage()

        status = _SystemPowerStatus()

        ctypes.windll.kernel32.GetSystemPowerStatus(
            ctypes.byref(status)
        )

        plugged = status.ACLineStatus == 1

        battery = (
            status.BatteryLifePercent
            if status.BatteryLifePercent <= 100
            else None
        )

        usage = shutil.disk_usage("C:\\")

        free = usage.free / (1024 ** 3)

        data = {
            "cpu_percent": cpu,
            "memory_percent": round(percent, 1),
            "plugged_in": plugged,
            "battery_percent": battery,
            "free_gb": round(free, 1),
        }

        parts = [
            f"your CPU is about {_format_gb(cpu)}% busy",
            (f"{_format_gb(percent)}% of your RAM is used "
            f"({_format_gb(used)} of {_format_gb(total)} GB)"),
        ]

        if battery is not None:

            parts.append(
                "you're plugged in"
                if plugged
                else f"you're on battery with {battery}% left"
            )

        parts.append(f"about {_format_gb(free)} GB free on C:")

        overall = "fine" if (cpu < 85 and percent < 90) else "under load"

        response = (
            f"Your computer looks {overall}. "
            + ", ".join(parts)
            + "."
        )

        return data, response

    def _query_top_process(self, kind="memory"):
        """The running application using the most memory."""

        if kind != "memory":

            return {
                "top": None,
                "note": "per-process CPU ranking unsupported",
            }, (
                f"I don't rank processes by {kind}. Your overall "
                "CPU usage is about "
                f"{_format_gb(round(_cpu_usage_percent(), 1))}%."
            )

        kernel32 = ctypes.windll.kernel32

        psapi = ctypes.windll.psapi

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        best = None

        for process in snapshot_processes():

            stem = process["name"].rsplit(".", 1)[0]

            if stem in SYSTEM_PROCESSES:
                continue

            handle = kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                False,
                process["pid"],
            )

            if not handle:
                continue

            try:

                counters = _ProcessMemoryCounters()

                counters.cb = ctypes.sizeof(counters)

                if psapi.GetProcessMemoryInfo(
                    handle, ctypes.byref(counters), ctypes.sizeof(counters)
                ):

                    working_set = counters.WorkingSetSize

                    if best is None or working_set > best[1]:
                        best = (process["name"], working_set)

            finally:

                kernel32.CloseHandle(handle)

        if best is None:

            return {"top": None}, (
                "I couldn't inspect running processes for memory usage."
            )

        name, working_set = best

        mb = working_set / (1024 ** 2)

        response = (
            f"{name.rsplit('.', 1)[0].capitalize()} is using the "
            "most memory right now, about "
            f"{f'{mb:.1f}'.replace('.0', '')} MB."
        )

        return {
            "top": name,
            "working_set_mb": round(mb, 1),
        }, response
