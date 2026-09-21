"""
Astra's capability layer.

Tools are self-contained capabilities discovered by the registry.
The AI brain produces ToolCalls; the registry executes them under
the safety policy.
"""

from tools.application_tools import OpenApplicationTool
from tools.base import AstraTool as AstraTool
from tools.base import Tool as Tool
from tools.base import ToolCall as ToolCall
from tools.base import ToolResult as ToolResult
from tools.browser_tools import OpenUrlTool, SearchWebTool
from tools.file_tool import (
    FileCreateTextTool,
    FileDeleteTool,
    FileListDirectoryTool,
    FileOpenFileTool,
    FileOpenFolderTool,
    FileReadTextTool,
    FileSearchTool,
)
from tools.registry import ToolRegistry
from tools.safety import ToolSafety as ToolSafety
from tools.system_tools import GetDateTool, GetTimeTool, SystemInfoTool


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