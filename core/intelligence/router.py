"""
Intent routing by confidence.

AUTO      - confident enough to act immediately
CLARIFY   - ask for a missing detail or restate
UNKNOWN   - nothing usable was understood

Thresholds (Phase 6 spec §8):
    >= 0.85                act
    0.60 - 0.85            clarify only when an entity is missing
                           or the action is risky; otherwise act
    <  0.60                clarify
"""

from core.intelligence.intent import IntentType

AUTO_THRESHOLD = 0.85
CLARIFY_THRESHOLD = 0.60

# Intents that always need a concrete entity before acting.
ENTITY_REQUIRED = {
    IntentType.OPEN_APPLICATION,
    IntentType.OPEN_WEBSITE,
    IntentType.SEARCH_WEB,
    IntentType.FILE_OPERATION,
    IntentType.READ_FILE,
    IntentType.CREATE_FILE,
    IntentType.LIST_FILES,
    IntentType.CLOSE_APPLICATION,
}


def entity_satisfied(intent):
    """True when the intent carries the entity its action needs."""

    if intent.name not in ENTITY_REQUIRED:
        return True

    if intent.entities.get("application"):
        return True

    if intent.entities.get("target"):
        return True

    if intent.entities.get("site"):
        return True

    if intent.entities.get("query"):
        return True

    if intent.entities.get("path"):
        return True

    return bool(intent.entities.get("action") and intent.entities.get("path"))


def decide(intent):
    """Return AUTO, CLARIFY or UNKNOWN for an intent."""

    if intent.name == IntentType.UNKNOWN:
        return "UNKNOWN"

    if intent.confidence >= AUTO_THRESHOLD:
        return "AUTO"

    if intent.confidence < CLARIFY_THRESHOLD:
        return "CLARIFY"

    # 0.60 - 0.85: act when the entity is present and the action
    # is not risky; otherwise ask.
    if entity_satisfied(intent):
        return "AUTO"

    return "CLARIFY"