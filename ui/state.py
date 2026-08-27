"""Central GUI state machine (Phase 11B).

The overlay must not flip between visual states from scattered
places, so every visual state transition goes through this one
machine.  It is pure Python and fully testable without Qt.

    IDLE
        -> LISTENING   wake word detected, microphone open
        -> THINKING    speech recognized, intelligence working
        -> SPEAKING    response ready, Astra talking
        -> IDLE        speech finished
    Any -> ERROR       something failed
    ERROR -> IDLE      recovered
"""

IDLE = "idle"
LISTENING = "listening"
THINKING = "thinking"
SPEAKING = "speaking"
ERROR = "error"

ALL_STATES = (IDLE, LISTENING, THINKING, SPEAKING, ERROR)

VALID_TRANSITIONS = {
    IDLE: {LISTENING, ERROR},
    LISTENING: {THINKING, SPEAKING, ERROR},
    THINKING: {SPEAKING, ERROR},
    SPEAKING: {IDLE, LISTENING, ERROR},
    ERROR: {IDLE},
}


class UiState:

    def __init__(self, initial=IDLE):
        self._state = initial if initial in ALL_STATES else IDLE

    @property
    def current(self):
        return self._state

    def transition(self, new_state):
        """Move to a new state, validating the transition.

        Returns True on success and False on invalid transitions
        (the state is left unchanged).
        """

        if new_state not in ALL_STATES:
            return False

        if new_state == self._state:
            return True

        if new_state not in VALID_TRANSITIONS[self._state]:
            return False

        self._state = new_state

        return True
