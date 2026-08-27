"""
Capability layer for the intelligence layer.

A capability owns one family of intents (applications, browser,
search, system, files).  Capabilities are self-contained: adding a
new one means writing a class and registering it, nothing else.

Execution goes through the shared ToolRegistry, so the safety
policy and confirmation gate apply exactly as they do for the
deterministic planner.
"""

from dataclasses import dataclass, field


@dataclass
class CapabilityResult:
    response: str
    success: bool = True
    needs_confirmation: bool = False
    data: dict = field(default_factory=dict)
    call: object = None


class Capability:

    name = ""
    description = ""
    intents = ()

    def can_handle(self, intent_name):
        return intent_name in self.intents

    def execute(self, intent, context):
        raise NotImplementedError


class CapabilityRegistry:

    def __init__(self, tool_registry=None, discovery=None):
        self.tool_registry = tool_registry
        self.discovery = discovery
        self._capabilities = []

    def register(self, capability):
        capability.registry = self
        capability.tool_registry = self.tool_registry
        capability.discovery = self.discovery
        self._capabilities.append(capability)
        return capability

    def route(self, intent_name):
        for capability in self._capabilities:
            if capability.can_handle(intent_name):
                return capability
        return None

    def capabilities(self):
        return list(self._capabilities)