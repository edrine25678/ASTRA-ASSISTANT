"""
Controlled tool-execution boundary.

The AI brain may only request tools through ToolCall objects.  The
safety policy decides whether an operation is permitted at all;
individual tools then restrict their own arguments further.

Dangerous operations (file deletion, drive formatting, killing
arbitrary processes, executing arbitrary code, ...) are not
registered as tools, so they can never be reached.
"""

from tools.base import ToolCall


class ToolSafety:

    # Only these tools may be executed.  Anything else is denied.
    ALLOWED_TOOLS = {
        "open_application",
        "open_url",
        "search_web",
        "get_time",
        "get_date",
        "system_info",
        "file_search",
        "file_list_directory",
        "file_open_file",
        "file_open_folder",
        "file_read_text",
        "file_create_text",
        "file_delete",
        "close_application",
    }

    def is_allowed(self, call):
        """Return True when a ToolCall is permitted."""

        if not isinstance(call, ToolCall):
            return False

        return call.name in self.ALLOWED_TOOLS
