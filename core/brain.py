"""
AstraBrain: the Phase 5 orchestrator.

Turns one user utterance into one spoken response by routing it
through the conversational brain, the task engine, memory and the
tool registry.  The brain also owns the confirmation flow for
single commands and the follow-up resolution for captured results.

Response variations are deterministic: the same utterance always
picks the same variant within a process, chosen by hash.
"""

import re
from dataclasses import dataclass

from config.settings import MEMORY_DB_PATH, MEMORY_ENABLED

from core.logger import get_logger

from core.confirmation import ConfirmationManager
from core.observer import AstraObserver
from core.planner import AstraPlanner
from core.task_engine import AstraTaskEngine, TaskState

from ai.brain import AIBrain
from ai.intent import (
    APPLICATION_ACTION,
    BROWSER_ACTION,
    CLARIFICATION,
    CONVERSATION,
    EXIT,
    FOLLOW_UP,
    KNOWLEDGE,
    MEMORY_ACTION,
    SYSTEM_QUERY,
    TASK,
    TASK_CONTROL,
    UNKNOWN,
)
from ai.provider import AIProviderError
from ai import build_provider

from memory.context import ConversationContext
from memory.manager import MemoryManager

from tools import build_default_registry
from tools.base import ToolCall

logger = get_logger("core.brain")


@dataclass
class BrainResponse:
    response: str
    exit: bool = False


class AstraBrain:

    # Spoken confirmation variants for app launches.
    APP_OPEN_POOL = (
        "Sure. Opening {name}.",
        "Got it. Launching {name} now.",
        "{name} is open.",
    )

    YES_PHRASES = ("yes", "yeah", "yep", "sure", "ok", "okay", "do it", "go ahead")
    NO_PHRASES = ("no", "nope", "cancel", "don't", "dont", "never mind")

    KNOWLEDGE_FALLBACK = (
        "I'm unable to access my conversational AI right now, "
        "but my local tools are still available."
    )

    def __init__(self, planner=None, registry=None, provider=None,
                 memory_enabled=None, memory_path=None):

        self.brain = AIBrain(planner=planner)
        self.registry = registry if registry is not None else build_default_registry()
        self.provider = provider if provider is not None else build_provider()
        self.context = ConversationContext()
        self.confirmation = ConfirmationManager()
        self.observer = AstraObserver()

        enabled = MEMORY_ENABLED if memory_enabled is None else memory_enabled
        path = memory_path if memory_path is not None else MEMORY_DB_PATH

        if enabled:
            self.memory = MemoryManager(path, enabled=True)
        else:
            self.memory = MemoryManager(None, enabled=False)

        self.planner = AstraPlanner()
        self.task_engine = AstraTaskEngine(
            registry=self.registry,
            planner=self.planner,
            observer=self.observer,
            confirmation=self.confirmation,
            memory=self.memory,
            context=self.context,
        )

    # ==============================================
    # MAIN ENTRY
    # ==============================================

    def process(self, text):
        """Turn one user utterance into a BrainResponse."""

        raw = (text or "").strip()

        if not raw:
            return self._respond("I didn't catch that.", raw)

        # A single-command confirmation is waiting for a yes or no.
        if self.context.pending_call is not None:
            return self._resolve_confirmation(raw)

        # A task is waiting for user input.
        task = self.task_engine.current_task

        if task is not None and task.status == TaskState.WAITING_FOR_USER:

            quick = self.brain.process(raw)

            if quick.type == EXIT:

                self.task_engine.cancel()

                return self._respond("Goodbye Edrine.", raw, exit=True)

            if quick.type == TASK_CONTROL and quick.action == "cancel":

                return self._respond(self.task_engine.cancel(), raw)

            reply = self.task_engine.continue_with_input(raw)

            return self._respond(reply, raw)

        intent = self.brain.process(raw)

        if intent.type == EXIT:
            return self._respond("Goodbye Edrine.", raw, exit=True)

        # Remember what the user just said.
        self._remember_short_term(raw)

        if intent.type == TASK_CONTROL:

            if intent.action == "cancel":
                return self._respond(self.task_engine.cancel(), raw)

            if intent.action == "status":
                return self._respond(
                    self.task_engine.status_description(), raw
                )

        if intent.type == TASK:

            goal = intent.parameters.get("goal") or raw

            response = self.task_engine.start_new(goal)

            return self._respond(response, raw)

        if intent.type == FOLLOW_UP:
            return self._handle_follow_up(intent, raw)

        if intent.type == CLARIFICATION:

            response = "Okay." if intent.action == "yes" else "Alright."

            return self._respond(response, raw)

        if intent.type == MEMORY_ACTION:
            return self._handle_memory(intent)

        if intent.type == KNOWLEDGE:
            return self._handle_knowledge(intent)

        if intent.type == CONVERSATION:
            return self._respond(intent.response, raw)

        if intent.tool_call is not None:
            return self._execute_tool(intent)

        return self._respond(
            intent.response or "I don't know how to do that yet.",
            raw,
        )

    # ==============================================
    # TOOL EXECUTION
    # ==============================================

    def _execute_tool(self, intent):

        if (
            intent.type == BROWSER_ACTION
            and intent.action == "open_url"
        ):
            self.context.set_last_site(intent.target)
        elif (
            intent.type == BROWSER_ACTION
            and intent.action == "search_web"
            and intent.parameters.get("engine") == "google"
            and self.context.last_site == "youtube"
        ):
            intent.parameters["engine"] = "youtube"
            intent.tool_call.arguments["engine"] = "youtube"

        call = intent.tool_call

        # Risk-based confirmation (file create, file delete, ...).
        if self.confirmation.needs_confirmation(call) and not call.confirmed:

            self.context.pending_call = call

            return self._respond(
                "Are you sure you want me to do that?", intent.raw_text
            )

        result = self.registry.execute(call)

        if result.needs_confirmation:

            self.context.pending_call = call

            return self._respond(result.response, intent.raw_text)

        if (
            intent.type == APPLICATION_ACTION
            and result.success
        ):
            return self._respond(
                self._vary_app_open(result.response), intent.raw_text
            )

        return self._respond(result.response, intent.raw_text)

    def _vary_app_open(self, response):

        match = re.match(r"^Opening (.+?)\.$", response)

        if not match:
            return response

        name = match.group(1)

        variant = self.APP_OPEN_POOL[hash(response) % len(self.APP_OPEN_POOL)]

        return variant.format(name=name)

    # ==============================================
    # CONFIRMATION FLOW (single commands)
    # ==============================================

    def _resolve_confirmation(self, raw):

        call = self.context.pending_call

        self.context.pending_call = None

        if any(phrase in raw for phrase in self.NO_PHRASES):

            return self._respond("Okay, I won't do that.", raw)

        if any(phrase in raw for phrase in self.YES_PHRASES):

            call.confirmed = True

            result = self.registry.execute(call)

            if result.needs_confirmation:

                return self._respond(result.response, raw)

            return self._respond(result.response, raw)

        # Neither yes nor no: treat it as a brand-new command.
        return self.process(raw)

    # ==============================================
    # FOLLOW-UPS
    # ==============================================

    def _handle_follow_up(self, intent, raw):

        task = self.task_engine.current_task

        index = intent.parameters.get("index")

        if task is not None and task.captured_results:

            picked = self.task_engine.resolve_follow_up(index)

            if picked is not None:

                call = ToolCall("file_open_file", {"path": picked})

                result = self.registry.execute(call)

                return self._respond(result.response, raw)

            return self._respond(
                "I have results from earlier. "
                "Say 'the first one' or 'the second one' and "
                "I'll open it.",
                raw,
            )

        if (
            task is not None
            and task.status == TaskState.COMPLETED
        ):

            last_tool = ""
            for step in reversed(task.steps):
                if step.tool:
                    last_tool = step.tool
                    break

            if last_tool == "search_web":

                return self._respond(
                    "I opened the search page, but I can't read "
                    "the results yet.",
                    raw,
                )

        return self._respond(
            "I don't have anything to follow up on right now.", raw
        )

    # ==============================================
    # MEMORY
    # ==============================================

    def _remember_short_term(self, text):

        try:
            self.memory.remember(text, category="short_term")
        except Exception as error:
            logger.warning("Could not store short-term memory: %s", error)

    def _handle_memory(self, intent):

        action = intent.action
        parameters = intent.parameters

        try:

            if action == "save":

                ok, message, _item = self.memory.remember(
                    parameters.get("content", ""),
                    parameters.get("category"),
                )

                return self._respond(message, intent.raw_text)

            if action == "forget":

                ok, message, _count = self.memory.forget(
                    parameters.get("query", "")
                )

                return self._respond(message, intent.raw_text)

            if action == "recall":

                category = parameters.get("category")

                ok, message, items = self.memory.recall(
                    parameters.get("query"), category=category
                )

                if ok and items:

                    content = items[0]["content"]

                    if category == "tasks":

                        response = f"Recently: {content}."

                    else:

                        extra = (
                            f" (and {len(items) - 1} more)"
                            if len(items) > 1 else ""
                        )

                        response = (
                            f"Here's what I remember: {content}{extra}."
                        )

                else:

                    # Selective fallback: relevance instead of a miss.
                    entries = self.memory.retrieve_relevant(
                        parameters.get("query") or intent.raw_text
                    )

                    if entries:
                        response = self._memory_answer(entries[0])
                    else:
                        response = message

                return self._respond(response, intent.raw_text)

        except Exception as error:

            logger.exception("Memory action %s failed", action)

            return self._respond(
                "I ran into a problem with my memory.", intent.raw_text
            )

        return self._respond("I don't know how to do that yet.", intent.raw_text)

    def _memory_answer(self, entry):

        content = entry["content"].strip()

        lowered = content.lower()

        if lowered.startswith("i "):
            return "You " + content[2:].strip() + "."

        if lowered.startswith("my "):
            return "You told me: " + content + "."

        return "I remember: " + content + "."

    # ==============================================
    # KNOWLEDGE (optional provider)
    # ==============================================

    def _handle_knowledge(self, intent):

        # Durable memory is authoritative for personal knowledge.
        entries = self.memory.retrieve_relevant(intent.raw_text)

        if entries:
            return self._respond(
                self._memory_answer(entries[0]), intent.raw_text
            )

        if self.provider is None or not self.provider.available():

            return self._respond(self.KNOWLEDGE_FALLBACK, intent.raw_text)

        try:

            history = self.context.history(limit=4)

            messages = [
                {"role": role, "content": content}
                for role, content in history
            ]

            messages.append({"role": "user", "content": intent.raw_text})

            answer = self.provider.generate(messages)

            if not answer or not answer.strip():
                raise AIProviderError("Empty answer from provider")

            return self._respond(answer.strip(), intent.raw_text)

        except AIProviderError as error:

            logger.warning("Knowledge provider failed: %s", error)

            return self._respond(self.KNOWLEDGE_FALLBACK, intent.raw_text)

    # ==============================================
    # HELPERS
    # ==============================================

    def _respond(self, response, user_text, exit=False):

        self.context.add_turn(user_text or "", response)

        return BrainResponse(response=response, exit=exit)