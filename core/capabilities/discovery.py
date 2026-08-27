"""
Application discovery with caching.

Finds installed applications from the Start Menu shortcuts and the
Windows uninstall registry keys, stores the result in a JSON cache,
and matches user phrases against it.  The disk is scanned at most
once per cache-age window - never on every command.

Aliases ("browser" -> Chrome) are resolved here too, so NLU and
capabilities share a single source of truth.
"""

import glob
import json
import os
import re
import winreg
from datetime import datetime

from config.settings import APP_CACHE_PATH, APP_CACHE_MAX_AGE_DAYS

from core.intents import APP_ALIASES

from core.logger import get_logger

logger = get_logger("core.capabilities.discovery")

START_MENU_ROOTS = [
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
]

UNINSTALL_KEYS = [
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE,
     r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER,
     r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

# Every key maps to a canonical application name.
ALIASES = {
    "browser": "chrome",
    "web browser": "chrome",
    "internet browser": "chrome",
    "text editor": "notepad",
    "code editor": "vs code",
    "vscode": "vs code",
    "visual studio code": "vs code",
    "explorer": "file explorer",
    "file manager": "file explorer",
    "files explorer": "file explorer",
    "calc": "calculator",
    "command prompt": "cmd",
    "terminal": "cmd",
}

# Reversed known-app aliases: "not bad" -> notepad etc.
_KNOWN_ALIASES = {}

for _app, _aliases in APP_ALIASES.items():
    for _alias in _aliases:
        _KNOWN_ALIASES[_alias] = _app


class ApplicationDiscovery:

    def __init__(self, cache_path=None, max_age_days=None):

        self.cache_path = (
            cache_path if cache_path is not None else APP_CACHE_PATH
        )

        self.max_age_days = (
            max_age_days if max_age_days is not None
            else APP_CACHE_MAX_AGE_DAYS
        )

        self.apps = []
        self.scanned_at = None

        self._load_cache()

    # ==============================================
    # CACHE
    # ==============================================

    def _load_cache(self):

        try:

            with open(self.cache_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            self.apps = data.get("apps", [])
            self.scanned_at = data.get("scanned_at")

        except (OSError, ValueError, json.JSONDecodeError):

            self.apps = []
            self.scanned_at = None

    def _save_cache(self):

        try:

            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

            with open(self.cache_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "scanned_at": self.scanned_at,
                        "apps": self.apps,
                    },
                    handle,
                    indent=2,
                )

        except OSError as error:

            logger.warning("Could not write app cache: %s", error)

    def _is_fresh(self):

        if not self.scanned_at:
            return False

        try:

            scanned = datetime.fromisoformat(self.scanned_at)

            return (
                datetime.now() - scanned
            ).days < self.max_age_days

        except ValueError:

            return False

    # ==============================================
    # SCAN
    # ==============================================

    def refresh(self, force=False):
        """Rescan the system unless the cache is fresh."""

        if not force and self._is_fresh():
            return

        found = {}

        for name in self._scan_start_menu():
            found[name] = name

        for name in self._scan_registry():
            if name not in found:
                found[name] = name

        self.apps = [
            {"name": name, "display": display}
            for name, display in sorted(found.items())
        ]

        self.scanned_at = datetime.now().isoformat()

        self._save_cache()

        logger.info("Discovered %d applications", len(self.apps))

    def _scan_start_menu(self):

        names = []

        for root in START_MENU_ROOTS:

            pattern = os.path.join(root, "**", "*.lnk")

            for path in glob.glob(pattern, recursive=True):

                stem = os.path.splitext(os.path.basename(path))[0]

                stem = re.sub(
                    r"\s*-\s*shortcut$", "", stem, flags=re.IGNORECASE
                )

                if stem.strip():
                    names.append(stem.strip())

        return names

    def _scan_registry(self):

        names = []

        for hive, key_path in UNINSTALL_KEYS:

            try:

                with winreg.OpenKey(hive, key_path) as key:

                    index = 0

                    while True:

                        try:

                            subkey_name = winreg.EnumKey(key, index)
                            index += 1

                        except OSError:
                            break

                        try:

                            with winreg.OpenKey(
                                hive, key_path + "\\" + subkey_name
                            ) as subkey:

                                display, _ = winreg.QueryValueEx(
                                    subkey, "DisplayName"
                                )

                        except OSError:
                            continue

                        if display and display.strip():
                            names.append(display.strip())

            except OSError:
                continue

        return names

    # ==============================================
    # MATCHING
    # ==============================================

    def find(self, phrase):
        """Resolve a user phrase to a canonical application info.

        Returns {"name": canonical, "display": human name} or None.
        """

        if not phrase:
            return None

        key = phrase.strip().lower()

        # Aliases first.
        if key in ALIASES:
            return self._info(ALIASES[key], phrase)

        if key in _KNOWN_ALIASES:
            return self._info(_KNOWN_ALIASES[key], phrase)

        # Known app aliases in the middle of a phrase ("my browser").
        for alias, app in _KNOWN_ALIASES.items():

            if re.search(r"\b" + re.escape(alias) + r"\b", key):

                if len(alias) > 2:
                    return self._info(app, phrase)

        if not self.apps:
            self.refresh()

        compact = key.replace(" ", "")

        # Exact, then compact, then prefix.
        for info in self.apps:

            name = info["name"].lower()
            name_compact = name.replace(" ", "")

            if name == key:
                return info

            if name_compact == compact:
                return info

        for info in self.apps:

            name = info["name"].lower()
            name_compact = name.replace(" ", "")

            if name_compact.startswith(compact) and len(compact) >= 3:
                return info

        return None

    @staticmethod
    def _info(name, display):
        return {"name": name, "display": display}