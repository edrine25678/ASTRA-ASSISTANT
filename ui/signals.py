"""Central signal hub between the voice worker and the GUI.

Every message crossing the thread boundary goes through this single
object with queued Qt connections, so the GUI thread never touches
audio, Whisper, the brain or the speaker directly.
"""

from PySide6.QtCore import QObject, Signal


class UISignals(QObject):

    # The wake word was detected (emitted from the worker thread).
    wake_detected = Signal()

    # GUI state changed; payload is a ui.state value.
    status_changed = Signal(str)

    # The user's utterance was recognized.
    user_spoke = Signal(str)

    # Astra is about to speak this text.
    astra_speaking = Signal(str)

    # Astra finished speaking.
    speaking_finished = Signal()

    # The conversation window opened / timed out.
    conversation_open = Signal()
    conversation_closed = Signal()

    # AI provider status.  payload: (label, available)
    provider_status = Signal(str, bool)

    # Listening was paused or resumed.  payload: paused
    paused_changed = Signal(bool)

    # Requests from the GUI to pause/resume the wake listener.
    pause_requested = Signal()
    resume_requested = Signal()

    # Something failed but Astra keeps running.
    error_occurred = Signal(str)

    # The user asked Astra to shut down.
    exit_requested = Signal()