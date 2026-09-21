"""
Risk-based confirmation for tool actions.

Every tool call is assigned a risk level.  Low-risk actions run
automatically; anything at or above the configured threshold asks
the user first.
"""

from typing import ClassVar

from tools.base import ToolCall


class RiskLevels:

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_RISK_RANK = {
    RiskLevels.LOW: 0,
    RiskLevels.MEDIUM: 1,
    RiskLevels.HIGH: 2,
    RiskLevels.CRITICAL: 3,
}


class ConfirmationManager:

    # Tool name -> risk level.  Unknown tools default to HIGH so an
    # unfamiliar capability can never run silently.
    _TOOL_RISKS: ClassVar[dict] = {
        "open_application": RiskLevels.LOW,
        "open_url": RiskLevels.LOW,
        "search_web": RiskLevels.LOW,
        "get_time": RiskLevels.LOW,
        "get_date": RiskLevels.LOW,
        "system_info": RiskLevels.LOW,
        "file_search": RiskLevels.LOW,
        "file_list_directory": RiskLevels.LOW,
        "file_open_file": RiskLevels.LOW,
        "file_open_folder": RiskLevels.LOW,
        "file_read_text": RiskLevels.LOW,
        "file_create_text": RiskLevels.MEDIUM,
        "file_delete": RiskLevels.HIGH,
        "close_application": RiskLevels.HIGH,
    }

    def __init__(self, ask_from=RiskLevels.MEDIUM):
        # Everything at or above this level requires confirmation.
        self.ask_from = ask_from

    def risk_of(self, call):
        """Return the risk level for a ToolCall."""

        if not isinstance(call, ToolCall):
            return RiskLevels.HIGH

        return self._TOOL_RISKS.get(call.name, RiskLevels.HIGH)

    def needs_confirmation(self, call):
        """True when the user must approve the action first."""

        risk = self.risk_of(call)

        return _RISK_RANK[risk] >= _RISK_RANK[self.ask_from]

    def describe(self, call):
        """Human-readable risk description."""

        return f"{call.name} ({self.risk_of(call)} risk)"