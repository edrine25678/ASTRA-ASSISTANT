"""
Application capability: open applications.

Closing moved to core.capabilities.windows.processes in Phase 7.
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import OPEN_APPLICATION
from tools.base import ToolCall


class ApplicationsCapability(Capability):

    name = "applications"
    description = "Open installed applications"
    intents = (OPEN_APPLICATION,)

    def execute(self, intent, context):

        application = (
            intent.entities.get("application")
            or intent.entities.get("target")
            or ""
        )

        # Planner-provided calls go straight through.
        if intent.tool_call is not None:

            return self._run(intent.tool_call)

        if not application:

            return CapabilityResult(
                success=False,
                needs_confirmation=True,
                response="What would you like me to open?",
            )

        resolved = application

        if self.discovery is not None:

            info = self.discovery.find(application)

            if info is not None:
                resolved = info["name"]

        return self._run(
            ToolCall("open_application", {"application": resolved})
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