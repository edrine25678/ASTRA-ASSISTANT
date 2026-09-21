"""
Network status (spec section 20).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import NETWORK_STATUS
from tools.base import ToolCall


class NetworkCapability(Capability):

    name = "network"
    description = "Internet connectivity, Wi-Fi and IP address"
    intents = (NETWORK_STATUS,)

    def execute(self, intent, context):

        if intent.tool_call is not None:
            return self._run(intent.tool_call)

        kind = intent.entities.get("kind") or "all"

        return self._run(
            ToolCall("system_info", {"topic": "network", "kind": kind})
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