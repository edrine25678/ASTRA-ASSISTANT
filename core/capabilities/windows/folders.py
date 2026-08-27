"""
Folder opening and listing, plus "here" awareness (spec sections
16-18).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.capabilities.windows.locations import resolve
from core.intelligence.intent import FOLDER_OPERATION

from tools.base import ToolCall


class WindowsFoldersCapability(Capability):

    name = "windows_folders"
    description = "Open or list approved folders"
    intents = (FOLDER_OPERATION,)

    def execute(self, intent, context):

        action = intent.entities.get("action") or "open"

        name = intent.entities.get("location")

        path = intent.entities.get("path")

        if name == "__here__":

            if not path:

                return CapabilityResult(
                    success=False,
                    response=(
                        "I'm not inside a folder right now, so I "
                        "don't know what 'here' means."
                    ),
                )

            resolved = path

        else:

            resolved = resolve(name, path)

            if not resolved:

                return CapabilityResult(
                    success=False,
                    response="I couldn't find that folder.",
                )

        tool = "file_list_directory" if action == "list" else "file_open_folder"

        result = self._run(ToolCall(tool, {"path": resolved}))

        if result.success and action != "list":
            context.current_location = resolved

        return result

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