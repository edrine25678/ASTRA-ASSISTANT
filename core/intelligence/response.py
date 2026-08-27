"""
Spoken response generation.

Responses are drawn from small variant pools and rotated, so the
same action never sounds scripted.  Clarification questions and
error phrasing live here as well.
"""

from core.intelligence.intent import IntentType

OPEN_POOL = (
    "Sure. Opening {name}.",
    "Got it. Launching {name} now.",
    "{name} is open.",
)

SEARCH_POOL = (
    "Searching {engine} for {query}.",
    "Okay, searching {engine} for {query}.",
    "On it - searching {engine} for {query}.",
)

CLARIFY_POOL = (
    "I'm not sure I understood. Could you say that again?",
    "I didn't quite catch that. Can you repeat it?",
    "Sorry, I'm not sure what you meant by that.",
)

CLOSE_POOL = (
    "Done. I closed {name}.",
    "Okay, {name} has been closed.",
    "{name} is closed now.",
)

MISSING_ENTITY = {
    IntentType.OPEN_APPLICATION: "What would you like me to open?",
    IntentType.OPEN_WEBSITE: "Which website would you like me to open?",
    IntentType.SEARCH_WEB: "What would you like me to search for?",
    IntentType.FILE_OPERATION: "Which file or folder do you mean?",
    IntentType.READ_FILE: "Which file would you like me to read?",
    IntentType.CREATE_FILE: "What would you like me to create?",
    IntentType.LIST_FILES: "Which folder would you like me to list?",
    IntentType.CLOSE_APPLICATION: "What would you like me to close?",
}

UNKNOWN_RESPONSE = "I don't know how to do that yet."


class ResponseGenerator:

    def __init__(self):
        self._open_index = 0
        self._clarify_index = 0

    # ==============================================
    # VARIANTS
    # ==============================================

    def close_response(self, name, last_response=""):
        """A close confirmation, avoiding the exact last one."""

        pool = list(CLOSE_POOL)

        if last_response in pool:
            pool = [v for v in pool if v != last_response]

        variant = pool[self._open_index % len(pool)]

        self._open_index += 1

        return variant.format(name=name)

    def open_response(self, name, last_response=""):
        """A launch confirmation, avoiding the exact last one."""

        pool = list(OPEN_POOL)

        if last_response in pool:
            pool = [v for v in pool if v != last_response]

        variant = pool[self._open_index % len(pool)]

        self._open_index += 1

        return variant.format(name=name)

    def search_response(self, engine, query, last_response=""):

        pool = list(SEARCH_POOL)

        if last_response in pool:
            pool = [v for v in pool if v != last_response]

        variant = pool[self._open_index % len(pool)]

        return variant.format(engine=engine, query=query)

    def clarify_response(self):
        """Generic "I didn't understand" phrasing."""

        variant = CLARIFY_POOL[self._clarify_index % len(CLARIFY_POOL)]

        self._clarify_index += 1

        return variant

    def missing_entity_response(self, intent_name):
        """Ask for the detail a confident intent is missing."""

        return MISSING_ENTITY.get(
            intent_name, "Could you tell me a bit more?"
        )

    def unknown_response(self):
        return UNKNOWN_RESPONSE