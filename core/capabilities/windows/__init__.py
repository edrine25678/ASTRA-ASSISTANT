"""
Windows awareness capabilities (Phase 7).

Every capability here is read-only or confirmation-gated.  Nothing
ever builds or executes a raw shell command from user speech.
"""

from core.capabilities.windows.applications import (
    WindowsApplicationsCapability,
)
from core.capabilities.windows.files import WindowsFilesCapability
from core.capabilities.windows.folders import WindowsFoldersCapability
from core.capabilities.windows.network import NetworkCapability
from core.capabilities.windows.processes import ProcessesCapability
from core.capabilities.windows.storage import StorageCapability
from core.capabilities.windows.system import WindowsSystemCapability


def register_windows_capabilities(registry):
    """Attach every Phase 7 capability to a CapabilityRegistry."""

    registry.register(WindowsSystemCapability())
    registry.register(StorageCapability())
    registry.register(NetworkCapability())
    registry.register(ProcessesCapability())
    registry.register(WindowsApplicationsCapability())
    registry.register(WindowsFilesCapability())
    registry.register(WindowsFoldersCapability())

    return registry


__all__ = [
    "NetworkCapability",
    "ProcessesCapability",
    "StorageCapability",
    "WindowsApplicationsCapability",
    "WindowsFilesCapability",
    "WindowsFoldersCapability",
    "WindowsSystemCapability",
    "register_windows_capabilities",
]