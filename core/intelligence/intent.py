"""
Structured intent representation for the intelligence layer.

An Intent states what the user means (name), how sure Astra is
(confidence), the extracted details (entities) and the original
utterance.  New intents are added by defining a new constant here
and registering a capability for it - never by extending a single
if/elif block.
"""

from dataclasses import dataclass, field

from tools.base import ToolCall


class IntentType:

    CONVERSATION = "conversation"
    OPEN_APPLICATION = "open_application"
    CLOSE_APPLICATION = "close_application"
    SEARCH_WEB = "search_web"
    OPEN_WEBSITE = "open_website"
    GET_TIME = "get_time"
    GET_DATE = "get_date"
    SYSTEM_INFORMATION = "system_information"
    CPU_STATUS = "cpu_status"
    MEMORY_STATUS = "memory_status"
    STORAGE_STATUS = "storage_status"
    BATTERY_STATUS = "battery_status"
    NETWORK_STATUS = "network_status"
    COMPUTER_STATUS = "computer_status"
    APPLICATION_SEARCH = "application_search"
    RUNNING_APPLICATIONS = "running_applications"
    PROCESS_INFORMATION = "process_information"
    FILE_OPERATION = "file_operation"
    FILE_SEARCH = "file_search"
    FOLDER_OPERATION = "folder_operation"
    READ_FILE = "read_file"
    CREATE_FILE = "create_file"
    LIST_FILES = "list_files"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    TASK = "task"
    TASK_CONTROL = "task_control"
    FOLLOW_UP = "follow_up"
    EXIT = "exit"
    UNKNOWN = "unknown"


# Module-level aliases so `from core.intelligence.intent
# import OPEN_APPLICATION` works as naturally as the class
# attribute.
CONVERSATION = IntentType.CONVERSATION
OPEN_APPLICATION = IntentType.OPEN_APPLICATION
CLOSE_APPLICATION = IntentType.CLOSE_APPLICATION
SEARCH_WEB = IntentType.SEARCH_WEB
OPEN_WEBSITE = IntentType.OPEN_WEBSITE
GET_TIME = IntentType.GET_TIME
GET_DATE = IntentType.GET_DATE
SYSTEM_INFORMATION = IntentType.SYSTEM_INFORMATION
CPU_STATUS = IntentType.CPU_STATUS
MEMORY_STATUS = IntentType.MEMORY_STATUS
STORAGE_STATUS = IntentType.STORAGE_STATUS
BATTERY_STATUS = IntentType.BATTERY_STATUS
NETWORK_STATUS = IntentType.NETWORK_STATUS
COMPUTER_STATUS = IntentType.COMPUTER_STATUS
APPLICATION_SEARCH = IntentType.APPLICATION_SEARCH
RUNNING_APPLICATIONS = IntentType.RUNNING_APPLICATIONS
PROCESS_INFORMATION = IntentType.PROCESS_INFORMATION
FILE_OPERATION = IntentType.FILE_OPERATION
FILE_SEARCH = IntentType.FILE_SEARCH
FOLDER_OPERATION = IntentType.FOLDER_OPERATION
READ_FILE = IntentType.READ_FILE
CREATE_FILE = IntentType.CREATE_FILE
LIST_FILES = IntentType.LIST_FILES
MEMORY = IntentType.MEMORY
KNOWLEDGE = IntentType.KNOWLEDGE
TASK = IntentType.TASK
TASK_CONTROL = IntentType.TASK_CONTROL
FOLLOW_UP = IntentType.FOLLOW_UP
EXIT = IntentType.EXIT
UNKNOWN = IntentType.UNKNOWN


# Maps the deterministic planner's intent types onto the
# intelligence-layer vocabulary.
PLANNER_TO_INTENT = {
    "conversation": IntentType.CONVERSATION,
    "application_action": IntentType.OPEN_APPLICATION,
    "browser_action": IntentType.OPEN_WEBSITE,
    "system_query": IntentType.SYSTEM_INFORMATION,
    "file_action": IntentType.FILE_OPERATION,
    "memory_action": IntentType.MEMORY,
    "knowledge": IntentType.KNOWLEDGE,
    "task": IntentType.TASK,
    "task_control": IntentType.TASK_CONTROL,
    "follow_up": IntentType.FOLLOW_UP,
    "clarification": IntentType.CONVERSATION,
    "exit": IntentType.EXIT,
    "unknown": IntentType.UNKNOWN,
}


@dataclass
class Intent:
    name: str = IntentType.UNKNOWN
    confidence: float = 0.0
    entities: dict = field(default_factory=dict)
    original_text: str = ""
    action: str = ""
    tool_call: "ToolCall | None" = None
    response: str = ""

    def __repr__(self):

        return (
            f"Intent(name={self.name!r}, confidence={self.confidence:.2f}, "
            f"entities={self.entities!r})"
        )