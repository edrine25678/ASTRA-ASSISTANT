"""
Planning: convert raw text into a structured Intent.

The current planner is a deterministic local fallback that keeps
Astra fully functional without any AI model.  A model-based planner
can replace it later as long as it implements the same plan()
interface.
"""

import re
from typing import ClassVar

from ai.intent import (
    APPLICATION_ACTION,
    BROWSER_ACTION,
    CLARIFICATION,
    CONVERSATION,
    EXIT,
    FILE_ACTION,
    FOLLOW_UP,
    KNOWLEDGE,
    MEMORY_ACTION,
    SYSTEM_QUERY,
    TASK,
    TASK_CONTROL,
    UNKNOWN,
    Intent,
)
from core.intents import OPEN_VERBS, detect_intent
from tools.base import ToolCall


class FallbackPlanner:

    # Websites handled by the browser tool.
    BROWSER_SITES = ("youtube", "google", "gmail", "chatgpt", "github")

    EXIT_PHRASES = (
        "exit astra",
        "quit astra",
        "shutdown astra",
        "stop listening",
        "goodbye astra",
    )

    GREETING_PHRASES = (
        "hello astra",
        "hi astra",
        "hey astra",
        "hello",
        "hi",
        "good morning",
        "good evening",
    )

    INTRO_PHRASES = (
        "who are you",
        "what are you",
        "what is your name",
        "what's your name",
        "tell me about yourself",
        "what do you know about yourself",
        "what do you remember about yourself",
    )

    THANKS_PHRASES = ("thank you", "thanks")

    FACT_PHRASES = ("did you know", "fun fact", "tell me something interesting")

    TIRED_PHRASES = (
        "i am tired",
        "i'm tired",
        "im tired",
        "i am sleepy",
        "i'm sleepy",
        "i am exhausted",
    )

    LOVE_PHRASES = ("i love you", "i like you", "i love astra")

    TIME_PHRASES = (
        "what time is it",
        "tell me the time",
        "current time",
        "time",
    )

    DATE_PHRASES = (
        "what is today's date",
        "what's today's date",
        "tell me the date",
        "today's date",
        "current date",
        "what day is it",
    )

    FILE_PHRASES = (
        "find a file",
        "find my files",
        "find the file",
        "locate a file",
        "search my files",
        "search for a file",
        "where is my file",
        "where are my files",
    )

    SEARCH_PREFIX = re.compile(
        r"^(search the web|search the internet|search)"
    )

    NAV_PREFIX = re.compile(
        r"^(take me to|go to|navigate to|open)\s+(.+)$"
    )

    NEED_PREFIX = re.compile(
        r"^i\s+(?:need|want|would like)\s+"
        r"(?:you\s+to\s+)?(?:to\s+)?(?:the\s+|a\s+|an\s+)?(.+)$"
    )

    DOMAIN_PATTERN = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")

    # ==============================================
    # MEMORY
    # ==============================================

    MEMORY_SAVE_PREFIX = re.compile(
        r"^(?:please\s+)?(?:remember|note|note that|write this down|"
        r"write that down|save this|jot down)\s+"
        r"(?:that\s+)?(.+)$"
    )

    MEMORY_RECALL_PHRASES = (
        "what do you remember about",
        "what do you know about",
        "what do you remember",
        "what have you remembered",
        "what did i tell you",
        "what have i told you",
        "what have you stored",
        "do you remember",
        "recall",
    )

    MEMORY_FORGET_PREFIX = re.compile(
        r"^(?:please\s+)?(?:forget|forget about|erase|erase from memory|"
        r"remove from memory|delete from memory|unremember)\s+"
        r"(?:about\s+)?(.+)$"
    )

    # ==============================================
    # KNOWLEDGE QUESTIONS
    # ==============================================

    KNOWLEDGE_PREFIX = re.compile(
        r"^(?:what is|what's|who is|who's|when did|when does|when was|"
        r"where is|where's|why is|why does|why did|how does|how do|"
        r"how to|which is|explain|tell me about|define)\b"
    )

    # ==============================================
    # UNKNOWN APPLICATIONS
    # ==============================================

    GENERIC_OPEN = re.compile(
        r"^(?:open|launch|start|run|opening)\s+(.+)$"
    )

    # ==============================================
    # TASK CONTROL
    # ==============================================

    CANCEL_PHRASES = (
        "cancel that",
        "cancel the task",
        "cancel this",
        "cancel it",
        "stop the task",
        "stop that",
        "stop it",
        "stop what you're doing",
        "stop what you are doing",
        "never mind",
        "forget it",
        "forget that",
        "abort the task",
        "scratch that",
        "skip it",
    )

    STATUS_PHRASES = (
        "what are you doing",
        "what's happening",
        "what is happening",
        "what is the current task",
        "what's the current task",
        "what are you working on",
        "are you finished",
        "are you done",
        "are you still working",
        "what's the status",
        "what is the status",
        "status report",
    )

    # ==============================================
    # FOLLOW-UPS
    # ==============================================

    FOLLOW_UP_PHRASES = (
        "the first one",
        "the second one",
        "the third one",
        "the fourth one",
        "the first result",
        "the second result",
        "the third result",
        "the last one",
        "the last result",
        "the next one",
        "the previous one",
        "first one",
        "second one",
        "third one",
        "number one",
        "number two",
        "number three",
        "that one",
        "this one",
        "the first",
        "the second",
        "the third",
        "the last",
        "the next",
        "pick the first one",
        "pick the second one",
        "choose the second one",
        "open the first one",
        "open the second one",
        "open the last one",
        "open the next one",
    )

    ORDINAL_INDEX: ClassVar[dict] = {
        "first": 0,
        "second": 1,
        "third": 2,
        "fourth": 3,
    }

    # ==============================================
    # TASK GOALS
    # ==============================================

    TASK_SEPARATOR = re.compile(
        r"\s*(?:,|\band\b|\bthen\b|\band\s+then\b|;|\bafter that\b)\s*"
    )

    VERB_GROUP = re.compile(
        r"^(?:open|launch|start|run|opening)\s+(.+)$"
    )

    # ==============================================
    # CLARIFICATION
    # ==============================================

    CLARIFICATION_YES: ClassVar[set] = {
        "yes", "yeah", "yep", "y", "sure", "ok", "okay",
        "alright", "fine", "uh huh", "go ahead",
    }

    CLARIFICATION_NO: ClassVar[set] = {
        "no", "nope", "n", "nah", "not now",
    }

    # ==============================================
    # FILES
    # ==============================================

    FILE_SEARCH_PATTERN = re.compile(
        r"^(?:find|search|locate|show me)\s+"
        r"(?:for\s+|my\s+|the\s+|all\s+)?(.+?)\s+files?$"
    )

    FILES_MODIFIED_PATTERN = re.compile(
        r"\bfiles?\s+(?:modified|changed)\s+(today|this week|this month)\b"
    )

    WHERE_FILES_PATTERN = re.compile(
        r"^where\s+(?:are|is)\s+(?:my\s+|the\s+)?(.+?)\s+files?$"
    )

    OPEN_FOLDER_PATTERN = re.compile(
        r"^open\s+(?:the\s+|my\s+)?(.+?)\s+(?:folder|project|directory)$"
    )

    READ_FILE_PATTERN = re.compile(r"^read\s+(?:the\s+|the file\s+|file\s+)?(.+)$")

    LIST_FOLDER_PATTERN = re.compile(
        r"^list\s+(?:the\s+|my\s+|this\s+)?(.+?)\s+(?:folder|directory)$"
    )

    WRITE_DOWN_PATTERN = re.compile(r"^write down\s+(.+)$")

    DELETE_PATTERN = re.compile(r"^delete\s+(?:the\s+|this\s+|that\s+)?(.+)$")

    KNOWN_FOLDERS: ClassVar[dict] = {
        "desktop": "desktop",
        "documents": "documents",
        "my documents": "documents",
        "downloads": "downloads",
        "astra": "astra",
        "astra project": "astra",
        "my project": "astra",
    }

    # ==============================================
    # SYSTEM: BATTERY AND USAGE
    # ==============================================

    BATTERY_PHRASES = (
        "battery level",
        "how much battery",
        "battery",
        "plugged in",
        "charging",
        "power status",
    )

    CPU_USAGE_PHRASES = (
        "cpu usage",
        "processor usage",
        "cpu load",
        "how much cpu",
        "how much of my cpu",
    )

    MEMORY_USAGE_PHRASES = (
        "memory usage",
        "ram usage",
        "how much memory am i using",
        "how much ram am i using",
        "used memory",
        "memory in use",
    )

    # ==============================================
    # TASK RECALL (memory)
    # ==============================================

    TASK_RECALL_PHRASES = (
        "what did i just ask you",
        "what did i ask you",
        "what did we just do",
        "what did we do",
        "what were we doing",
        "what was the last task",
        "what was the last thing",
        "what have you done recently",
        "recent tasks",
        "what did you just do",
    )

    # ==============================================
    # PLANNING
    # ==============================================

    def plan(self, text):
        """Convert raw text into a structured Intent."""

        raw = (text or "").lower().strip("?!.,;: ")

        if not raw:
            return self._unknown(text)

        # ==================================
        # EXIT
        # ==================================

        if any(phrase in raw for phrase in self.EXIT_PHRASES):
            return Intent(EXIT, confidence=1.0, raw_text=text)

        # ==================================
        # TASK CONTROL: CANCEL
        # ==================================

        if any(phrase in raw for phrase in self.CANCEL_PHRASES):
            return Intent(
                TASK_CONTROL,
                action="cancel",
                confidence=1.0,
                raw_text=text,
            )

        # ==================================
        # TASK CONTROL: STATUS
        # ==================================

        if any(phrase in raw for phrase in self.STATUS_PHRASES):
            return Intent(
                TASK_CONTROL,
                action="status",
                confidence=1.0,
                raw_text=text,
            )

        # ==================================
        # MEMORY
        # ("remember that X", "what do you
        #  remember about X", "forget X")
        # ==================================

        memory_intent = self._memory_intent(raw, text)

        if memory_intent:
            return memory_intent

        # ==================================
        # FOLLOW-UPS
        # ("the first one", "open the second")
        # ==================================

        follow_up = self._follow_up_intent(raw, text)

        if follow_up:
            return follow_up

        # ==================================
        # MULTI-STEP TASKS
        # ("open chrome and open youtube",
        #  "open notepad and calculator")
        # ==================================

        task = self._task_intent(raw, text)

        if task:
            return task

        # ==================================
        # FILES
        # (before conversation so that
        #  "write down hello world" is not
        #  swallowed by the "hello" greeting)
        # ==================================

        file_intent = self._file_intent(raw, text)

        if file_intent:
            return file_intent

        # ==================================
        # CONVERSATION
        # ==================================

        if any(phrase in raw for phrase in self.GREETING_PHRASES):
            return self._conversation(
                "Hello Edrine. How can I help you?", text
            )

        if "how are you" in raw:
            return self._conversation(
                "I'm doing great, Edrine. I'm ready to help.", text
            )

        if any(phrase in raw for phrase in self.INTRO_PHRASES):
            return self._conversation(
                "I'm Astra, your personal desktop assistant.", text
            )

        if any(phrase in raw for phrase in self.THANKS_PHRASES):
            return self._conversation(
                "You're welcome, Edrine.", text
            )

        if any(phrase in raw for phrase in self.FACT_PHRASES):
            return self._conversation(
                "I know quite a lot, Edrine, but without a knowledge "
                "provider I prefer to stick to what I can verify.",
                text,
            )

        if any(phrase in raw for phrase in self.TIRED_PHRASES):
            return self._conversation(
                "Then you should get some rest, Edrine. "
                "I'll be here when you need me.",
                text,
            )

        if any(phrase in raw for phrase in self.LOVE_PHRASES):
            return self._conversation(
                "That's very kind of you, Edrine. "
                "I'm here whenever you need me.",
                text,
            )

        # ==================================
        # SYSTEM QUERIES
        # ==================================

        if any(phrase in raw for phrase in self.TIME_PHRASES):
            return self._system_query("get_time", {}, 1.0, text)

        if any(phrase in raw for phrase in self.DATE_PHRASES):
            return self._system_query("get_date", {}, 1.0, text)

        # Usage queries come before total queries because
        # "how much ram am i using" contains "how much ram".
        if any(phrase in raw for phrase in self.MEMORY_USAGE_PHRASES):
            return self._system_query(
                "system_info", {"topic": "memory_usage"}, 1.0, text
            )

        if any(phrase in raw for phrase in self.CPU_USAGE_PHRASES):
            return self._system_query(
                "system_info", {"topic": "cpu_usage"}, 1.0, text
            )

        if any(phrase in raw for phrase in self.BATTERY_PHRASES):
            return self._system_query(
                "system_info", {"topic": "battery"}, 1.0, text
            )

        if (
            "operating system" in raw
            or "windows version" in raw
            or re.search(r"\bwhat os\b", raw)
        ):
            return self._system_query(
                "system_info", {"topic": "os"}, 1.0, text
            )

        if (
            "how much ram" in raw
            or "how much memory" in raw
            or "total memory" in raw
            or "free memory" in raw
        ):
            return self._system_query(
                "system_info", {"topic": "memory"}, 1.0, text
            )

        if "processor" in raw or re.search(r"\bcpu\b", raw):
            return self._system_query(
                "system_info", {"topic": "cpu"}, 1.0, text
            )

        if (
            "disk space" in raw
            or "hard drive" in raw
            or "storage" in raw
            or "disk usage" in raw
            or "free space" in raw
        ):
            return self._system_query(
                "system_info", {"topic": "disk"}, 1.0, text
            )

        if (
            "what is running" in raw
            or "what's running" in raw
            or "applications are running" in raw
            or "programs are running" in raw
            or ("processes" in raw and "running" in raw)
        ):
            return self._system_query(
                "system_info", {"topic": "processes"}, 1.0, text
            )

        # ==================================
        # SEARCH THE WEB
        # ==================================

        search = self._search_intent(raw, text)

        if search:
            return search

        # ==================================
        # APPLICATIONS AND WEBSITES
        # ==================================

        detected = detect_intent(raw)

        if detected is not None:

            if detected.target in self.BROWSER_SITES:
                return self._browser_open(
                    detected.target, detected.confidence, text
                )

            return self._application_open(
                detected.target, detected.confidence, text
            )

        # ==================================
        # NAVIGATION PHRASING
        # ("take me to youtube", "open github.com")
        # ==================================

        match = self.NAV_PREFIX.match(raw)

        if match:

            target = match.group(2).strip()

            if (
                target in self.BROWSER_SITES
                or self.DOMAIN_PATTERN.fullmatch(target)
            ):
                return self._browser_open(target, 0.9, text)

            resolved = detect_intent(f"open {target}")

            if resolved is not None:

                if resolved.target in self.BROWSER_SITES:
                    return self._browser_open(
                        resolved.target, 0.9, text
                    )

                return self._application_open(
                    resolved.target, 0.9, text
                )

        # ==================================
        # NEED / WANT PHRASING
        # ("i need the calculator")
        # ==================================

        match = self.NEED_PREFIX.match(raw)

        if match:

            wanted = match.group(1).strip()

            first = wanted.split()[0] if wanted.split() else ""

            candidate = wanted if first in OPEN_VERBS else f"open {wanted}"

            resolved = detect_intent(candidate)

            if resolved is not None:

                if resolved.target in self.BROWSER_SITES:
                    return self._browser_open(
                        resolved.target, 0.85, text
                    )

                return self._application_open(
                    resolved.target, 0.85, text
                )

        # ==================================
        # UNKNOWN APPLICATIONS
        # ("open discord", "launch spotify")
        # ==================================

        generic = self._generic_application_open(raw, text)

        if generic:
            return generic

        # ==================================
        # KNOWLEDGE QUESTIONS
        # ("what is python", "how does the
        #  internet work")
        # ==================================

        knowledge = self._knowledge_intent(raw, text)

        if knowledge:
            return knowledge

        # ==================================
        # CLARIFICATION
        # ("yes", "no", "okay")
        # ==================================

        clarification = self._clarification_intent(raw, text)

        if clarification:
            return clarification

        # ==================================
        # UNKNOWN
        # ==================================

        return self._unknown(text)

    # ==============================================
    # HELPERS
    # ==============================================

    def _clarification_intent(self, raw, text):

        if raw in self.CLARIFICATION_YES:
            return Intent(
                CLARIFICATION,
                action="yes",
                confidence=1.0,
                raw_text=text,
            )

        if raw in self.CLARIFICATION_NO:
            return Intent(
                CLARIFICATION,
                action="no",
                confidence=1.0,
                raw_text=text,
            )

        return None

    def _follow_up_intent(self, raw, text):

        for phrase in self.FOLLOW_UP_PHRASES:

            if phrase in raw:

                index = None

                if phrase.startswith("number"):
                    index = {
                        "one": 0, "two": 1, "three": 2, "four": 3,
                    }.get(phrase.split()[-1])
                elif phrase.startswith("the "):
                    index = self.ORDINAL_INDEX.get(
                        phrase.split()[1]
                    )
                elif phrase in (
                    "first one", "second one", "third one"
                ):
                    index = self.ORDINAL_INDEX.get(
                        phrase.split()[0]
                    )

                if "last" in phrase:
                    index = "last"
                elif "next" in phrase:
                    index = "next"
                elif "that" in phrase or "this" in phrase:
                    index = "only"

                if index is None:
                    continue

                return Intent(
                    FOLLOW_UP,
                    action="resolve",
                    parameters={"index": index},
                    confidence=0.9,
                    raw_text=text,
                )

        return None

    def _task_intent(self, raw, text):

        # 1. Separator-split: two or more self-contained clauses.
        parts = [
            part.strip()
            for part in self.TASK_SEPARATOR.split(raw)
            if part.strip()
        ]

        if len(parts) >= 2:

            resolvable = [part for part in parts if self._resolves(part)]

            if len(resolvable) >= 2:
                return self._task(raw, text)

        # 2. Verb group: "open chrome and youtube".
        match = self.VERB_GROUP.match(raw)

        if match:

            targets = [
                target.strip()
                for target in re.split(r"\s*(?:,|and)\s*", match.group(1))
                if target.strip()
            ]

            if len(targets) >= 2:

                resolved = [
                    target
                    for target in targets
                    if self._resolves(
                        target
                        if target.split()[0] in OPEN_VERBS
                        else f"open {target}"
                    )
                ]

                if len(resolved) >= 2:
                    return self._task(raw, text)

        return None

    def _task(self, raw, text):

        return Intent(
            TASK,
            parameters={"goal": text},
            confidence=0.85,
            raw_text=text,
        )

    def _resolves(self, part):
        """True when a clause can be planned as a concrete step."""

        intent = self.plan(part)

        return intent.type not in (UNKNOWN,)

    def _file_intent(self, raw, text):

        # "show me files modified today"
        match = self.FILES_MODIFIED_PATTERN.search(raw)

        if match:

            parameters = {
                "query": "",
                "modified_since": match.group(1),
            }

            return self._file_tool_intent("file_search", parameters, 0.9, text)

        # "find my python files"
        match = self.FILE_SEARCH_PATTERN.match(raw)

        if match:

            query = match.group(1).strip()

            extensions = [".py"] if query == "python" else None

            return self._file_tool_intent(
                "file_search",
                {"query": query, "extensions": extensions},
                0.9,
                text,
            )

        # "where are my python files"
        match = self.WHERE_FILES_PATTERN.match(raw)

        if match:

            return self._file_tool_intent(
                "file_search",
                {"query": match.group(1).strip()},
                0.9,
                text,
            )

        # "where are my downloads" (known folders)
        match = re.match(
            r"^where\s+(?:are|is)\s+(?:my\s+|the\s+)?(.+)$", raw
        )

        if match:

            folder = self.KNOWN_FOLDERS.get(match.group(1).strip())

            if folder:

                return self._file_tool_intent(
                    "file_list_directory",
                    {"path": folder},
                    0.9,
                    text,
                )

        # "open the astra folder"
        match = self.OPEN_FOLDER_PATTERN.match(raw)

        if match:

            folder = match.group(1).strip()

            return self._file_tool_intent(
                "file_open_folder",
                {"path": folder},
                0.9,
                text,
            )

        # "list the documents folder"
        match = self.LIST_FOLDER_PATTERN.match(raw)

        if match:

            return self._file_tool_intent(
                "file_list_directory",
                {"path": match.group(1).strip()},
                0.9,
                text,
            )

        # "read C:\path\file.txt"
        match = self.READ_FILE_PATTERN.match(raw)

        if match:

            return self._file_tool_intent(
                "file_read_text",
                {"path": match.group(1).strip()},
                0.9,
                text,
            )

        # "write down python is cool"
        match = self.WRITE_DOWN_PATTERN.match(raw)

        if match:

            return self._file_tool_intent(
                "file_create_text",
                {"path": "", "content": match.group(1).strip()},
                0.9,
                text,
            )

        # "delete C:\path\file.txt"
        match = self.DELETE_PATTERN.match(raw)

        if match:

            return self._file_tool_intent(
                "file_delete",
                {"path": match.group(1).strip()},
                0.85,
                text,
            )

        # Generic file help ("find a file", "search my files").
        if any(phrase in raw for phrase in self.FILE_PHRASES):

            return Intent(
                FILE_ACTION,
                action="file_search",
                confidence=0.8,
                raw_text=text,
                response=(
                    "I can search for files. Try something like "
                    "'find my python files' or 'show me files "
                    "modified today'."
                ),
            )

        return None

    def _file_tool_intent(self, tool, parameters, confidence, text):

        return Intent(
            FILE_ACTION,
            action=tool,
            parameters=parameters,
            confidence=confidence,
            raw_text=text,
            tool_call=ToolCall(tool, parameters),
        )

    def _memory_intent(self, raw, text):

        match = self.MEMORY_SAVE_PREFIX.match(raw)

        if match:

            content = match.group(1).strip()

            if content:

                return Intent(
                    MEMORY_ACTION,
                    action="save",
                    parameters={
                        "content": content,
                        "category": self._memory_category(content),
                    },
                    confidence=0.9,
                    raw_text=text,
                )

        match = self.MEMORY_FORGET_PREFIX.match(raw)

        if match:

            query = match.group(1).strip()

            if query:

                return Intent(
                    MEMORY_ACTION,
                    action="forget",
                    parameters={"query": query},
                    confidence=0.9,
                    raw_text=text,
                )

        if any(phrase in raw for phrase in self.TASK_RECALL_PHRASES):

            return Intent(
                MEMORY_ACTION,
                action="recall",
                parameters={"query": None, "category": "tasks"},
                confidence=0.9,
                raw_text=text,
            )

        if any(
            phrase in raw for phrase in self.MEMORY_RECALL_PHRASES
        ):

            query = None

            about = re.search(r"\babout\s+(.+)$", raw)

            if about:
                query = about.group(1).strip()

            return Intent(
                MEMORY_ACTION,
                action="recall",
                parameters={"query": query, "category": None},
                confidence=0.9,
                raw_text=text,
            )

        return None

    @staticmethod
    def _memory_category(content):

        if re.search(
            r"\b(prefer|preference|favorite|like|love|hate|want)\b",
            content,
        ):
            return "preferences"

        if re.search(r"\b(from now on|always|never)\b", content):
            return "instructions"

        if re.search(r"\b(fact|did you know that)\b", content):
            return "facts"

        return "long_term"

    def _knowledge_intent(self, raw, text):

        if not self.KNOWLEDGE_PREFIX.match(raw):
            return None

        query = self.KNOWLEDGE_PREFIX.sub("", raw).strip()

        if not query or len(query) > 80:
            return None

        return Intent(
            KNOWLEDGE,
            parameters={"query": query},
            confidence=0.7,
            raw_text=text,
        )

    def _generic_application_open(self, raw, text):

        match = self.GENERIC_OPEN.match(raw)

        if not match:
            return None

        target = match.group(1).strip()

        if not target or len(target) > 40:
            return None

        if self.DOMAIN_PATTERN.fullmatch(target):
            return self._browser_open(target, 0.55, text)

        return self._application_open(target, 0.55, text)

    def _search_intent(self, raw, text):

        match = self.SEARCH_PREFIX.match(raw)

        if not match:
            return None

        rest = raw[match.end():].strip()

        if rest.startswith("for "):
            rest = rest[4:].strip()

        engine = "google"

        for name in ("youtube", "duckduckgo", "bing", "google"):

            if rest.startswith(name + " "):

                engine = name

                rest = rest[len(name):].strip()

                break

        if rest.startswith("for "):
            rest = rest[4:].strip()

        if not rest:
            return None

        parameters = {"query": rest, "engine": engine}

        return Intent(
            BROWSER_ACTION,
            action="search_web",
            parameters=parameters,
            confidence=0.9,
            raw_text=text,
            tool_call=ToolCall("search_web", parameters),
        )

    def _system_query(self, action, parameters, confidence, text):

        return Intent(
            SYSTEM_QUERY,
            action=action,
            parameters=parameters,
            confidence=confidence,
            raw_text=text,
            tool_call=ToolCall(action, parameters),
        )

    def _application_open(self, target, confidence, text):

        return Intent(
            APPLICATION_ACTION,
            action="open_application",
            target=target,
            confidence=confidence,
            raw_text=text,
            tool_call=ToolCall(
                "open_application", {"application": target}
            ),
        )

    def _browser_open(self, target, confidence, text):

        return Intent(
            BROWSER_ACTION,
            action="open_url",
            target=target,
            confidence=confidence,
            raw_text=text,
            tool_call=ToolCall("open_url", {"url": target}),
        )

    def _conversation(self, response, text):

        return Intent(
            CONVERSATION,
            response=response,
            confidence=1.0,
            raw_text=text,
        )

    def _unknown(self, text):

        return Intent(
            UNKNOWN,
            response="I don't know how to do that yet.",
            confidence=0.0,
            raw_text=text,
        )