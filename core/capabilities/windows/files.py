"""
File search with type / location / date awareness (spec sections
12, 14-15).
"""

from config.settings import MAX_FILE_SEARCH_DEPTH
from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import FILE_SEARCH
from tools.base import ToolCall


class WindowsFilesCapability(Capability):

    name = "windows_files"
    description = "File search inside allowed folders"
    intents = (FILE_SEARCH,)

    def execute(self, intent, context):

        if intent.tool_call is not None:
            return self._run(intent.tool_call)

        entities = intent.entities

        location = entities.get("location")

        path = entities.get("path")

        parameters = {
            "query": entities.get("query") or "",
            "extensions": entities.get("extensions") or [],
            "modified_within_days": entities.get("modified_within_days"),
            "max_depth": MAX_FILE_SEARCH_DEPTH,
        }

        if location == "__here__":

            if not path:

                return CapabilityResult(
                    success=False,
                    response=(
                        "I'm not inside a folder right now, so I "
                        "don't know what 'here' means."
                    ),
                )

            parameters["root"] = path

        elif location:

            parameters["root"] = location

        return self._run(ToolCall("file_search", parameters))

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