"""
Web search capability.
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import SEARCH_WEB

from tools.base import ToolCall


class SearchCapability(Capability):

    name = "search"
    description = "Search the web"
    intents = (SEARCH_WEB,)

    def execute(self, intent, context):

        if intent.tool_call is not None:

            return self._run(intent.tool_call)

        query = intent.entities.get("query")

        if not query:

            return CapabilityResult(
                success=False,
                needs_confirmation=True,
                response="What would you like me to search for?",
            )

        return self._run(
            ToolCall("search_web", {"query": query, "engine": "google"})
        )

    def _run(self, call):

        if self.tool_registry is None:

            return CapabilityResult(
                success=False,
                response="I don't know how to do that yet.",
            )

        result = self.tool_registry.execute(call)

        return CapabilityResult(
            response=result.response,
            success=result.success,
            needs_confirmation=result.needs_confirmation,
            data=result.data,
            call=call,
        )