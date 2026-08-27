"""
Performance probe (Phase 5 spec section 37): measures Astra's
resident RAM and CPU usage in three states on this machine:

  1. idle            - after startup, Whisper not yet loaded
  2. whisper loaded  - after the Whisper model is in memory
  3. transcribing    - Whisper transcribes data/whisper_test.wav

Run from the project root:

    python tests/performance_probe.py
    (or: .venv/Scripts/python.exe tests/performance_probe.py)

This script is informational: it always exits 0 and prints a table.
"""

import ctypes
import ctypes.wintypes
import os
import sys
import time

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from core.logger import get_logger

logger = get_logger("tests.performance_probe")

# ==============================================
# WINDOWS MEASUREMENT HELPERS (psapi + kernel32)
# ==============================================

_psapi = ctypes.WinDLL("psapi")
_kernel32 = ctypes.WinDLL("kernel32")


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


def _working_set_mb():

    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(_ProcessMemoryCounters)

    _psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        ctypes.wintypes.DWORD,
    ]
    _psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL

    ok = _psapi.GetProcessMemoryInfo(
        _kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    )

    if not ok:
        return 0.0

    return counters.WorkingSetSize / (1024 * 1024)


def _cpu_percent(sample_seconds=0.8):

    class _FileTime(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_ulong),
            ("dwHighDateTime", ctypes.c_ulong),
        ]

    def _to_int(ft):
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

    idle0, kernel0, user0 = _FileTime(), _FileTime(), _FileTime()

    _kernel32.GetSystemTimes(
        ctypes.byref(idle0),
        ctypes.byref(kernel0),
        ctypes.byref(user0),
    )

    time.sleep(sample_seconds)

    idle1, kernel1, user1 = _FileTime(), _FileTime(), _FileTime()

    _kernel32.GetSystemTimes(
        ctypes.byref(idle1),
        ctypes.byref(kernel1),
        ctypes.byref(user1),
    )

    idle = _to_int(idle1) - _to_int(idle0)
    total = (
        _to_int(kernel1) + _to_int(user1)
    ) - (_to_int(kernel0) + _to_int(user0))

    if total <= 0:
        return 0.0

    return max(0.0, min(100.0, 100.0 * (total - idle) / total))


# ==============================================
# MEASUREMENTS
# ==============================================

def _measure(label, fn):
    """Run fn, then sample RAM and CPU right after."""

    fn()

    ram = _working_set_mb()
    cpu = _cpu_percent()

    return label, ram, cpu


def _measurement_rows():

    rows = []

    # 1. Idle: import the voice module but do NOT load the model.
    def _idle():
        from voice.whisper import AstraWhisper
        globals()["_whisper"] = AstraWhisper()

    rows.append(_measure("idle (whisper unloaded)", _idle))

    # 2. Whisper loaded.
    def _load():
        globals()["_whisper"]._load_model()

    rows.append(_measure("whisper loaded", _load))

    # 3. Transcribe the bundled test clip.
    def _transcribe():
        import time as _time

        clip = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "whisper_test.wav",
        )

        started = _time.monotonic()

        segments, _info = globals()["_whisper"].model.transcribe(
            clip,
            language="en",
            beam_size=5,
            best_of=3,
            vad_filter=True,
            no_speech_threshold=0.7,
        )

        text = " ".join(
            segment.text.strip() for segment in segments
        ).strip()

        elapsed = _time.monotonic() - started

        globals()["_transcribe_text"] = text
        globals()["_transcribe_seconds"] = elapsed

    _measure("transcribing", _transcribe)

    return rows


def main():

    print()
    print("================================================")
    print("       ASTRA PERFORMANCE PROBE")
    print("================================================")

    rows = _measurement_rows()

    print()
    print("State                  RAM (working set)   CPU (sample)")
    print("------------------------------------------------------")

    for label, ram, cpu in rows:

        print(f"{label:<22} {ram:>12.1f} MB      {cpu:>5.1f} %")

    print()
    print("Transcription (data/whisper_test.wav):")

    if "_transcribe_text" in globals():
        print(f"  text: {globals()['_transcribe_text']!r}")
        print(f"  seconds: {globals()['_transcribe_seconds']:.2f}")

    print()
    print("Note: CPU is a system-wide sample taken right after each")
    print("state, so it includes everything running on the machine.")

    return 0


if __name__ == "__main__":
    sys.exit(main())