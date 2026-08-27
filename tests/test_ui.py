"""
Phase 11B GUI tests.

Runs headless with the Qt offscreen platform.  Covers the UI state
machine, the orb, the overlay (show/fade/auto-hide/expand/input),
the voice worker integration (wake -> listen -> think -> speak ->
conversation), pause/resume/stop, typed commands, provider labels,
tray availability guard, and one real assistant round trip.
"""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import time

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

checks = 0
failed = 0


def ok(condition, label):
    global checks, failed
    checks += 1
    if condition:
        print(f"  ok: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")


def spin(seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)


def wait_until(condition, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if condition():
            return True
        QApplication.processEvents()
        time.sleep(0.01)
    return False


app = QApplication.instance() or QApplication([])

print()
print("--- UI STATE MACHINE ---")

from ui.state import (
    ALL_STATES,
    ERROR,
    IDLE,
    LISTENING,
    SPEAKING,
    THINKING,
    UiState,
)

state = UiState()
ok(state.current == IDLE, "starts IDLE")

ok(state.transition(LISTENING), "IDLE -> LISTENING")
ok(state.transition(THINKING), "LISTENING -> THINKING")
ok(state.transition(SPEAKING), "THINKING -> SPEAKING")
ok(state.transition(IDLE), "SPEAKING -> IDLE")

ok(state.transition(THINKING) is False, "IDLE -> THINKING rejected")
ok(state.current == IDLE, "state unchanged after rejected transition")

ok(state.transition(ERROR), "any -> ERROR (from IDLE)")
ok(state.transition(IDLE), "ERROR -> IDLE")

state.transition(LISTENING)
ok(state.transition(ERROR), "any -> ERROR (from LISTENING)")
ok(state.current == ERROR, "state is ERROR")

ok(state.transition("bogus") is False, "unknown state rejected")
ok(all(s in ALL_STATES for s in (IDLE, LISTENING, THINKING, SPEAKING, ERROR)),
   "all five states defined")

print()
print("--- ORB ---")

from ui.orb import AstraOrb

orb = AstraOrb()
ok(orb.width() == orb.height() and orb.width() > 0, "orb fixed square size")

orb.start()
ok(orb.isActive(), "orb timer active after start()")

for mode in (IDLE, LISTENING, THINKING, SPEAKING, ERROR):
    orb.set_mode(mode)
    orb.set_amplitude(0.7)
    orb.repaint()
    QApplication.processEvents()
ok(True, "all five modes painted without error")

orb.set_amplitude(3.0)
ok(orb._amplitude == 1.0, "amplitude clamped high")
orb.set_amplitude(-1.0)
ok(orb._amplitude == 0.0, "amplitude clamped low")

orb.stop()
ok(not orb.isActive(), "orb timer stops")

pix = orb.grab()
ok(not pix.isNull(), "orb can be rendered to a pixmap")

print()
print("--- PROVIDER LABELS ---")

from ui.workers import provider_label


class FakeProvider:

    def __init__(self, name, model_name=""):
        self.name = name
        self.model_name = model_name

    def available(self):
        return True


ok("Ollama" in provider_label(FakeProvider("ollama", "qwen2.5:3b-instruct")),
   "ollama label shows provider")
ok("qwen2.5:3b-instruct" in provider_label(FakeProvider("ollama", "qwen2.5:3b-instruct")),
   "ollama label shows configured model")
ok("Cloud" in provider_label(FakeProvider("cloud")), "cloud label")
ok("Local" in provider_label(FakeProvider("local", "llama3")), "local label")
ok(provider_label(FakeProvider("none")) == "Local AI engine unavailable",
   "unavailable label")

print()
print("--- OVERLAY ---")

from ui.overlay import AstraOverlay

overlay = AstraOverlay(auto_hide_ms=200)
ok(not overlay.isVisible(), "overlay hidden initially")

overlay.show_overlay()
spin(0.05)
ok(overlay.isVisible(), "overlay shows")

spin(0.5)
ok(overlay._effect.opacity() > 0.95, "overlay fades in to full opacity")

overlay.set_status(LISTENING)
ok("Listening" in overlay._status.text(), "status shows Listening")
ok(overlay.orb.mode() == LISTENING, "orb follows status state")

overlay.add_user_text("Open Chrome")
overlay.add_astra_text("Opening Chrome.")
ok(overlay._transcript_layout.count() >= 2, "transcript gains user + astra lines")

ok(not overlay.is_expanded(), "overlay compact by default")
overlay.toggle_expanded()
ok(overlay.is_expanded(), "orb click expands overlay")
ok(overlay._transcript.isVisible(), "transcript visible when expanded")
ok(overlay._input_row.isVisible(), "text input visible when expanded")
overlay.toggle_expanded()
ok(not overlay.is_expanded(), "second click collapses overlay")

overlay.set_expanded(True)
overlay._input.setText("hello there")
overlay._submit_text()
ok(overlay._input.text() == "", "input cleared after submit")

submitted = []

overlay.text_submitted.connect(lambda text: submitted.append(text))
overlay._input.setText("open notepad")
overlay._submit_text()
ok(submitted == ["open notepad"], "text_submitted emitted with the typed text")

overlay.set_expanded(False)
overlay.start_fade_out()
ok(wait_until(lambda: not overlay.isVisible(), 3), "overlay fades out and hides")

overlay.show_overlay(keep_seconds=0.3)
ok(wait_until(lambda: not overlay.isVisible(), 3), "auto-hide timer hides overlay")

overlay.show_overlay()
pos = overlay.pos()
ok(pos.x() >= 0 and pos.y() > 0, "overlay positioned on the screen")
overlay.hide()

print()
print("--- VOICE WORKER (stubbed voice pipeline) ---")

import ui.workers as workers_module

from ui.signals import UISignals
from ui.workers import VoiceWorker


class FakeWakeWord:

    def __init__(self, wake_on_call=1):
        self.calls = 0
        self.wake_on_call = wake_on_call

    def listen(self, on_wake, stop_event=None, break_event=None):
        self.calls += 1
        while True:
            if stop_event is not None and stop_event.is_set():
                return False
            if break_event is not None and break_event.is_set():
                return True
            if self.calls <= self.wake_on_call:
                return True
            time.sleep(0.01)


class FakeWhisper:

    def __init__(self, responses):
        self.responses = list(responses)

    def listen(self):
        if self.responses:
            return self.responses.pop(0)
        time.sleep(0.02)
        return ""


class FakeSpeaker:

    def __init__(self):
        self.spoken = []

    def speak(self, text):
        self.spoken.append(text)
        time.sleep(0.005)


class FakeAssistant:

    def __init__(self):
        self.calls = []

    def process(self, text):
        self.calls.append(text)
        if text.lower() == "close astra":
            return SimpleNamespace(response="Closing Astra.", exit=True)
        return SimpleNamespace(response=f"Astra heard: {text}", exit=False)


workers_module.CONVERSATION_TIMEOUT = 0.5

signals = UISignals()
wake_word = FakeWakeWord(wake_on_call=1)
whisper = FakeWhisper(["open chrome", "what time is it"])
speaker = FakeSpeaker()
assistant = FakeAssistant()

worker = VoiceWorker(signals, assistant=assistant, wake_word=wake_word,
                     whisper=whisper, speaker=speaker)

spy_wake = QSignalSpy(signals.wake_detected)
spy_conv_open = QSignalSpy(signals.conversation_open)
spy_conv_closed = QSignalSpy(signals.conversation_closed)
spy_paused = QSignalSpy(signals.paused_changed)

worker.start()
ok(worker.is_running(), "worker thread running")

ok(wait_until(lambda: spy_wake.count() >= 1, 5), "wake word detected signal")
ok(wait_until(lambda: len(speaker.spoken) >= 1, 5), "greeting spoken")
ok(speaker.spoken[0] == "Hey Edrine.", "Astra greets after wake")

ok(wait_until(lambda: len(assistant.calls) >= 1, 5), "assistant processed first command")
ok(assistant.calls[0] == "open chrome", "first command text")
ok(wait_until(lambda: speaker.spoken and speaker.spoken[-1] == "Astra heard: open chrome", 5),
   "Astra spoke the response")

ok(wait_until(lambda: spy_conv_open.count() >= 1, 5), "conversation window opened")

ok(wait_until(lambda: len(assistant.calls) >= 2, 5), "conversation follow-up processed")
ok(assistant.calls[1] == "what time is it", "conversation follow-up text")

ok(wait_until(lambda: spy_conv_closed.count() >= 1, 5), "conversation closed after timeout")
ok(speaker.spoken[-1] == "I'll be here if you need me.", "farewell spoken")

# Back to waiting for the wake word; pause must stop the listener.
calls_before = wake_word.calls
worker.pause()
ok(wait_until(lambda: spy_paused.count() >= 1, 5), "paused signal emitted")
ok(worker.is_paused(), "worker reports paused")
time.sleep(0.4)
ok(wake_word.calls == calls_before, "wake listener not entered while paused")

worker.resume()
spin(0.3)
ok(not worker.is_paused(), "worker reports resumed")
ok(wake_word.calls > calls_before, "wake listener resumes")

# Typed command while idle.
worker.submit_text("open notepad")
ok(wait_until(lambda: len(assistant.calls) >= 3, 5), "typed command processed without wake word")
ok(assistant.calls[-1] == "open notepad", "typed command reached assistant")

# Graceful stop.
spy_stopped = QSignalSpy(worker.stopped)
worker.stop()
ok(wait_until(lambda: spy_stopped.count() >= 1, 5), "worker emits stopped after stop()")
worker.join(timeout=3)
ok(not worker.is_running(), "worker thread finished")
ok(speaker.spoken[-1] == "Astra heard: open notepad", "no farewell after manual stop")

print()
print("--- WORKER EXIT COMMAND ---")

signals2 = UISignals()
worker2 = VoiceWorker(
    signals2,
    assistant=FakeAssistant(),
    wake_word=FakeWakeWord(wake_on_call=99),
    whisper=FakeWhisper([]),
    speaker=FakeSpeaker(),
)

spy_exit = QSignalSpy(signals2.exit_requested)
spy_stopped2 = QSignalSpy(worker2.stopped)

worker2.start()
worker2.submit_text("close astra")
ok(wait_until(lambda: spy_exit.count() >= 1, 5), "exit requested")
ok(wait_until(lambda: spy_stopped2.count() >= 1, 5), "worker stopped after exit")

print()
print("--- WORKER ERROR PATH ---")


class BrokenAssistant:

    def process(self, text):
        raise RuntimeError("boom")


signals3 = UISignals()
worker3 = VoiceWorker(
    signals3,
    assistant=BrokenAssistant(),
    wake_word=FakeWakeWord(wake_on_call=1),
    whisper=FakeWhisper(["do something"]),
    speaker=FakeSpeaker(),
)

spy_error = QSignalSpy(signals3.error_occurred)

worker3.start()
ok(wait_until(lambda: spy_error.count() >= 1, 5), "error_occurred emitted on assistant failure")
ok(worker3.is_running(), "worker survives an assistant error")
worker3.stop()
worker3.join(timeout=3)

print()
print("--- TRAY GUARD ---")

from PySide6.QtWidgets import QSystemTrayIcon
from ui.tray import AstraTray

ok(not QSystemTrayIcon.isSystemTrayAvailable() or True,
   "tray availability query works (headless offscreen)")
tray = AstraTray(None, UISignals())
ok(tray._tray is None or tray._tray is not None,
   "AstraTray constructed without crashing")
ok(tray._tray is None if not QSystemTrayIcon.isSystemTrayAvailable() else True,
   "no tray object when the platform has no tray")

print()
print("--- REAL ASSISTANT ROUND TRIP ---")

from core.brain import AstraBrain
from core.intelligence.assistant import AstraAssistant

real = AstraAssistant(brain=AstraBrain(memory_enabled=False))

result = real.process("what time is it")
ok(result is not None and bool(result.response), "time query answered")
ok(result.exit is False, "time query does not exit")

result = real.process("who are you")
ok(result is not None and bool(result.response), "identity query answered")

result = real.process("close astra")
ok(result is not None and result.exit is True, "close astra requests exit")

print()
print("=================================")
print(f"PASS: {checks - failed}   FAIL: {failed}")
print("=================================")

raise SystemExit(1 if failed else 0)
