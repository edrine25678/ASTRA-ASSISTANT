"""
Structured representation of what Astra believes the user wants.

The brain separates:
    1. what the user said           (raw_text)
    2. what the user means          (type)
    3. which capability is needed   (action / target)
    4. what arguments the tool needs (parameters / tool_call)
    5. whether it is safe           (decided by the tool safety policy)
    6. the result of the action     (ToolResult, produced by the tool)
    7. the natural-language response (response)
"""

from dataclasses import dataclass, field

from tools.base import ToolCall

CONVERSATION = "conversation"
APPLICATION_ACTION = "application_action"
BROWSER_ACTION = "browser_action"
SYSTEM_QUERY = "system_query"
FILE_ACTION = "file_action"
MEMORY_ACTION = "memory_action"
KNOWLEDGE = "knowledge"
TASK = "task"
TASK_CONTROL = "task_control"
FOLLOW_UP = "follow_up"
CLARIFICATION = "clarification"
EXIT = "exit"
UNKNOWN = "unknown"


@dataclass
class Intent:
    type: str
    action: str = ""
    target: str = ""
    parameters: dict = field(default_factory=dict)
    confidence: float = 0.0
    raw_text: str = ""
    response: str = ""
    tool_call: "ToolCall | None" = None

    def __repr__(self):

        call = ""

        if self.tool_call is not None:
            call = (
                f" -> tool={self.tool_call.name} "
                f"args={self.tool_call.arguments}"
            )

        return (
            f"Intent(type={self.type!r}, action={self.action!r}, "
            f"target={self.target!r}, "
            f"confidence={self.confidence:.2f}{call})"
        )
