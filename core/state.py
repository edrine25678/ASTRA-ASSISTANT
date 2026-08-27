"""
Astra's conversation state machine.

States are explicit, transitions are validated, and every
conversation flows through them in order:

    IDLE
        -> LISTENING_FOR_WAKE_WORD     waiting for the wake word
        -> LISTENING_FOR_COMMAND       waiting for a command
        -> CONVERSATION                natural conversation
        -> EXECUTING                   acting on what was heard
        -> RESPONDING                  producing the reply
        -> LISTENING_FOR_WAKE_WORD     conversation timed out

No booleans: the state is a single value, so invalid transitions
are caught instead of silently mishandled.
"""

from core.logger import get_logger

logger = get_logger("core.state")

IDLE = "idle"
LISTENING_FOR_WAKE_WORD = "listening_for_wake_word"
LISTENING_FOR_COMMAND = "listening_for_command"
CONVERSATION = "conversation"
EXECUTING = "executing"
RESPONDING = "responding"

VALID_TRANSITIONS = {
    IDLE: {LISTENING_FOR_WAKE_WORD},
    LISTENING_FOR_WAKE_WORD: {
        LISTENING_FOR_COMMAND,
        IDLE,
    },
    LISTENING_FOR_COMMAND: {
        EXECUTING,
        LISTENING_FOR_WAKE_WORD,
    },
    CONVERSATION: {
        EXECUTING,
        LISTENING_FOR_WAKE_WORD,
        IDLE,
    },
    EXECUTING: {
        RESPONDING,
    },
    RESPONDING: {
        LISTENING_FOR_WAKE_WORD,
        CONVERSATION,
        IDLE,
    },
}


class AstraState:

    def __init__(self):
        self.state = IDLE

    @property
    def current(self):
        return self.state

    def transition(self, new_state):
        """Move to a new state, validating the transition."""

        if new_state not in VALID_TRANSITIONS[self.state]:

            logger.warning(
                "Invalid state transition: %s -> %s",
                self.state,
                new_state,
            )

            return False

        self.state = new_state

        logger.debug("State: %s", self.state)

        return True

    def is_waiting_for_wake_word(self):
        return self.state == LISTENING_FOR_WAKE_WORD

    def is_conversing(self):
        return self.state == CONVERSATION

    def reset(self):
        self.state = IDLE