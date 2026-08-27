"""
System specifications and live status (spec sections 3-5, 19, 21).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import (
    BATTERY_STATUS,
    COMPUTER_STATUS,
    CPU_STATUS,
    MEMORY_STATUS,
    SYSTEM_INFORMATION,
)

from tools.base import ToolCall


class WindowsSystemCapability(Capability):

    name = "windows_system"
    description = "Computer specifications, CPU, RAM and battery"
    intents = (
        SYSTEM_INFORMATION,
        CPU_STATUS,
        MEMORY_STATUS,
        BATTERY_STATUS,
        COMPUTER_STATUS,
    )

    def execute(self, intent, context):

        if intent.tool_call is not None:
            return self._run(intent.tool_call)

        if intent.name == SYSTEM_INFORMATION:

            topic = intent.entities.get("topic") or "specs"

            if topic not in ("specs", "os"):
                topic = "specs"

            return self._run(ToolCall("system_info", {"topic": topic}))

        if intent.name == CPU_STATUS:
            return self._run(ToolCall("system_info",
                                      {"topic": "cpu_usage"}))

        if intent.name == MEMORY_STATUS:
            return self._run(ToolCall("system_info",
                                      {"topic": "memory_usage"}))

        if intent.name == BATTERY_STATUS:
            return self._run(ToolCall("system_info",
                                      {"topic": "battery"}))

        if intent.name == COMPUTER_STATUS:
            return self._run(ToolCall("system_info",
                                      {"topic": "computer_status"}))

        return CapabilityResult(
            success=False,
            response="I don't know how to do that yet.",
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