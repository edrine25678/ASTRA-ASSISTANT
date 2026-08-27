"""
Tool system foundation: the contract every Astra capability follows.

The AI brain never executes code directly.  It produces a ToolCall,
and the tool registry decides whether the operation is permitted,
validates the arguments, and runs the tool.
"""

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    """A request to execute a tool."""

    name: str
    arguments: dict = field(default_factory=dict)
    confirmed: bool = False


@dataclass
class ToolResult:
    """The outcome of a tool execution."""

    success: bool
    data: dict = field(default_factory=dict)
    response: str = ""
    error: str = ""
    denied: bool = False
    needs_confirmation: bool = False
    tool: str = ""


class Tool:
    """Base class for every Astra capability.

    Subclasses define a unique name, a description and a parameter
    specification, then implement run() to perform the action and
    return a ToolResult.  Extra argument restrictions go in
    validate(), which the registry always checks before execution.
    """

    name = ""
    description = ""
    parameters = {}

    # Set to True on a tool to require the user to confirm the
    # action before it actually runs.
    requires_confirmation = False

    def validate(self, arguments):
        """Return an error message string, or None when allowed."""

        missing = [
            key
            for key, spec in self.parameters.items()
            if spec.get("required") and not arguments.get(key)
        ]

        if missing:
            return (
                "Missing required argument(s): "
                + ", ".join(missing)
            )

        return None

    def run(self, arguments):
        raise NotImplementedError(
            f"{type(self).__name__} must implement run()"
        )

    def describe(self):
        """Metadata used by the brain for tool selection."""

        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires_confirmation": self.requires_confirmation,
        }


# Compatibility alias: the Phase 4 spec names the interface
# "AstraTool"; both names refer to the same contract.
AstraTool = Tool
