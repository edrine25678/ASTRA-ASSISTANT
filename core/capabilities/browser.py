"""
Browser capability: open websites.
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import OPEN_WEBSITE

from tools.base import ToolCall


class BrowserCapability(Capability):

    name = "browser"
    description = "Open websites in the default browser"
    intents = (OPEN_WEBSITE,)

    def execute(self, intent, context):

        if intent.tool_call is not None:

            return self._run(intent.tool_call)

        site = intent.entities.get("site") or intent.entities.get("target")

        if not site:

            return CapabilityResult(
                success=False,
                needs_confirmation=True,
                response="Which website would you like me to open?",
            )

        return self._run(ToolCall("open_url", {"url": site}))

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