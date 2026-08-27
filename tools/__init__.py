"""
Astra's capability layer.

Tools are self-contained capabilities discovered by the registry.
The AI brain produces ToolCalls; the registry executes them under
the safety policy.
"""

from tools.base import AstraTool, Tool, ToolCall, ToolResult
from tools.registry import ToolRegistry
from tools.safety import ToolSafety
from tools.application_tools import OpenApplicationTool
from tools.browser_tools import OpenUrlTool, SearchWebTool
from tools.system_tools import GetDateTool, GetTimeTool, SystemInfoTool
from tools.file_tool import (
    FileCreateTextTool,
    FileDeleteTool,
    FileListDirectoryTool,
    FileOpenFileTool,
    FileOpenFolderTool,
    FileReadTextTool,
    FileSearchTool,
)


def build_default_registry(safety=None):
    """Create a registry with every default Astra tool."""

    registry = ToolRegistry(safety=safety)

    registry.register(OpenApplicationTool())
    registry.register(OpenUrlTool())
    registry.register(SearchWebTool())
    registry.register(GetTimeTool())
    registry.register(GetDateTool())
    registry.register(SystemInfoTool())
    registry.register(FileSearchTool())
    registry.register(FileListDirectoryTool())
    registry.register(FileOpenFileTool())
    registry.register(FileOpenFolderTool())
    registry.register(FileReadTextTool())
    registry.register(FileCreateTextTool())
    registry.register(FileDeleteTool())

    return registry