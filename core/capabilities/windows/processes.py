"""
Running applications, process information and controlled closing
(spec sections 9-11, 25-26).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import (
    CLOSE_APPLICATION,
    PROCESS_INFORMATION,
    RUNNING_APPLICATIONS,
)
from tools.base import ToolCall
from tools.process_tools import SYSTEM_PROCESSES, matching_processes, snapshot_processes


class ProcessesCapability(Capability):

    name = "processes"
    description = "Running applications and process information"
    intents = (RUNNING_APPLICATIONS, PROCESS_INFORMATION,
               CLOSE_APPLICATION)

    def execute(self, intent, context):

        if intent.name == RUNNING_APPLICATIONS:
            return self._running(intent, context)

        if intent.name == PROCESS_INFORMATION:
            return self._process_information(intent)

        return self._close(intent, context)

    def _running(self, intent, context):

        application = (
            intent.entities.get("application")
            or intent.entities.get("target")
        )

        if application:

            matches = matching_processes(application)

            display = application

            info = self.discovery.find(application) if self.discovery else None

            if info is not None:
                display = info["display"]

            if matches:

                windows = len(matches)

                response = (
                    f"Yes, {display} is running"
                    + (f" with {windows} window(s)." if windows > 1
                       else ".")
                )

            else:

                response = f"No, {display} is not running right now."

            return CapabilityResult(
                response=response,
                data={
                    "running": bool(matches),
                    "application": application,
                    "count": len(matches),
                },
            )

        names = []

        for process in snapshot_processes():

            stem = process["name"].rsplit(".", 1)[0]

            if stem in SYSTEM_PROCESSES or not stem:
                continue

            if stem not in names:
                names.append(stem)

        names.sort()

        preview = ", ".join(names[:12])

        if not names:

            return CapabilityResult(
                success=False,
                response="I couldn't read the running processes.",
            )

        response = (
            f"These are running right now: {preview}"
            + (" and more." if len(names) > 12 else ".")
        )

        return CapabilityResult(
            response=response,
            data={"count": len(names), "names": names[:12]},
        )

    def _process_information(self, intent):

        kind = intent.entities.get("kind") or "memory"

        topic = "top_process" if kind == "memory" else "cpu_usage"

        return self._run(ToolCall("system_info", {"topic": topic}))

    def _close(self, intent, context):

        application = (
            intent.entities.get("application")
            or intent.entities.get("target")
        )

        if not application and context is not None:
            application = context.last_entity

        if not application:

            return CapabilityResult(
                success=False,
                response="What would you like me to close?",
            )

        return self._run(
            ToolCall("close_application", {"application": application})
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