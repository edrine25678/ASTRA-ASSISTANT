"""
AstraAssistant: the Phase 6 orchestrator.

Wraps the Phase 5 AstraBrain, so everything already working
(confirmations, tasks, memory, follow-ups, tools) is preserved
unchanged.  The assistant adds:

    1. pre-checks      pronoun opens, pronoun file actions,
                       date ellipses ("and tomorrow?")
    2. the brain       first word on every utterance
    3. semantic NLU    only when the brain falls back
    4. confidence      auto / clarify / unknown routing
    5. capabilities    safe tool execution with one registry
    6. personality     variant responses, no repetition

The assistant never guesses on pronouns: "Open it." and
"Delete that folder." always produce a clarifying question.
"""

from ai.model_agent import ModelAgent
from core.brain import AstraBrain, BrainResponse
from core.capabilities import ApplicationDiscovery, build_capability_registry
from core.intelligence.context import ConversationContext
from core.intelligence.intent import Intent, IntentType
from core.intelligence.nlu import FILE_PRONOUN, NLU
from core.intelligence.response import ResponseGenerator
from core.intelligence.router import decide, entity_satisfied
from tools.base import ToolCall
from tools.process_tools import CloseApplicationTool

NO_PHRASES = ("no", "nope", "cancel", "don't", "dont", "never mind",
              "nothing")
YES_PHRASES = ("yes", "yeah", "yep", "sure", "ok", "okay", "do it",
               "go ahead")

FALLBACK_RESPONSES = (
    "I don't know how to do that yet.",
    ("I'm unable to access my conversational AI right now, "
    "but my local tools are still available."),
)

ANSWER_KIND = {
    IntentType.OPEN_APPLICATION: "open",
    IntentType.OPEN_WEBSITE: "site",
    IntentType.SEARCH_WEB: "search",
    IntentType.FILE_OPERATION: "file",
    IntentType.READ_FILE: "file",
    IntentType.CREATE_FILE: "file",
    IntentType.LIST_FILES: "file",
    IntentType.CLOSE_APPLICATION: "close",
}


class AstraAssistant:

    def __init__(self, brain=None, discovery=None, registry=None,
                 context=None):

        self.brain = brain if brain is not None else AstraBrain()

        self.registry = (
            registry if registry is not None else self.brain.registry
        )

        # The close tool is only reachable through the assistant
        # registry (always confirmation-gated), never registered in
        # the default tool set.
        if "close_application" not in {
            tool["name"] for tool in self.registry.discover()
        }:

            try:
                self.registry.register(CloseApplicationTool())
            except (ImportError, OSError):
                pass  # CloseApplicationTool unavailable on this platform

        self.discovery = (
            discovery if discovery is not None else ApplicationDiscovery()
        )

        self.nlu = NLU(
            discovery=self.discovery,
            brain=self.brain.brain,
        )

        self.caps = build_capability_registry(
            tool_registry=self.registry,
            discovery=self.discovery,
        )

        self.responder = ResponseGenerator()

        # Optional model-assisted reasoning. It is disabled automatically
        # when no provider is configured, so Astra remains fully local.
        self.model_agent = ModelAgent(
            provider=getattr(self.brain, "provider", None),
            registry=self.registry,
            memory=getattr(self.brain, "memory", None),
        )

        # Share the brain's context by default. This prevents Phase 5 and
        # Phase 6 from maintaining two independent conversation histories.
        self.context = (
            context
            if context is not None
            else getattr(self.brain, "context", None)
            or ConversationContext()
        )

        # Keep the wrapped brain and assistant on the same context object.
        # This is important for confirmations, topics, last-site follow-ups
        # and conversation history.
        self.brain.context = self.context

        self.pending = None

    # ==============================================
    # MAIN ENTRY
    # ==============================================

    def process(self, text):
        """Turn one user utterance into a BrainResponse."""

        raw = (text or "").strip()

        if not raw:
            return BrainResponse("I didn't catch that.")

        # 1. A clarification or confirmation is waiting.
        if self.pending is not None:
            return self._resolve_pending(raw)

        # 2. Pre-checks before the brain sees the text.
        pre = self.nlu.precheck(raw, self.context)

        if pre is not None:
            return self._handle_precheck(pre, raw)

        # 3. The deterministic brain decides first.
        brain_result = self.brain.process(raw)

        if brain_result.exit:
            return brain_result

        if not self._brain_fell_back(brain_result.response):

            self._track_topic(raw)

            self.context.add_turn(raw, brain_result.response)

            return brain_result

        # 4. Semantic fallback for what the brain could not resolve.
        intent = self.nlu.resolve(raw, self.context, skip_planner=True)

        if intent.name == IntentType.UNKNOWN:

            # Phase 8+: use the optional model only after deterministic
            # understanding has failed. The model can answer naturally or
            # request one validated tool call, but it never executes tools.
            model_result = self.model_agent.decide(raw, self.context)

            if model_result is not None:
                if model_result["type"] in ("reply", "clarify"):
                    response = model_result["reply"]
                    self.context.add_turn(raw, response)
                    return BrainResponse(response)

                if model_result["type"] == "tool":
                    return self._execute_model_tool(
                        model_result["call"], raw
                    )

            response = self.responder.unknown_response()

            self.context.add_turn(raw, response)

            return BrainResponse(response)

        decision = decide(intent)

        if decision == "CLARIFY":

            return self._ask(intent, raw)

        return self._act(intent, raw)

    # ==============================================
    # PRECHECKS
    # ==============================================

    def _handle_precheck(self, intent, raw):

        if intent.name == IntentType.GET_DATE:

            # "and tomorrow?" after a time/date turn.
            capability = self.caps.route(IntentType.GET_DATE)

            result = capability.execute(intent, self.context)

            self.context.set_topic(IntentType.GET_DATE)

            self.context.add_turn(raw, result.response)

            return BrainResponse(result.response)

        if intent.name == IntentType.OPEN_APPLICATION:

            # "open it" - never guess what "it" is.
            return self._ask(intent, raw)

        if intent.name == IntentType.SEARCH_WEB:

            # "search the web" - ask what to search for.
            return self._ask(intent, raw)

        if intent.name == IntentType.FILE_OPERATION:

            # "delete that folder" - ask which folder.
            return self._ask_file(raw)

        if intent.name == IntentType.CLOSE_APPLICATION:

            # "close it" - the entity came from the conversation
            # topic, so it can be acted on (with confirmation).
            return self._act(intent, raw)

        if intent.name == IntentType.FOLDER_OPERATION:

            # "go to downloads" - navigate before the brain.
            capability = self.caps.route(IntentType.FOLDER_OPERATION)

            result = capability.execute(intent, self.context)

            self.context.add_turn(raw, result.response)

            return BrainResponse(result.response)

        if intent.name == IntentType.EXIT:

            # "close astra" - stop the assistant.
            return BrainResponse("Closing Astra.", exit=True)

        return BrainResponse(self.responder.unknown_response())

    # ==============================================
    # MODEL TOOL EXECUTION
    # ==============================================

    def _execute_model_tool(self, call, raw):
        """Execute a model-selected tool through the normal safety path."""

        if call.name not in {
            item["name"] for item in self.registry.discover()
        }:
            response = "I can't access that capability."
            self.context.add_turn(raw, response)
            return BrainResponse(response)

        result = self.registry.execute(call)

        if result.needs_confirmation:
            self.pending = {
                "kind": "tool_confirm",
                "call": call,
            }
            self.context.add_turn(raw, result.response)
            return BrainResponse(result.response)

        self._track_topic(raw)
        self.context.add_turn(raw, result.response)
        return BrainResponse(result.response)

    # ==============================================
    # FALLBACK EXECUTION
    # ==============================================

    def _act(self, intent, raw):

        capability = self.caps.route(intent.name)

        if capability is None:

            response = self.responder.unknown_response()

            self.context.add_turn(raw, response)

            return BrainResponse(response)

        result = capability.execute(intent, self.context)

        if result.needs_confirmation:

            if result.call is not None:

                # A tool needs a yes/no (destructive actions).
                self.pending = {
                    "kind": "tool_confirm",
                    "call": result.call,
                }

            else:

                # A detail is missing; the next utterance is the answer.
                self.pending = {
                    "kind": ANSWER_KIND.get(
                        intent.name, "restate"
                    ),
                    "intent": intent,
                }

            self.context.add_turn(raw, result.response)

            return BrainResponse(result.response)

        self._track_topic(raw)

        self.context.add_turn(raw, result.response)

        return BrainResponse(result.response)

    def _ask(self, intent, raw):
        """Clarify a low-confidence or incomplete intent."""

        if not entity_satisfied(intent):

            question = self.responder.missing_entity_response(intent.name)

            self.pending = {
                "kind": ANSWER_KIND.get(intent.name, "restate"),
                "intent": intent,
            }

        else:

            question = self.responder.clarify_response()

            self.pending = {"kind": "restate", "intent": intent}

        self.context.add_turn(raw, question)

        return BrainResponse(question)

    def _ask_file(self, raw):
        """Ask which folder a pronoun file action means."""

        match = FILE_PRONOUN.match(raw.lower().strip("?!.,;: "))

        action = match.group(1) if match else ""

        if (
            "folder" in raw.lower()
            or "directory" in raw.lower()
            or action in ("delete", "remove", "erase", "move", "rename")
        ):

            question = "Which folder do you mean?"

        else:

            question = "Which file do you mean?"

        self.pending = {
            "kind": "file",
            "action": action,
        }

        self.context.add_turn(raw, question)

        return BrainResponse(question)

    # ==============================================
    # PENDING ANSWERS
    # ==============================================

    def _resolve_pending(self, raw):

        pending = self.pending

        self.pending = None

        kind = pending["kind"]

        if any(phrase in raw.lower() for phrase in NO_PHRASES):

            response = "Okay, I won't do that."

            self.context.add_turn(raw, response)

            return BrainResponse(response)

        if kind == "tool_confirm":

            call = pending["call"]

            if any(phrase in raw.lower() for phrase in YES_PHRASES):

                call.confirmed = True

                result = self.registry.execute(call)

                self.context.add_turn(raw, result.response)

                return BrainResponse(result.response)

            # Neither yes nor no: treat it as a new command.
            return self.process(raw)

        answer = raw.strip("?!.,;: ")

        if not answer:
            return self.process(raw)

        if kind in ("open", "site", "search"):

            return self._answer_entity(kind, answer, raw)

        if kind == "file":

            action = pending.get("action")

            if action:

                result = self.brain.process(f"{action} {answer}")

                response = result.response or self.responder.unknown_response()

                self.context.add_turn(raw, response)

                return BrainResponse(response)

            return self.process(raw)

        if kind == "close":

            # "What would you like me to close?" -> "Chrome."
            intent = Intent(
                name=IntentType.CLOSE_APPLICATION,
                confidence=0.9,
                entities={"application": answer},
                original_text=raw,
            )

            return self._act(intent, raw)

        # "restate": the user repeated what they meant.
        return self.process(raw)

    def _answer_entity(self, kind, answer, raw):

        if kind == "open":

            application = answer

            if self.discovery is not None:

                info = self.discovery.find(answer)

                if info is not None:
                    application = info["name"]

            result = self.registry.execute(
                ToolCall("open_application", {"application": application})
            )

        elif kind == "site":

            result = self.registry.execute(
                ToolCall("open_url", {"url": answer})
            )

        else:

            result = self.registry.execute(
                ToolCall(
                    "search_web",
                    {"query": answer, "engine": "google"},
                )
            )

        self.context.add_turn(raw, result.response)

        return BrainResponse(result.response)

    # ==============================================
    # HELPERS
    # ==============================================

    @staticmethod
    def _brain_fell_back(response):
        return response in FALLBACK_RESPONSES

    def _track_topic(self, raw):

        intent = self.nlu.resolve(
            raw, self.context, skip_planner=True
        )

        if intent.name == IntentType.UNKNOWN:
            return

        entity = None

        for key in ("application", "site", "query", "day", "path"):

            if intent.entities.get(key):
                entity = intent.entities[key]
                break

        self.context.set_topic(intent.name, entity)