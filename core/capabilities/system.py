"""
System capability: time and date.

Machine information moved to core.capabilities.windows in Phase 7.
"""

from datetime import datetime, timedelta, timezone

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import GET_DATE, GET_TIME
from tools.base import ToolCall


class SystemCapability(Capability):

    name = "system"
    description = "Time and date"
    intents = (GET_TIME, GET_DATE)

    def execute(self, intent, context):

        if intent.name == GET_TIME:

            if intent.tool_call is not None:
                return self._run(intent.tool_call)

            return self._run(ToolCall("get_time", {}))

        if intent.name == GET_DATE:

            if intent.tool_call is not None:
                return self._run(intent.tool_call)

            day = intent.entities.get("day")

            if day:

                return CapabilityResult(
                    response=self._date_for(day),
                    data={"day": day},
                )

            return self._run(ToolCall("get_date", {}))

        return CapabilityResult(
            success=False,
            response="I don't know how to do that yet.",
        )

    @staticmethod
    def _date_for(day):

        today = datetime.now(tz=timezone.utc)

        if day == "tomorrow":
            return (
                "Tomorrow will be "
                f"{(today + timedelta(days=1)).strftime('%A, %B %d, %Y')}."
            )

        if day == "yesterday":
            return (
                "Yesterday was "
                f"{(today - timedelta(days=1)).strftime('%A, %B %d, %Y')}."
            )

        if day == "today":
            return f"Today is {today.strftime('%A, %B %d, %Y')}."

        if day == "next week":
            return (
                "A week from today will be "
                f"{(today + timedelta(days=7)).strftime('%A, %B %d, %Y')}."
            )

        if day == "next month":
            return (
                "In about a month, it will be around "
                f"{(today + timedelta(days=30)).strftime('%B %d, %Y')}."
            )

        if day == "next year":
            return (
                "In about a year, it will be around "
                f"{(today + timedelta(days=365)).strftime('%B %d, %Y')}."
            )

        return f"Today is {today.strftime('%A, %B %d, %Y')}."

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