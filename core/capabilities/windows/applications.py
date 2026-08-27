"""
Installed-application search (spec sections 7-8).
"""

from core.capabilities.base import Capability, CapabilityResult
from core.intelligence.intent import APPLICATION_SEARCH


class WindowsApplicationsCapability(Capability):

    name = "windows_applications"
    description = "Search the list of installed applications"
    intents = (APPLICATION_SEARCH,)

    def execute(self, intent, context):

        application = (
            intent.entities.get("application")
            or intent.entities.get("target")
        )

        if application:

            info = self.discovery.find(application) if self.discovery else None

            display = (
                info["display"] if info is not None else application
            )

            if info is not None:

                response = f"Yes, {display} is installed."

            else:

                response = (
                    f"I don't see {application} installed on this "
                    "computer."
                )

            return CapabilityResult(
                response=response,
                data={
                    "installed": info is not None,
                    "application": application,
                },
            )

        apps = getattr(self.discovery, "apps", None) if self.discovery else None

        if not apps and self.discovery is not None and hasattr(
            self.discovery, "refresh"
        ):

            self.discovery.refresh()

            apps = getattr(self.discovery, "apps", None)

        if not apps:

            return CapabilityResult(
                success=False,
                response="I couldn't find any installed applications.",
            )

        names = sorted(app["name"] for app in apps)

        preview = ", ".join(names[:12])

        response = (
            f"You have these applications installed: {preview}"
            + (" and more." if len(names) > 12 else ".")
        )

        return CapabilityResult(
            response=response,
            data={"count": len(names), "apps": names[:12]},
        )