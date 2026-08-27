"""
Generalized application-launching capability.

The tool accepts a canonical application name and determines how to
launch it.  Known applications use dedicated launch code; everything
else is discovered through the PATH, the Start Menu shortcuts, or a
small table of Windows shell targets.  When nothing is found, the
tool reports gracefully instead of failing.
"""

import os
import re
import subprocess
import glob
from shutil import which

from tools.base import Tool, ToolResult

from core.intents import canonical


class OpenApplicationTool(Tool):

    name = "open_application"
    description = "Open an installed Windows application"
    parameters = {
        "application": {"type": "str", "required": True}
    }

    # Canonical name -> spoken confirmation.
    RESPONSES = {
        "chrome": "Opening Chrome.",
        "notepad": "Opening Notepad.",
        "calculator": "Opening Calculator.",
        "file explorer": "Opening File Explorer.",
        "vs code": "Opening Visual Studio Code.",
    }

    CHROME_PATHS = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(
            r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
        ),
    ]

    # Fallbacks for well-known targets that are not executables on
    # the PATH.  "start" means: hand the string to the shell.
    SHELL_TARGETS = {
        "settings": "ms-settings:",
        "windows settings": "ms-settings:",
        "control panel": "control",
        "file explorer": "explorer.exe",
    }

    START_MENU_ROOTS = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
    ]

    def validate(self, arguments):
        return super().validate(arguments)

    def find_application(self, name):
        """Locate a launcher for an application name.

        Returns one of:
            ("exe", path_or_command)  run with subprocess
            ("lnk", path)             open with os.startfile
            ("start", target)         run through the shell
            None                      nothing found
        """

        name = canonical(name).lower()

        name = re.sub(r"\s+app$", "", name)

        # 1. Executables on the PATH.
        for candidate in (name + ".exe", name):

            found = which(candidate)

            if found:
                return ("exe", found)

        # 2. Start Menu shortcuts (most installed programs).
        shortcut = self._find_start_menu_shortcut(name)

        if shortcut:
            return ("lnk", shortcut)

        # 3. Well-known shell targets.
        if name in self.SHELL_TARGETS:
            return ("start", self.SHELL_TARGETS[name])

        return None

    def _find_start_menu_shortcut(self, name):

        compact = name.replace(" ", "")

        for root in self.START_MENU_ROOTS:

            pattern = os.path.join(root, "**", "*.lnk")

            for path in glob.glob(pattern, recursive=True):

                stem = os.path.splitext(os.path.basename(path))[0]

                stem = re.sub(r"\s*-\s*shortcut$", "", stem, flags=re.IGNORECASE)

                stem_compact = stem.replace(" ", "")

                if (
                    stem.lower() == name
                    or stem_compact.lower() == compact
                    or stem_compact.lower().startswith(compact)
                ):
                    return path

        return None

    def run(self, arguments):

        application = (
            arguments.get("application") or ""
        ).strip().lower()

        # ==============================================
        # KNOWN APPLICATIONS (dedicated launch code)
        # ==============================================

        if application == "chrome":
            self._launch_chrome()
        elif application == "notepad":
            subprocess.Popen("notepad.exe", shell=True)
        elif application == "calculator":
            subprocess.Popen("calc.exe", shell=True)
        elif application == "file explorer":
            subprocess.Popen("explorer.exe", shell=True)
        elif application == "vs code":
            subprocess.Popen("code", shell=True)

        if application in self.RESPONSES:

            return ToolResult(
                success=True,
                data={"application": application},
                response=self.RESPONSES[application],
            )

        # ==============================================
        # DISCOVERED APPLICATIONS
        # ==============================================

        launcher = self.find_application(application)

        if launcher is None:

            return ToolResult(
                success=False,
                data={"application": application},
                response=(
                    f"I couldn't find an application called {application}."
                ),
                error=f"Application not found: {application}",
            )

        kind, target = launcher

        if kind == "exe":
            subprocess.Popen([target])
        elif kind == "lnk":
            os.startfile(target)
        else:
            subprocess.Popen(target, shell=True)

        return ToolResult(
            success=True,
            data={"application": application, "launcher": launcher},
            response=f"Opening {application}.",
        )

    def _launch_chrome(self):

        for path in self.CHROME_PATHS:

            if os.path.exists(path):

                subprocess.Popen([path])

                return

        subprocess.Popen(
            "start chrome",
            shell=True
        )