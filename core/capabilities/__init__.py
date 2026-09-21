"""
Capability registry and the built-in capabilities.
"""

from core.capabilities.applications import ApplicationsCapability
from core.capabilities.base import Capability, CapabilityRegistry, CapabilityResult
from core.capabilities.browser import BrowserCapability
from core.capabilities.discovery import ApplicationDiscovery
from core.capabilities.files import FilesCapability
from core.capabilities.search import SearchCapability
from core.capabilities.system import SystemCapability
from core.capabilities.windows import (
    NetworkCapability,
    ProcessesCapability,
    StorageCapability,
    WindowsApplicationsCapability,
    WindowsFilesCapability,
    WindowsFoldersCapability,
    WindowsSystemCapability,
    register_windows_capabilities,
)


def build_capability_registry(tool_registry=None, discovery=None):
    """Create a registry with every default capability."""

    registry = CapabilityRegistry(
        tool_registry=tool_registry,
        discovery=discovery,
    )

    registry.register(ApplicationsCapability())
    registry.register(BrowserCapability())
    registry.register(SearchCapability())
    registry.register(SystemCapability())
    registry.register(FilesCapability())
    register_windows_capabilities(registry)

    return registry


__all__ = [
    "ApplicationDiscovery",
    "ApplicationsCapability",
    "BrowserCapability",
    "Capability",
    "CapabilityRegistry",
    "CapabilityResult",
    "FilesCapability",
    "NetworkCapability",
    "ProcessesCapability",
    "SearchCapability",
    "StorageCapability",
    "SystemCapability",
    "WindowsApplicationsCapability",
    "WindowsFilesCapability",
    "WindowsFoldersCapability",
    "WindowsSystemCapability",
    "build_capability_registry",
]