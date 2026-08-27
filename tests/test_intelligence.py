"""
Phase 6 intelligence-layer tests: NLU, conversation memory,
routing, discovery, capabilities, response generation and the
AstraAssistant orchestrator.

Run from the project root:

    python tests/test_intelligence.py

Tools are stubbed so no application is ever launched and no
browser is ever opened.
"""

import os
import re
import sys
import tempfile

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from datetime import datetime

from core.brain import AstraBrain
from core.capabilities import ApplicationDiscovery
from core.intelligence import (
    ConversationContext,
    Intent,
    IntentType,
    NLU,
    ResponseGenerator,
    decide,
)
from core.intelligence.assistant import AstraAssistant
from core.intelligence.router import entity_satisfied

from tools.base import AstraTool, ToolResult
from tools.registry import ToolRegistry
from tools.safety import ToolSafety


_PASS = 0
_FAIL = 0


def _check(label, actual, expected):

    global _PASS, _FAIL

    if actual == expected:

        _PASS += 1

        return True

    _FAIL += 1

    print(f"FAIL: {label}")
    print(f"  expected: {expected!r}")
    print(f"  actual:   {actual!r}")

    return False


def _check_true(label, condition):

    global _PASS, _FAIL

    if condition:

        _PASS += 1

        return True

    _FAIL += 1

    print(f"FAIL: {label} (condition was False)")
    print(f"  {condition!r}")

    return False


# ==============================================
# TEST DOUBLES
# ==============================================

class AllowAllSafety(ToolSafety):
    ALLOWED_TOOLS = {
        "open_application",
        "open_url",
        "search_web",
        "get_time",
        "get_date",
        "system_info",
        "file_search",
        "file_list_directory",
        "file_open_file",
        "file_open_folder",
        "file_read_text",
        "file_create_text",
        "file_delete",
    }


class StubTool(AstraTool):

    def __init__(self, name, respond):
        self._name = name
        self._respond = respond
        self.parameters = {}

    @property
    def name(self):
        return self._name

    def run(self, arguments):
        return ToolResult(
            success=True,
            response=self._respond(arguments),
            data=arguments,
        )


def _open_response(arguments):
    app = (arguments.get("application") or "").title()
    return f"Opening {app}."


def _search_response(arguments):
    query = arguments.get("query")
    engine = arguments.get("engine") or "google"
    return f"Searching {engine} for {query}."


def _url_response(arguments):
    return f"Opening {arguments.get('url')}."


def _time_response(arguments):
    return "The current time is 3:45 PM."


def _date_response(arguments):
    return "Today is Friday, August 14, 2026."


def _delete_response(arguments):
    return f"I deleted {arguments.get('path')}."


def _stub_registry():

    registry = ToolRegistry(safety=AllowAllSafety())

    registry.register(StubTool("open_application", _open_response))
    registry.register(StubTool("search_web", _search_response))
    registry.register(StubTool("open_url", _url_response))
    registry.register(StubTool("get_time", _time_response))
    registry.register(StubTool("get_date", _date_response))
    registry.register(StubTool("system_info", _url_response))
    registry.register(StubTool("file_delete", _delete_response))

    return registry


class FakeDiscovery:

    APPS = {
        "chrome": "chrome",
        "browser": "chrome",
        "notepad": "notepad",
        "calculator": "calculator",
        "spotify": "spotify",
        "obsidian": "obsidian",
    }

    def find(self, phrase):

        key = (phrase or "").strip().lower()

        if key in self.APPS:
            return {"name": self.APPS[key], "display": self.APPS[key]}

        return None


def _assistant():

    brain = AstraBrain(
        registry=_stub_registry(),
        memory_enabled=False,
    )

    return AstraAssistant(
        brain=brain,
        discovery=FakeDiscovery(),
    )


OPEN_VARIANTS = {
    "Sure. Opening Chrome.",
    "Got it. Launching Chrome now.",
    "Chrome is open.",
}


# ==============================================
# THE EIGHT SPEC CONVERSATIONS (§20)
# ==============================================

def test_spec_conversations():

    print()
    print("--- THE EIGHT SPEC CONVERSATIONS ---")

    # 1. "Open Chrome."
    assistant = _assistant()

    result = assistant.process("open chrome")

    _check_true("1. open chrome", result.response in OPEN_VARIANTS)

    # 2. "Could you open Chrome for me?"
    assistant = _assistant()

    result = assistant.process("could you open chrome for me")

    _check_true("2. polite open", result.response in OPEN_VARIANTS)

    # 3. "Launch Chrome for me."
    assistant = _assistant()

    result = assistant.process("launch chrome for me")

    _check_true("3. launch chrome", result.response in OPEN_VARIANTS)

    # 4. "Start my browser."
    assistant = _assistant()

    result = assistant.process("start my browser")

    _check_true("4. start my browser", result.response in OPEN_VARIANTS)

    # 5. "I want Chrome."
    assistant = _assistant()

    result = assistant.process("i want chrome")

    _check_true("5. i want chrome", result.response in OPEN_VARIANTS)

    # 6. "Can you bring up the browser?"
    assistant = _assistant()

    result = assistant.process("can you bring up the browser")

    _check_true("6. bring up browser", result.response in OPEN_VARIANTS)

    # 7. "Open it." -> "What would you like me to open?"
    assistant = _assistant()

    result = assistant.process("open it")

    _check(
        "7. open it clarifies",
        result.response,
        "What would you like me to open?",
    )

    # 8. "And tomorrow?" after the time.
    assistant = _assistant()

    result = assistant.process("what time is it")

    _check_true(
        "8. time first", result.response.startswith("The current time is")
    )

    result = assistant.process("and tomorrow?")

    _check_true(
        "8. tomorrow after time",
        result.response.startswith("Tomorrow will be"),
    )


# ==============================================
# THE SPEC EXAMPLE CONVERSATIONS (§13)
# ==============================================

def test_search_web_clarifies_then_searches():

    print()
    print("--- SEARCH WEB CLARIFICATION ---")

    assistant = _assistant()

    result = assistant.process("search the web")

    _check(
        "bare search asks for topic",
        result.response,
        "What would you like me to search for?",
    )

    result = assistant.process("python multiprocessing")

    _check(
        "answer searched",
        result.response,
        "Searching google for python multiprocessing.",
    )


def test_delete_folder_clarifies():

    print()
    print("--- PRONOUN FILE ACTION ---")

    assistant = _assistant()

    result = assistant.process("delete that folder")

    _check(
        "pronoun folder asks which",
        result.response,
        "Which folder do you mean?",
    )

    result = assistant.process("the downloads folder")

    _check(
        "brain confirms destructive delete",
        result.response,
        "Are you sure you want me to do that?",
    )

    result = assistant.process("yes")

    _check_true(
        "answered folder deletes",
        result.response.startswith("I deleted"),
    )


def test_open_it_then_answer():

    print()
    print("--- OPEN IT -> ANSWER ---")

    assistant = _assistant()

    result = assistant.process("open it")

    _check(
        "pronoun open clarifies",
        result.response,
        "What would you like me to open?",
    )

    result = assistant.process("chrome")

    _check("answer opens chrome", result.response, "Opening Chrome.")


# ==============================================
# NLU
# ==============================================

def test_nlu_semantic_open():

    print()
    print("--- NLU SEMANTIC OPEN ---")

    nlu = NLU(discovery=FakeDiscovery(), brain=None)
    context = ConversationContext()

    cases = {
        "load chrome": ("chrome", 0.8),
        "show me notepad": ("notepad", 0.95),
        "get me the calculator": ("calculator", 0.95),
        "fire up spotify": ("spotify", 0.95),
    }

    for text, (app, confidence) in cases.items():

        intent = nlu.resolve(text, context)

        _check(
            f"nlu {text!r} name",
            intent.name,
            IntentType.OPEN_APPLICATION,
        )

        _check(
            f"nlu {text!r} app",
            intent.entities.get("application"),
            app,
        )

        _check(
            f"nlu {text!r} confidence",
            intent.confidence,
            confidence,
        )

    # The alias "browser" resolves through discovery.
    intent = nlu.resolve("open the browser", context)

    _check(
        "nlu browser alias",
        intent.entities.get("application"),
        "chrome",
    )

    # Unknown stays unknown.
    intent = nlu.resolve("dance for me", context)

    _check("nlu unknown", intent.name, IntentType.UNKNOWN)


def test_nlu_date_ellipsis():

    print()
    print("--- NLU DATE ELLIPSIS ---")

    nlu = NLU(discovery=FakeDiscovery(), brain=None)

    context = ConversationContext()
    context.set_topic(IntentType.GET_TIME)

    intent = nlu.resolve("and tomorrow?", context)

    _check("and tomorrow intent", intent.name, IntentType.GET_DATE)
    _check("and tomorrow day", intent.entities.get("day"), "tomorrow")

    intent = nlu.resolve("what about next week", context)

    _check("next week intent", intent.name, IntentType.GET_DATE)
    _check("next week day", intent.entities.get("day"), "next week")

    # Without a time/date topic the ellipse stays unknown.
    fresh = ConversationContext()

    intent = nlu.resolve("and tomorrow?", fresh)

    _check("no context stays unknown", intent.name, IntentType.UNKNOWN)


def test_nlu_bare_search():

    print()
    print("--- NLU BARE SEARCH ---")

    nlu = NLU(discovery=FakeDiscovery(), brain=None)

    for text in ("search the web", "can you search the internet"):

        intent = nlu.resolve(text, ConversationContext())

        _check(f"bare search {text!r}", intent.name, IntentType.SEARCH_WEB)

        _check(
            f"bare search no query {text!r}",
            intent.entities.get("query"),
            None,
        )


# ==============================================
# ROUTER
# ==============================================

def test_router_confidence():

    print()
    print("--- ROUTER CONFIDENCE ---")

    _check(
        "unknown routes to UNKNOWN",
        decide(Intent(name=IntentType.UNKNOWN)),
        "UNKNOWN",
    )

    _check(
        "0.95 with entity is AUTO",
        decide(Intent(
            name=IntentType.OPEN_APPLICATION,
            confidence=0.95,
            entities={"application": "chrome"},
        )),
        "AUTO",
    )

    _check(
        "0.85 is AUTO even without entity",
        decide(Intent(
            name=IntentType.OPEN_APPLICATION,
            confidence=0.85,
        )),
        "AUTO",
    )

    _check(
        "0.70 without entity is CLARIFY",
        decide(Intent(
            name=IntentType.OPEN_APPLICATION,
            confidence=0.70,
        )),
        "CLARIFY",
    )

    _check(
        "0.70 with entity is AUTO",
        decide(Intent(
            name=IntentType.OPEN_APPLICATION,
            confidence=0.70,
            entities={"application": "chrome"},
        )),
        "AUTO",
    )

    _check(
        "0.80 search without query is CLARIFY",
        decide(Intent(
            name=IntentType.SEARCH_WEB,
            confidence=0.80,
        )),
        "CLARIFY",
    )

    _check(
        "0.50 is CLARIFY",
        decide(Intent(
            name=IntentType.GET_TIME,
            confidence=0.50,
        )),
        "CLARIFY",
    )


def test_entity_satisfied():

    print()
    print("--- ENTITY SATISFIED ---")

    _check(
        "open without entity",
        entity_satisfied(Intent(
            name=IntentType.OPEN_APPLICATION, confidence=0.7
        )),
        False,
    )

    _check(
        "open with application",
        entity_satisfied(Intent(
            name=IntentType.OPEN_APPLICATION,
            confidence=0.7,
            entities={"application": "chrome"},
        )),
        True,
    )

    _check(
        "search without query",
        entity_satisfied(Intent(
            name=IntentType.SEARCH_WEB, confidence=0.8
        )),
        False,
    )

    _check(
        "time needs no entity",
        entity_satisfied(Intent(name=IntentType.GET_TIME, confidence=0.9)),
        True,
    )


# ==============================================
# CONVERSATION CONTEXT
# ==============================================

def test_context_bounded():

    print()
    print("--- CONVERSATION CONTEXT BOUNDS ---")

    context = ConversationContext(max_messages=3, max_tokens=200)

    for index in range(6):

        context.add_turn(
            f"user message number {index}",
            f"assistant reply number {index}",
        )

    _check("message cap enforced", len(context.turns), 3)

    _check(
        "oldest dropped",
        context.turns[0]["user"],
        "user message number 3",
    )

    tokens = ConversationContext(max_messages=100, max_tokens=20)

    tokens.add_turn(
        "aaaa bbbb cccc dddd eeee ffff gggg hhhh",
        "x x x",
    )

    tokens.add_turn("short", "y")

    _check_true(
        "token cap enforced",
        tokens._token_count() <= 20,
    )

    _check("history flat", len(context.history()), 6)

    _check("topic starts empty", context.topic, None)

    context.set_topic(IntentType.SEARCH_WEB, "python")

    _check("topic stored", context.topic, IntentType.SEARCH_WEB)
    _check("entity stored", context.last_entity, "python")


# ==============================================
# DISCOVERY
# ==============================================

def test_discovery_aliases_and_cache():

    print()
    print("--- DISCOVERY ---")

    cache = os.path.join(tempfile.mkdtemp(), "apps_cache.json")

    discovery = ApplicationDiscovery(cache_path=cache, max_age_days=7)

    _check(
        "browser alias",
        discovery.find("browser"),
        {"name": "chrome", "display": "browser"},
    )

    _check(
        "not bad alias",
        discovery.find("not bad"),
        {"name": "notepad", "display": "not bad"},
    )

    _check(
        "explorer alias",
        discovery.find("explorer"),
        {"name": "file explorer", "display": "explorer"},
    )

    # Seeded apps, fresh cache: no disk scan.
    discovery.apps = [
        {"name": "spotify", "display": "Spotify"},
        {"name": "obsidian", "display": "Obsidian"},
    ]

    discovery.scanned_at = datetime.now().isoformat()

    _check(
        "exact match",
        discovery.find("spotify"),
        {"name": "spotify", "display": "Spotify"},
    )

    _check(
        "case insensitive",
        discovery.find("Spotify"),
        {"name": "spotify", "display": "Spotify"},
    )

    _check(
        "unknown returns None",
        discovery.find("no-such-app"),
        None,
    )

    # Cache round trip.
    discovery._save_cache()

    reloaded = ApplicationDiscovery(cache_path=cache, max_age_days=7)

    _check(
        "cache loaded",
        reloaded.find("spotify"),
        {"name": "spotify", "display": "Spotify"},
    )


# ==============================================
# RESPONSE GENERATION
# ==============================================

def test_response_variation():

    print()
    print("--- RESPONSE VARIATION ---")

    generator = ResponseGenerator()

    first = generator.open_response("Chrome")
    second = generator.open_response("Chrome")

    _check_true(
        "variants differ",
        first != second,
    )

    _check_true(
        "variant from pool",
        first in {
            "Sure. Opening Chrome.",
            "Got it. Launching Chrome now.",
            "Chrome is open.",
        },
    )

    _check(
        "missing entity question",
        generator.missing_entity_response(IntentType.OPEN_APPLICATION),
        "What would you like me to open?",
    )

    _check(
        "search missing question",
        generator.missing_entity_response(IntentType.SEARCH_WEB),
        "What would you like me to search for?",
    )


# ==============================================
# ASSISTANT BEHAVIOUR
# ==============================================

def test_assistant_passthrough():

    print()
    print("--- ASSISTANT BRAIN PASSTHROUGH ---")

    assistant = _assistant()

    result = assistant.process("what time is it")

    _check(
        "time passes through",
        result.response,
        "The current time is 3:45 PM.",
    )

    result = assistant.process("hello astra")

    _check(
        "greeting passes through",
        result.response,
        "Hello Edrine. How can I help you?",
    )

    result = assistant.process("dance for me")

    _check(
        "unknown stays unknown",
        result.response,
        "I don't know how to do that yet.",
    )

    result = assistant.process("exit astra")

    _check("exit passes through", result.response, "Goodbye Edrine.")
    _check("exit flag", result.exit, True)


def test_assistant_semantic_fallback():

    print()
    print("--- ASSISTANT SEMANTIC FALLBACK ---")

    assistant = _assistant()

    result = assistant.process("load spotify")

    _check(
        "load spotify opens",
        result.response,
        "Opening Spotify.",
    )

    result = assistant.process("show me obsidian")

    _check(
        "show me obsidian opens",
        result.response,
        "Opening Obsidian.",
    )


def test_assistant_tool_confirmation():

    print()
    print("--- ASSISTANT TOOL CONFIRMATION ---")

    assistant = _assistant()

    result = assistant.process("delete that folder")

    _check(
        "folder clarified",
        result.response,
        "Which folder do you mean?",
    )

    result = assistant.process("the downloads folder")

    _check(
        "brain confirms destructive delete",
        result.response,
        "Are you sure you want me to do that?",
    )

    result = assistant.process("yes")

    _check_true("folder deleted", result.response.startswith("I deleted"))


def test_topic_tracking():

    print()
    print("--- TOPIC TRACKING ---")

    assistant = _assistant()

    assistant.process("what time is it")

    _check("time topic", assistant.context.topic, IntentType.GET_TIME)

    assistant.process("and tomorrow?")

    _check(
        "date topic after answer",
        assistant.context.topic,
        IntentType.GET_DATE,
    )


# ==============================================
# MAIN
# ==============================================

def main():

    print("================================")
    print("      INTELLIGENCE LAYER")
    print("================================")

    test_spec_conversations()
    test_search_web_clarifies_then_searches()
    test_delete_folder_clarifies()
    test_open_it_then_answer()
    test_nlu_semantic_open()
    test_nlu_date_ellipsis()
    test_nlu_bare_search()
    test_router_confidence()
    test_entity_satisfied()
    test_context_bounded()
    test_discovery_aliases_and_cache()
    test_response_variation()
    test_assistant_passthrough()
    test_assistant_semantic_fallback()
    test_assistant_tool_confirmation()
    test_topic_tracking()

    print()
    print("================================")
    print(f"PASS: {_PASS}   FAIL: {_FAIL}")
    print("================================")

    sys.exit(1 if _FAIL else 0)


if __name__ == "__main__":
    main()