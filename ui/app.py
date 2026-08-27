"""Astra's floating-interface application.

Boots the Qt application, wires the overlay / tray / worker through
the central signal hub, and owns clean shutdown.  The GUI is only a
view: the VoiceWorker talks to the same Astra brain, tools and
safety pipeline as every other interface.
"""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.overlay import AstraOverlay
from ui.signals import UISignals
from ui.state import ERROR, IDLE, LISTENING, SPEAKING, THINKING
from ui.tray import AstraTray
from ui.workers import VoiceWorker


class AstraUi:

    def __init__(self, app, signals, overlay, tray, worker):
        self._app = app
        self._signals = signals
        self._overlay = overlay
        self._tray = tray
        self._worker = worker

        self._session_open = False
        self._shutting_down = False
        self._boot_peek = True

        self._wire()

    # ==============================================
    # WIRING
    # ==============================================

    def _wire(self):
        s = self._signals

        # Voice worker -> interface (queued to the GUI thread).
        s.wake_detected.connect(self._on_wake_detected)
        s.status_changed.connect(self._on_status_changed)
        s.user_spoke.connect(self._on_user_spoke)
        s.astra_speaking.connect(self._on_astra_speaking)
        s.speaking_finished.connect(self._on_speaking_finished)
        s.conversation_open.connect(self._on_conversation_open)
        s.conversation_closed.connect(self._on_conversation_closed)
        s.provider_status.connect(self._on_provider_status)
        s.paused_changed.connect(self._on_paused_changed)
        s.error_occurred.connect(self._on_error)
        s.exit_requested.connect(self._shutdown)
        s.pause_requested.connect(self._worker.pause)
        s.resume_requested.connect(self._worker.resume)

        self._worker.stopped.connect(self._on_worker_stopped)

        # Interface -> worker (thread-safe primitives, direct).
        self._overlay.text_submitted.connect(
            self._worker.submit_text
        )

        self._app.aboutToQuit.connect(self._worker.stop)

    # ==============================================
    # EVENTS
    # ==============================================

    def _on_wake_detected(self):
        self._session_open = True
        self._overlay.clear_transcript()
        self._overlay.cancel_hide()
        self._overlay.show_overlay()
        self._overlay.set_status(LISTENING)

    def _on_status_changed(self, mode):
        if mode == LISTENING and not self._overlay.isVisible():
            self._overlay.show_overlay()

        self._overlay.set_status(mode)

        if mode == THINKING:
            self._overlay.cancel_hide()

    def _on_user_spoke(self, text):
        if not self._overlay.isVisible():
            self._overlay.show_overlay()

        self._overlay.cancel_hide()
        self._overlay.add_user_text(text)
        self._overlay.set_status(LISTENING)

    def _on_astra_speaking(self, text):
        self._overlay.cancel_hide()
        self._overlay.set_status(SPEAKING, text)
        self._overlay.add_astra_text(text)

    def _on_speaking_finished(self):
        self._overlay.set_status(IDLE)

        if not self._session_open:
            if self._boot_peek:
                # Boot peek consumed: the overlay may now go quiet again.
                self._boot_peek = False

            self._overlay.schedule_hide()

    def _on_conversation_open(self):
        self._session_open = True
        self._overlay.cancel_hide()

    def _on_conversation_closed(self):
        self._session_open = False

    def _on_provider_status(self, label, available):
        self._overlay.set_provider(label, available)

    def _on_paused_changed(self, paused):
        self._overlay.set_status(
            IDLE,
            "Listening paused" if paused else "Listening",
        )

    def _on_error(self, message):
        self._overlay.show_overlay()
        self._overlay.set_status(
            ERROR,
            "Something went wrong",
        )
        self._overlay.schedule_hide(3)

    # ==============================================
    # SHUTDOWN
    # ==============================================

    def _on_worker_stopped(self):
        if self._shutting_down:
            self._app.quit()

    def _shutdown(self):
        if self._shutting_down:
            return

        self._shutting_down = True

        self._overlay.hide()
        self._tray.hide()
        self._worker.stop()
        self._worker.join(timeout=5)

        if not self._worker.is_running():
            self._app.quit()


def run_gui(argv=None):
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("Astra")
    app.setApplicationDisplayName("Astra")
    app.setQuitOnLastWindowClosed(False)

    signals = UISignals()
    overlay = AstraOverlay()
    tray = AstraTray(None, signals, overlay)
    worker = VoiceWorker(signals)

    AstraUi(app, signals, overlay, tray, worker)

    tray.show()
    worker.start()

    # Boot peek: keep the overlay visible at startup (no auto-hide) so
    # the user can see the interface; it goes quiet after the first
    # spoken exchange.
    QTimer.singleShot(600, overlay.show_overlay)

    try:
        return app.exec()
    except KeyboardInterrupt:
        worker.stop()
        worker.join(timeout=5)
        return 0