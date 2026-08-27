"""
Storage drives (spec section 6).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import STORAGE_STATUS

from tools.base import ToolCall


class StorageCapability(Capability):

    name = "storage"
    description = "Storage drives and free space"
    intents = (STORAGE_STATUS,)

    def execute(self, intent, context):

        if intent.tool_call is not None:
            return self._run(intent.tool_call)

        parameters = {"topic": "storage"}

        drive = intent.entities.get("drive")

        if drive:
            parameters["drive"] = drive

        return self._run(ToolCall("system_info", parameters))

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