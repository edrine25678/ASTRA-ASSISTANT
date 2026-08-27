"""
Files capability: route file intents to the file tools.
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import (
    CREATE_FILE,
    FILE_OPERATION,
    LIST_FILES,
    READ_FILE,
)

from tools.base import ToolCall


class FilesCapability(Capability):

    name = "files"
    description = "Read, create, list and delete files and folders"
    intents = (FILE_OPERATION, READ_FILE, CREATE_FILE, LIST_FILES)

    def execute(self, intent, context):

        if intent.tool_call is not None:

            return self._run(intent.tool_call)

        path = intent.entities.get("path")

        if not path:

            return CapabilityResult(
                success=False,
                needs_confirmation=True,
                response="Which file or folder do you mean?",
            )

        action = intent.entities.get("action")

        tool = self._tool_for(action)

        if tool is None:

            return CapabilityResult(
                success=False,
                response="I can't do that with files yet.",
            )

        return self._run(ToolCall(tool, {"path": path}))

    @staticmethod
    def _tool_for(action):

        mapping = {
            "read": "file_read_text",
            "open": "file_open_file",
            "show": "file_open_folder",
            "list": "file_list_directory",
            "create": "file_create_text",
            "write": "file_create_text",
            "search": "file_search",
            "find": "file_search",
            "delete": "file_delete",
            "remove": "file_delete",
            "erase": "file_delete",
        }

        return mapping.get((action or "").lower())

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