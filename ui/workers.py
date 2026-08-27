"""VoiceWorker: Astra's runtime loop in a background thread.

The GUI thread never touches audio, Whisper, the brain or the
speaker.  The worker owns the existing voice pipeline
(wake_word -> whisper -> assistant -> speaker) and mirrors the
behavior of core/astra.py, but communicates with the interface
through the ui.signals hub instead of console prints.

Thread-safety: pause/resume/stop/submit_text only touch threading
primitives, so they can be called from any thread.  Everything else
runs on the worker thread.
"""

import queue
import threading
import time

from PySide6.QtCore import QObject, Signal

from config.settings import CONVERSATION_TIMEOUT

from ui.state import LISTENING, THINKING


def provider_label(provider):
    """Human label for an AI provider (used by the overlay chip)."""

    name = getattr(provider, "name", "none") or "none"
    model = getattr(provider, "model_name", "") or ""

    if name == "ollama":
        return f"Local AI \u00b7 Ollama{(' \u00b7 ' + model) if model else ''}"

    if name == "local":
        return f"Local AI{(' \u00b7 ' + model) if model else ''}"

    if name == "cloud":
        return "Cloud AI"

    return "Local AI engine unavailable"


class VoiceWorker(QObject):

    # Emitted once when the run loop exits (after stop()).
    stopped = Signal()

    def __init__(self, signals, assistant=None, wake_word=None,
                 whisper=None, speaker=None):
        super().__init__()

        self._signals = signals
        self._assistant = assistant
        self._wake_word = wake_word
        self._whisper = whisper
        self._speaker = speaker

        self._stop = threading.Event()
        self._pause = threading.Event()
        self._wake_break = threading.Event()
        self._text_queue = queue.Queue()

        self._thread = None

    # ==============================================
    # CONTROL (safe from any thread)
    # ==============================================

    def start(self):
        if self.is_running():
            return

        self._stop.clear()
        self._pause.clear()
        self._wake_break.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="astra-voice-worker",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._wake_break.set()

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def is_running(self):
        return bool(self._thread is not None and self._thread.is_alive())

    def is_paused(self):
        return self._pause.is_set()

    def pause(self):
        self._pause.set()
        self._wake_break.set()  # Interrupt listen() if it's running
        self._signals.paused_changed.emit(True)

    def resume(self):
        self._pause.clear()
        self._signals.paused_changed.emit(False)

    def submit_text(self, text):
        """Queue a typed command (voice remains the primary input)."""

        text = (text or "").strip()

        if not text:
            return

        self._text_queue.put(text)
        self._wake_break.set()

    # ==============================================
    # RUN LOOP
    # ==============================================

    def _run(self):
        try:
            self._build_voice_components()
        except Exception as error:
            self._signals.error_occurred.emit(
                f"Could not start Astra: {error}"
            )
            self.stopped.emit()
            return

        threading.Thread(
            target=self._check_provider,
            name="astra-provider-check",
            daemon=True,
        ).start()

        try:
            while not self._stop.is_set():
                outcome = self._wait_for_wake()

                if outcome == "stop":
                    break

                if outcome == "text":
                    self._handle_idle_text()
                    continue

                self._session_after_wake()
        finally:
            self.stopped.emit()

    def _wait_for_wake(self):
        """Wait for the wake word, a typed command, pause or stop."""

        while not self._stop.is_set():
            if self._pause.is_set():
                time.sleep(0.2)
                continue

            # A text command may arrive right before the wait starts.
            self._wake_break.clear()

            if not self._text_queue.empty():
                return "text"

            try:
                result = self._wake_word.listen(
                    self._on_wake,
                    stop_event=self._stop,
                    break_event=self._wake_break,
                )
            except Exception as error:
                self._signals.error_occurred.emit(
                    f"Wake-word listener problem: {error}"
                )
                time.sleep(1.0)
                continue

            if result is False:
                return "stop"

            if self._wake_break.is_set():
                return "text"

            return "wake"

        return "stop"

    def _on_wake(self):
        # Runs on the audio callback thread; only records detection.
        # The signals are emitted from the worker thread after the
        # wait returns.
        pass

    def _session_after_wake(self):
        self._signals.wake_detected.emit()
        self._speak("Hey Edrine.")

        self._signals.status_changed.emit(LISTENING)

        text = self._listen_once()

        if not text:
            self._speak("I didn't hear you.")
            return

        self._process(text)
        self._conversation()

    def _conversation(self):
        """Keep listening after the wake word without repeating it."""

        self._signals.conversation_open.emit()

        last_heard = time.time()

        while not self._stop.is_set():

            if self._pause.is_set():

                if time.time() - last_heard >= CONVERSATION_TIMEOUT:
                    break

                time.sleep(0.2)
                continue

            if not self._text_queue.empty():

                last_heard = time.time()
                self._process(self._text_queue.get_nowait())
                continue

            text = self._listen_once()

            if not text:

                if time.time() - last_heard >= CONVERSATION_TIMEOUT:
                    break

                continue

            last_heard = time.time()
            self._process(text)

        self._signals.conversation_closed.emit()
        self._speak("I'll be here if you need me.")

    def _handle_idle_text(self):
        """A typed command arrived while Astra was waiting."""

        if self._text_queue.empty():
            return

        self._signals.status_changed.emit(LISTENING)
        self._process(self._text_queue.get_nowait())

    # ==============================================
    # STEPS
    # ==============================================

    def _listen_once(self):
        try:
            return (self._whisper.listen() or "").strip()
        except Exception as error:
            self._signals.error_occurred.emit(
                f"Speech recognition problem: {error}"
            )
            return ""

    def _process(self, text):
        self._signals.user_spoke.emit(text)
        self._signals.status_changed.emit(THINKING)

        try:
            result = self._assistant.process(text)
        except Exception as error:
            self._signals.error_occurred.emit(
                f"Processing problem: {error}"
            )
            return

        if result is not None and getattr(result, "exit", False):
            self._signals.exit_requested.emit()
            self.stop()
            return

        response = (
            result.response
            if result is not None and getattr(result, "response", None)
            else ""
        )

        self._speak(response)

    def _speak(self, text):
        if not text:
            self._signals.speaking_finished.emit()
            return

        self._signals.astra_speaking.emit(text)

        try:
            self._speaker.speak(text)
        except Exception as error:
            self._signals.error_occurred.emit(
                f"Speech output problem: {error}"
            )
        finally:
            self._signals.speaking_finished.emit()

    # ==============================================
    # SETUP
    # ==============================================

    def _build_voice_components(self):
        """Build (or reuse injected) voice objects on this thread."""

        if self._assistant is None:
            from core.brain import AstraBrain
            from core.intelligence.assistant import AstraAssistant

            self._assistant = AstraAssistant(brain=AstraBrain())

        if self._wake_word is None:
            from voice.wake_word import AstraWakeWord

            self._wake_word = AstraWakeWord()

        if self._whisper is None:
            from voice.whisper import AstraWhisper

            self._whisper = AstraWhisper()

        if self._speaker is None:
            from voice.speaker import AstraSpeaker

            self._speaker = AstraSpeaker()

    def _check_provider(self):
        """Report AI provider status without blocking the voice loop."""

        try:
            from ai import build_provider

            provider = build_provider()

            available = bool(provider.available())

            label = provider_label(provider)

            if not self._stop.is_set():
                self._signals.provider_status.emit(label, available)
        except Exception:
            if not self._stop.is_set():
                self._signals.provider_status.emit(
                    "Local AI engine unavailable", False
                )
