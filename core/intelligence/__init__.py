"""
The intelligence layer: NLU, conversation memory, intent routing,
response generation, and the assistant orchestrator.

The assistant is intentionally not re-exported here: it depends on
the capability layer, which in turn depends on the intent constants,
so eager re-exporting creates an import cycle.  Import it directly:

    from core.intelligence.assistant import AstraAssistant
"""

from core.intelligence.intent import Intent, IntentType
from core.intelligence.context import ConversationContext
from core.intelligence.nlu import NLU
from core.intelligence.router import AUTO_THRESHOLD, CLARIFY_THRESHOLD, decide
from core.intelligence.response import ResponseGenerator

__all__ = [
    "AUTO_THRESHOLD",
    "CLARIFY_THRESHOLD",
    "ConversationContext",
    "Intent",
    "IntentType",
    "NLU",
    "ResponseGenerator",
    "decide",
]