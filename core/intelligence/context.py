"""
Bounded conversation memory for the intelligence layer.

Keeps the most recent turns (message cap), caps the total stored
text (token cap), tracks the current topic and the last entity
mentioned, and remembers the last assistant response so the
personality layer can avoid repeating itself.

History is deliberately bounded: nothing grows without limit.
"""

from config.settings import MAX_CONTEXT_MESSAGES, MAX_CONTEXT_TOKENS


class ConversationContext:

    def __init__(self, max_messages=None, max_tokens=None):

        self.max_messages = (
            max_messages if max_messages is not None
            else MAX_CONTEXT_MESSAGES
        )

        self.max_tokens = (
            max_tokens if max_tokens is not None
            else MAX_CONTEXT_TOKENS
        )

        self.turns = []
        self.topic = None
        self.last_entity = None
        self.last_response = ""
        self.pending_clarification = None
        self.current_location = None
        # Backward-compatible fields used by the Phase 5 brain.
        self.last_site = None
        self.pending_call = None

    # ==============================================
    # TURNS
    # ==============================================

    def add_turn(self, user_text, assistant_text):
        """Record one exchange, bounded by both caps."""

        self.turns.append(
            {"user": user_text, "assistant": assistant_text}
        )

        self.last_response = assistant_text

        while len(self.turns) > self.max_messages:
            self.turns.pop(0)

        while self._token_count() > self.max_tokens and len(self.turns) > 1:
            self.turns.pop(0)

    def _token_count(self):

        count = 0

        for turn in self.turns:
            count += len(turn["user"].split())
            count += len(turn["assistant"].split())

        return count

    def history(self, limit=None):
        """Recent history as a flat [(role, text), ...] list."""

        if limit is None:
            limit = self.max_messages

        flat = []

        for turn in self.turns[-limit:]:
            flat.append(("user", turn["user"]))
            flat.append(("assistant", turn["assistant"]))

        return flat

    def last_user_text(self):
        """The most recent user utterance, or ""."""

        if not self.turns:
            return ""

        return self.turns[-1]["user"]

    def set_last_site(self, site):
        """Remember the last browser site for follow-up requests."""
        self.last_site = site

    # ==============================================
    # TOPIC
    # ==============================================

    def set_topic(self, topic, entity=None):
        """Remember what the conversation is currently about."""

        self.topic = topic

        if entity is not None:
            self.last_entity = entity

    def clear(self):

        self.turns = []
        self.topic = None
        self.last_entity = None
        self.last_response = ""
        self.pending_clarification = None
        self.current_location = None
        # Backward-compatible fields used by the Phase 5 brain.
        self.last_site = None
        self.pending_call = None