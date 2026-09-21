"""
Tool discovery and execution.

New capabilities are added by registering a Tool instance; nothing in
the brain, the registry or the safety policy needs to change to
support them.

Tools that set requires_confirmation ask the user for approval
before the action runs: the first execute() returns a
ToolResult.needs_confirmation, and only a second call with
confirmed=True performs the action.
"""

from core.logger import get_logger
from tools.base import ToolCall, ToolResult
from tools.safety import ToolSafety

logger = get_logger("tools.registry")


class ToolRegistry:

    def __init__(self, safety=None):
        self.safety = safety if safety is not None else ToolSafety()
        self._tools = {}

    def register(self, tool):
        """Register a tool under its unique name."""

        if not tool.name:
            raise ValueError("A tool must have a unique name")

        self._tools[tool.name] = tool

        logger.info("Registered tool: %s", tool.name)

        return tool

    def get(self, name):
        return self._tools.get(name)

    def discover(self):
        """Return metadata for every registered tool."""

        return [tool.describe() for tool in self._tools.values()]

    def execute(self, call):
        """Run a ToolCall under the safety policy.

        Never raises: every failure becomes a controlled ToolResult.
        """

        if not isinstance(call, ToolCall):

            return ToolResult(
                success=False,
                denied=True,
                response="I don't know how to do that yet.",
                error="Invalid tool call",
            )

        tool = self._tools.get(call.name)

        if tool is None:

            return ToolResult(
                success=False,
                denied=True,
                response="I don't know how to do that yet.",
                error=f"Unknown tool: {call.name}",
            )

        if not self.safety.is_allowed(call):

            return ToolResult(
                success=False,
                denied=True,
                response="That action is not permitted.",
                error=f"Denied by safety policy: {call.name}",
            )

        validation_error = tool.validate(call.arguments)

        if validation_error:

            return ToolResult(
                success=False,
                response="I couldn't do that.",
                error=validation_error,
            )

        # ==============================================
        # CONFIRMATION GATE
        # ==============================================

        if tool.requires_confirmation and not call.confirmed:

            return ToolResult(
                success=False,
                needs_confirmation=True,
                response="Are you sure you want me to do that?",
            )

        try:

            logger.info(
                "Executing tool: %s %s", call.name, call.arguments
            )

            result = tool.run(call.arguments)

            if not result.tool:
                result.tool = call.name

            logger.info(
                "Tool %s finished (success=%s)",
                call.name,
                result.success,
            )

            return result

        except Exception as error:

            logger.exception("Tool %s failed", call.name)

            return ToolResult(
                success=False,
                response="I ran into a problem doing that.",
                error=str(error),
            )