"""
Safe file-system capabilities.

File access is strictly scoped: every operation validates the
resolved path against an allow-list of roots (Desktop, Documents,
Downloads by default, overridable for testing).  Writes and
deletes inside the Astra project itself are refused so Astra can
never modify its own source code.  Deletion is the only operation
that permanently removes data, so it requires confirmation.
"""

import os
from datetime import datetime

from config.settings import PROJECT_ROOT

from tools.base import AstraTool, ToolResult

from core.logger import get_logger

logger = get_logger("tools.file")


def _home():
    return os.path.expanduser("~")


def _default_roots():

    roots = []

    for name in ("Desktop", "Documents", "Downloads", "Pictures",
                 "Videos", "Music"):

        path = os.path.normpath(os.path.join(_home(), name))

        if os.path.isdir(path):
            roots.append(path)

    return roots


def _path_allowed(path, roots, writable=False):
    """Return the normalized absolute path when allowed, else None."""

    path = os.path.normpath(os.path.abspath(path))

    if not os.path.isabs(path):
        return None

    if writable:

        project = os.path.normpath(PROJECT_ROOT)

        if path == project or path.startswith(project + os.sep):
            return None

    for root in roots:

        root = os.path.normpath(root)

        if path == root or path.startswith(root + os.sep):
            return path

    return None


def _resolve_folder(folder, roots):
    """Resolve a folder name or path against known folders."""

    raw = (folder or "").strip()

    known = {
        "desktop": os.path.join(_home(), "Desktop"),
        "documents": os.path.join(_home(), "Documents"),
        "downloads": os.path.join(_home(), "Downloads"),
        "pictures": os.path.join(_home(), "Pictures"),
        "videos": os.path.join(_home(), "Videos"),
        "music": os.path.join(_home(), "Music"),
        "home": _home(),
        "astra": PROJECT_ROOT,
        "astra project": PROJECT_ROOT,
        "project": PROJECT_ROOT,
    }

    if raw.lower() in known:
        return known[raw.lower()]

    if os.path.isabs(raw):
        return raw

    return None


def _notes_path():
    return os.path.join(_home(), "Documents", "Astra", "notes.txt")


def _modified_since_days(since):

    today = datetime.now().date()

    if since == "today":
        return 0

    if since == "this week":
        return today.weekday()

    if since == "this month":
        return today.day

    return None


class FileSearchTool(AstraTool):

    name = "file_search"
    description = ("Search for files in allowed folders (Desktop, "
                   "Documents, Downloads, Pictures, Videos, Music)")
    parameters = {
        "query": {"type": "str"},
        "extensions": {"type": "list"},
        "modified_since": {"type": "str"},
        "root": {"type": "str"},
        "modified_within_days": {"type": "int"},
        "max_depth": {"type": "int"},
    }

    DEFAULT_MAX_DEPTH = 5

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        query = (arguments.get("query") or "").strip().lower()
        extensions = arguments.get("extensions") or []
        modified_since = arguments.get("modified_since") or ""
        root_name = (arguments.get("root") or "").strip()
        modified_days = arguments.get("modified_within_days")
        max_depth = arguments.get("max_depth") or self.DEFAULT_MAX_DEPTH

        days = (
            modified_days
            if modified_days is not None
            else (_modified_since_days(modified_since)
                  if modified_since else None)
        )

        if not query and days is None:
            return ToolResult(
                success=False,
                tool=self.name,
                response=(
                    "I can search for files. Try something like "
                    "'find my python files' or 'show me files "
                    "modified today'."
                ),
            )

        roots = list(self.roots)

        if root_name:

            resolved = _resolve_folder(root_name, roots)

            if resolved is not None:

                path = _path_allowed(resolved, roots)

                if path is not None and os.path.isdir(path):
                    roots = [path]
                else:
                    roots = []

        if not roots:

            return ToolResult(
                success=False,
                tool=self.name,
                data={"files": []},
                response=(
                    f"I couldn't search inside {root_name} - it is "
                    "not one of my allowed folders."
                ),
            )

        found = []

        for root in roots:

            root = os.path.normpath(root)

            for current, directories, filenames in os.walk(root):

                directories[:] = [
                    d for d in directories
                    if not d.startswith("$") and d not in ("AppData", "node_modules")
                ]

                depth = current.count(os.sep) - root.count(os.sep)

                if depth > max_depth:
                    directories[:] = []
                    continue

                for filename in filenames:

                    name_lower = filename.lower()

                    if extensions and not any(
                        name_lower.endswith(ext) for ext in extensions
                    ):
                        continue

                    if query and query not in name_lower:
                        continue

                    path = os.path.join(current, filename)

                    if days is not None:

                        try:
                            modified = datetime.fromtimestamp(
                                os.path.getmtime(path)
                            ).date()
                        except OSError:
                            continue

                        delta = (datetime.now().date() - modified).days

                        if delta > days:
                            continue

                    found.append(path)

                    if len(found) >= 20:
                        break

                if len(found) >= 20:
                    break

            if len(found) >= 20:
                break

        if not found:

            where = "your allowed folders"

            if len(roots) == 1:
                where = os.path.basename(roots[0].rstrip(os.sep)) or "that folder"

            return ToolResult(
                success=False,
                tool=self.name,
                data={"files": []},
                response=(
                    f"I couldn't find any matching files in {where}."
                ),
            )

        preview = "; ".join(found[:3])

        response = (
            f"I found {len(found)} matching file(s): {preview}."
        )

        return ToolResult(
            success=True,
            tool=self.name,
            data={"files": found, "count": len(found)},
            response=response,
        )


class FileListDirectoryTool(AstraTool):

    name = "file_list_directory"
    description = "List the contents of a folder"
    parameters = {"path": {"type": "str", "required": True}}

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        folder = _resolve_folder(
            arguments.get("path") or "", self.roots
        )

        path = _path_allowed(folder, self.roots) if folder else None

        if path is None or not os.path.isdir(path):
            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't open that folder.",
            )

        names = sorted(os.listdir(path))

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path, "items": names},
            response=(
                f"The folder contains {len(names)} item(s). "
                f"First few: {', '.join(names[:5])}."
            ),
        )


class FileOpenFileTool(AstraTool):

    name = "file_open_file"
    description = "Open a file with its default application"
    parameters = {"path": {"type": "str", "required": True}}

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        path = _path_allowed(arguments.get("path") or "", self.roots)

        if path is None or not os.path.isfile(path):
            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't find that file.",
            )

        os.startfile(path)

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path},
            response=f"Opening {os.path.basename(path)}.",
        )


class FileOpenFolderTool(AstraTool):

    name = "file_open_folder"
    description = "Open a folder in File Explorer"
    parameters = {"path": {"type": "str", "required": True}}

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        folder = _resolve_folder(
            arguments.get("path") or "", self.roots
        )

        path = _path_allowed(folder, self.roots) if folder else None

        if path is None or not os.path.isdir(path):
            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't find that folder.",
            )

        os.startfile(path)

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path},
            response=f"Opening {os.path.basename(path)}.",
        )


class FileReadTextTool(AstraTool):

    name = "file_read_text"
    description = "Read the beginning of a text file"
    parameters = {"path": {"type": "str", "required": True}}

    MAX_CHARS = 4000

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        path = _path_allowed(arguments.get("path") or "", self.roots)

        if path is None or not os.path.isfile(path):
            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't find that file.",
            )

        try:

            with open(path, "r", encoding="utf-8", errors="replace") as file:
                content = file.read(self.MAX_CHARS)

        except OSError as error:

            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't read that file.",
                error=str(error),
            )

        excerpt = content.strip() or "(empty file)"

        if len(excerpt) > 300:
            excerpt = excerpt[:300] + "..."

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path, "content": content},
            response=f"Here's what it says: {excerpt}",
        )


class FileCreateTextTool(AstraTool):

    name = "file_create_text"
    description = "Create a text file (confirmation required)"
    parameters = {
        "path": {"type": "str"},
        "content": {"type": "str", "required": True},
    }

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        content = (arguments.get("content") or "").strip()

        if not content:
            return ToolResult(
                success=False,
                tool=self.name,
                response="I need some content to write.",
            )

        path = _path_allowed(
            arguments.get("path") or _notes_path(),
            self.roots,
            writable=True,
        )

        if path is None:
            return ToolResult(
                success=False,
                tool=self.name,
                response=(
                    "I can only create files in your Documents, "
                    "Desktop, or Downloads folders, and I will not "
                    "modify the Astra project itself."
                ),
            )

        try:

            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, "w", encoding="utf-8") as file:
                file.write(content + "\n")

        except OSError as error:

            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't create that file.",
                error=str(error),
            )

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path},
            response=f"Created {os.path.basename(path)}.",
        )


class FileDeleteTool(AstraTool):

    name = "file_delete"
    description = "Delete a file (confirmation required)"
    parameters = {"path": {"type": "str", "required": True}}

    requires_confirmation = True

    def __init__(self, allowed_roots=None):
        self.roots = allowed_roots or _default_roots()

    def run(self, arguments):

        path = _path_allowed(
            arguments.get("path") or "", self.roots, writable=True
        )

        if path is None or not os.path.isfile(path):
            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't find that file to delete.",
            )

        try:

            os.remove(path)

        except OSError as error:

            return ToolResult(
                success=False,
                tool=self.name,
                response="I couldn't delete that file.",
                error=str(error),
            )

        return ToolResult(
            success=True,
            tool=self.name,
            data={"path": path},
            response=f"Deleted {os.path.basename(path)}.",
        )