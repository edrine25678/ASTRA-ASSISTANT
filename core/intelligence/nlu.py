"""
Natural-language understanding for the intelligence layer.

NLU is signal-based, not phrase-based: each intent carries a set of
synonym words ("open", "launch", "start", "bring", ...) and entities
are extracted semantically (applications through the discovery
cache, websites, search queries, dates).  Adding an intent means
adding a signal group, not hundreds of hard-coded phrases.

The deterministic planner remains the first pass because it is
proven; NLU refines only what the planner could not resolve.
"""

import re

from ai.intent import UNKNOWN as PLANNER_UNKNOWN
from core.intelligence.intent import PLANNER_TO_INTENT, Intent, IntentType

# ==============================================
# SIGNAL GROUPS (synonyms per intent)
# ==============================================

OPEN_SIGNALS = {"open", "launch", "start", "run", "bring", "load",
                "get", "show", "fire", "boot"}

DESIRE_SIGNALS = {"want", "need", "like", "love"}

SEARCH_SIGNALS = {"search", "look", "find", "google", "browse", "query"}

SITE_SIGNALS = {"open", "go", "visit", "navigate", "take", "bring",
                "load", "browse"}

TIME_SIGNALS = {"time", "clock", "hour"}

DATE_SIGNALS = {"date", "day", "today", "tomorrow", "yesterday",
                "week", "month", "year"}

SYSTEM_SIGNALS = {"ram", "memory", "cpu", "processor", "battery",
                  "disk", "storage", "operating", "running"}

FILE_SIGNALS = {"file", "files", "folder", "read", "list", "create",
                "write", "find", "search", "delete"}

# ==============================================
# WINDOWS AWARENESS SIGNALS (Phase 7)
# ==============================================

CPU_SIGNALS = {"cpu", "processor", "load", "busy", "usage"}

MEMORY_SIGNALS = {"ram", "memory"}

STORAGE_SIGNALS = {"storage", "space", "drives", "drive", "disk"}

BATTERY_SIGNALS = {"battery", "charging", "charge", "charged"}

NETWORK_SIGNALS = {"internet", "network", "wifi", "wi-fi", "online",
                   "connected", "connection"}

STATUS_SIGNALS = {"doing", "status", "healthy", "condition"}

CLOSE_SIGNALS = {"close", "quit", "shut", "kill", "terminate"}

RUNNING_SIGNALS = {"running", "launched", "active", "open"}

INSTALLED_SIGNALS = {"installed"}

NAV_SIGNALS = {"go", "navigate", "take", "show", "open"}

FIND_SIGNALS = {"find", "locate", "search"}

# File categories: what the user says -> the extensions that match.
FILE_TYPES = {
    "pdf": [".pdf"],
    "doc": [".doc", ".docx"],
    "docx": [".docx"],
    "word": [".doc", ".docx"],
    "xls": [".xls", ".xlsx"],
    "xlsx": [".xlsx"],
    "excel": [".xls", ".xlsx"],
    "ppt": [".ppt", ".pptx"],
    "pptx": [".pptx"],
    "powerpoint": [".ppt", ".pptx"],
    "txt": [".txt"],
    "text": [".txt"],
    "python": [".py"],
    "py": [".py"],
    "java": [".java"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".hpp"],
    "c++": [".cpp", ".cc", ".hpp"],
    "php": [".php"],
    "html": [".html", ".htm"],
    "css": [".css"],
    "js": [".js"],
    "json": [".json"],
    "csv": [".csv"],
    "md": [".md"],
    "markdown": [".md"],
    "zip": [".zip"],
    "exe": [".exe"],
    "mp4": [".mp4"],
    "jpg": [".jpg", ".jpeg"],
    "jpeg": [".jpg", ".jpeg"],
    "png": [".png"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "photo": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "photos": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "picture": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "pictures": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
    "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "movie": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "music": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "song": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "songs": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "audio": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
}

# Folder names: what the user says -> canonical location name.
LOCATION_ALIASES = {
    "downloads": "downloads",
    "download": "downloads",
    "downloads folder": "downloads",
    "desktop": "desktop",
    "documents": "documents",
    "document": "documents",
    "pictures": "pictures",
    "photos": "pictures",
    "photo": "pictures",
    "videos": "videos",
    "video": "videos",
    "music": "music",
    "home": "home",
    "astra project": "astra",
    "astra": "astra",
    "project": "astra",
    "this project": "astra",
    "this folder": "__here__",
    "this directory": "__here__",
    "here": "__here__",
    "current folder": "__here__",
}

# "downloaded yesterday" -> Downloads, modified within one day.
DOWNLOAD_HINTS = {"downloaded", "download"}

DRIVE_PATTERN = re.compile(r"\b([a-z])\s*(?:drive|:)\b")

DATE_RANGE_WORDS = {
    "yesterday": 1,
    "today": 0,
    "last week": 7,
    "this week": None,
    "this month": None,
}

CLOSE_PRONOUN = re.compile(
    r"^(?:please\s+)?(?:close|quit|kill|shut\s+down|terminate)\s+"
    r"(it|that|this)$"
)

FOLDER_NAV = re.compile(
    r"^(?:please\s+)?(?:take me to|go to|navigate to|show me|"
    r"open up|open)\s+(?:the\s+|my\s+)?"
    r"(downloads|download|desktop|documents|document|pictures|"
    r"photos|videos|video|music|home|astra project|astra|project)$"
)

CLOSE_ASTRA = re.compile(
    r"^(?:please\s+)?(?:close|quit|shut\s+down|kill)\s+astra$"
)

POLITE_STOP = {
    "could", "can", "would", "will", "do", "does", "did", "you",
    "me", "my", "your", "the", "a", "an", "please", "for", "to",
    "i", "we", "us", "and", "with", "it", "its", "on", "of",
    "want", "need", "like", "up", "out",
}

BIGRAMS = ("open up", "start up", "bring up", "fire up", "look up",
           "look for", "search for", "go to", "take me", "show me",
           "get me", "find me", "bring me", "can you", "could you")

FILE_PRONOUN = re.compile(
    r"^(?:please\s+)?(delete|remove|erase|move|rename|open|read|"
    r"show|list|close)\s+(?:it|that|this|those|them|the)"
    r"(?:\s+(?:folder|file|directory))?$"
)

BARE_SEARCH = re.compile(
    r"^(?:please\s+)?(?:can\s+you\s+|could\s+you\s+)?"
    r"(?:search|look up)\s+(?:the\s+)?(?:web|internet)$"
)

KNOWN_SITES = ("youtube", "google", "gmail", "chatgpt", "github")

DOMAIN_PATTERN = re.compile(r"[a-z0-9-]+(\.[a-z0-9-]+)+")

SEARCH_MARKERS = re.compile(
    r"\b(?:search|look up|look for|find|google|query)"
    r"\s+(?:for\s+)?(?:the\s+|a\s+|an\s+)?(.+)$"
)

QUERY_WORDS = re.compile(r"\b(?:about|for|on)\s+(.+)$")


class NLU:

    def __init__(self, discovery=None, brain=None):

        self.discovery = discovery

        # The deterministic planner is the first pass.
        self.brain = brain

    # ==============================================
    # PRECHECKS (run before the brain)
    # ==============================================

    def precheck(self, raw, context):
        """Intercept utterances the brain must never see.

        Pronoun opens ("open it"), pronoun file actions ("delete
        that folder") and date ellipses ("and tomorrow?") are
        resolved here so the brain is never asked to guess.
        """

        if not raw:
            return None

        pronoun = self._pronoun_open(raw)

        if pronoun is not None:
            return pronoun

        date_ellipsis = self._date_ellipsis(raw, context)

        if date_ellipsis is not None:
            return date_ellipsis

        # "search the web" alone asks for a topic, never searches
        # the literal phrase "the web".
        if BARE_SEARCH.fullmatch(raw.lower().strip("?!.,;: ")):

            return Intent(
                name=IntentType.SEARCH_WEB,
                confidence=0.65,
                entities={},
                original_text=raw,
            )

        # "close it" after "Is Chrome running?" refers to the last
        # mentioned application, not to a file.
        if (
            CLOSE_PRONOUN.fullmatch(raw.lower().strip("?!.,;: "))
            and context is not None
            and context.last_entity
            and context.last_entity not in set(LOCATION_ALIASES.values())
        ):

            return Intent(
                name=IntentType.CLOSE_APPLICATION,
                confidence=0.85,
                entities={"application": context.last_entity},
                original_text=raw,
            )

        # "close astra" means exit the assistant, never anything else.
        if CLOSE_ASTRA.fullmatch(raw.lower().strip("?!.,;: ")):

            return Intent(
                name=IntentType.EXIT,
                confidence=0.95,
                entities={},
                original_text=raw,
            )

        # "open the downloads folder" and friends are navigated
        # before the brain ever sees them.
        folder = FOLDER_NAV.fullmatch(raw.lower().strip("?!.,;: "))

        if folder is not None:

            return Intent(
                name=IntentType.FOLDER_OPERATION,
                confidence=0.95,
                entities={"action": "open",
                          "location": LOCATION_ALIASES[folder.group(1)]},
                original_text=raw,
            )

        file_pronoun = self._file_pronoun(raw)

        if file_pronoun is not None:
            return file_pronoun

        return None

    @staticmethod
    def _file_pronoun(raw):

        match = FILE_PRONOUN.match(raw.lower().strip("?!.,;: "))

        if not match:
            return None

        return Intent(
            name=IntentType.FILE_OPERATION,
            confidence=0.7,
            entities={"action": match.group(1)},
            original_text=raw,
        )

    # ==============================================
    # MAIN ENTRY
    # ==============================================

    def resolve(self, text, context, skip_planner=False):
        """Return an Intent for the utterance, using conversation
        context to resolve ellipses."""

        raw = (text or "").strip()

        if not raw:
            return Intent(name=IntentType.UNKNOWN, original_text=text)

        # 1. Pre-checks: pronoun opens, pronoun file actions and
        #    date ellipses are resolved before anything else.
        pre = self.precheck(raw, context)

        if pre is not None:
            return pre

        # 2. Deterministic planner first (proven, precise).
        if not skip_planner and self.brain is not None:

            planned = self.brain.process(raw)

            if planned.type != PLANNER_UNKNOWN:

                mapped = self._map_planner(planned)

                if mapped.name != IntentType.UNKNOWN:
                    return mapped

        # 3. Semantic signals for everything else.
        semantic = self._semantic(raw, context)

        if semantic is not None:
            return semantic

        return Intent(name=IntentType.UNKNOWN, original_text=text)

    # ==============================================
    # PLANNER MAPPING
    # ==============================================

    def _map_planner(self, planned):

        name = PLANNER_TO_INTENT.get(planned.type, IntentType.UNKNOWN)

        entities = {}

        if planned.target:
            entities["target"] = planned.target

        for key, value in (planned.parameters or {}).items():
            entities[key] = value

        if name == IntentType.SYSTEM_INFORMATION:

            topic = entities.get("topic") or planned.action or ""

            if topic == "get_time" or planned.action == "get_time":
                name = IntentType.GET_TIME
            elif topic == "get_date" or planned.action == "get_date":
                name = IntentType.GET_DATE
            else:
                entities["topic"] = topic

        if name == IntentType.OPEN_WEBSITE and planned.action == "search_web":
            name = IntentType.SEARCH_WEB

        return Intent(
            name=name,
            confidence=planned.confidence,
            entities=entities,
            original_text=planned.raw_text,
            action=planned.action,
            tool_call=planned.tool_call,
            response=planned.response,
        )

    # ==============================================
    # SEMANTIC RESOLUTION
    # ==============================================

    def _semantic(self, raw, context):

        lower = raw.lower()
        tokens = re.findall(r"[a-z0-9]+", lower)

        bigram_hits = {bigram for bigram in BIGRAMS if bigram in lower}

        candidates = []

        # ----- windows awareness (Phase 7) -----

        windows, file_search = self._windows_candidates(
            lower, tokens, bigram_hits, context
        )

        candidates.extend(windows)

        # ----- status groups (computed first: they override the
        # generic no-entity open candidate below) -----

        cpu_hits = self._signal_hits(tokens, CPU_SIGNALS, bigram_hits)
        memory_hits = self._signal_hits(tokens, MEMORY_SIGNALS,
                                        bigram_hits)
        storage_hits = self._signal_hits(tokens, STORAGE_SIGNALS,
                                         bigram_hits)
        battery_hits = self._signal_hits(tokens, BATTERY_SIGNALS,
                                         bigram_hits)
        network_hits = self._signal_hits(tokens, NETWORK_SIGNALS,
                                         bigram_hits)
        status_hits = self._signal_hits(tokens, STATUS_SIGNALS,
                                        bigram_hits)

        status_any = any((
            cpu_hits, memory_hits, storage_hits, battery_hits,
            network_hits, status_hits,
        ))

        # ----- open / website -----

        open_hits = self._signal_hits(tokens, OPEN_SIGNALS, bigram_hits)
        site_hits = self._signal_hits(tokens, SITE_SIGNALS, bigram_hits)
        desire_hits = self._signal_hits(tokens, DESIRE_SIGNALS, bigram_hits)

        site_entity = self._extract_site(lower)

        app = None

        if not site_entity:
            app = self._extract_app(tokens, open_hits)

        if site_entity and (site_hits or open_hits or desire_hits):

            candidates.append(
                Intent(
                    name=IntentType.OPEN_WEBSITE,
                    confidence=self._confidence(
                        max(open_hits, site_hits, desire_hits),
                        entity=True,
                    ),
                    entities={"site": site_entity},
                    original_text=raw,
                )
            )

        if (open_hits or desire_hits) and not site_entity:

            if app is not None:

                candidates.append(
                    Intent(
                        name=IntentType.OPEN_APPLICATION,
                        confidence=self._confidence(
                            max(open_hits, desire_hits), entity=True
                        ),
                        entities={"application": app},
                        original_text=raw,
                    )
                )

            elif open_hits and not status_any:

                candidates.append(
                    Intent(
                        name=IntentType.OPEN_APPLICATION,
                        confidence=self._confidence(open_hits, entity=False),
                        entities={},
                        original_text=raw,
                    )
                )

        # ----- search -----

        search_hits = self._signal_hits(tokens, SEARCH_SIGNALS, bigram_hits)

        if search_hits and not file_search:

            query = self._extract_query(lower)

            candidates.append(
                Intent(
                    name=IntentType.SEARCH_WEB,
                    confidence=self._confidence(
                        search_hits, entity=bool(query)
                    ),
                    entities={"query": query} if query else {},
                    original_text=raw,
                )
            )

        # ----- time / date -----

        time_hits = self._signal_hits(tokens, TIME_SIGNALS, bigram_hits)
        date_hits = self._signal_hits(tokens, DATE_SIGNALS, bigram_hits)

        if (
            date_hits
            and not time_hits
            and any(word in tokens for word in ("what", "tell", "current"))
        ):

            candidates.append(
                Intent(
                    name=IntentType.GET_DATE,
                    confidence=self._confidence(date_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )

        if time_hits and not date_hits:

            candidates.append(
                Intent(
                    name=IntentType.GET_TIME,
                    confidence=self._confidence(time_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )
        # ----- cpu / memory / storage / battery / network -----

        if cpu_hits:

            candidates.append(
                Intent(
                    name=IntentType.CPU_STATUS,
                    confidence=self._status_confidence(cpu_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )

        if memory_hits:

            candidates.append(
                Intent(
                    name=IntentType.MEMORY_STATUS,
                    confidence=self._status_confidence(memory_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )

        if storage_hits:

            entities = {}

            drive = self._extract_drive(lower)

            if drive is not None:
                entities["drive"] = drive

            candidates.append(
                Intent(
                    name=IntentType.STORAGE_STATUS,
                    confidence=self._status_confidence(
                        storage_hits, entity=bool(entities)),
                    entities=entities,
                    original_text=raw,
                )
            )

        if battery_hits:

            candidates.append(
                Intent(
                    name=IntentType.BATTERY_STATUS,
                    confidence=self._status_confidence(battery_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )

        if network_hits:

            kind = "internet"

            if "wifi" in tokens or "wi-fi" in lower:
                kind = "wifi"
            elif "ip" in tokens:
                kind = "ip"

            candidates.append(
                Intent(
                    name=IntentType.NETWORK_STATUS,
                    confidence=self._status_confidence(network_hits, entity=False),
                    entities={"kind": kind},
                    original_text=raw,
                )
            )

        if status_hits and "you" not in tokens:

            candidates.append(
                Intent(
                    name=IntentType.COMPUTER_STATUS,
                    confidence=self._status_confidence(status_hits, entity=False),
                    entities={},
                    original_text=raw,
                )
            )

        if not candidates:
            return None

        best = max(candidates, key=lambda item: item.confidence)

        if best.confidence < 0.55:
            return None

        return best

    # ==============================================
    # WINDOWS AWARENESS CANDIDATES (Phase 7)
    # ==============================================

    def _windows_candidates(self, lower, tokens, bigram_hits, context):

        candidates = []

        # FILE_SEARCH suppresses the generic web-search candidate.
        file_search = False

        # ----- close application -----

        close_hits = self._signal_hits(tokens, CLOSE_SIGNALS, bigram_hits)

        if close_hits:

            app = self._extract_app(tokens, close_hits,
                                    extra_stop=CLOSE_SIGNALS)

            candidates.append(
                Intent(
                    name=IntentType.CLOSE_APPLICATION,
                    confidence=self._confidence(close_hits,
                                                entity=app is not None),
                    entities={"application": app} if app else {},
                    original_text=lower,
                )
            )

        # ----- "is X running?" / "what is running?" -----

        running_app = self._extract_question_target(lower, "running")

        if running_app is not None:

            candidates.append(
                Intent(
                    name=IntentType.RUNNING_APPLICATIONS,
                    confidence=0.9,
                    entities={"application": running_app},
                    original_text=lower,
                )
            )

        elif (
            re.match(
                r"what(?:\'s| is)?\s+(?:(?:apps?|applications?|"
                r"programs?|software)\s+(?:are\s+)?(?:currently\s+)?)?"
                r"(?:running|open)\b",
                lower.strip("?!.,;: "),
            )
            and "open source" not in lower
            and not re.search(r"\b(running\s+low|low\s+on|out\s+of)\b",
                              lower)
        ):

            candidates.append(
                Intent(
                    name=IntentType.RUNNING_APPLICATIONS,
                    confidence=0.85,
                    entities={},
                    original_text=lower,
                )
            )

        # ----- "is X installed?" / "do I have X?" -----

        installed_app = self._extract_question_target(lower, "installed")

        if installed_app is not None:

            candidates.append(
                Intent(
                    name=IntentType.APPLICATION_SEARCH,
                    confidence=0.9,
                    entities={"application": installed_app},
                    original_text=lower,
                )
            )

        else:

            have_match = re.fullmatch(
                r"do\s+i\s+have\s+(?:a\s+|an\s+|any\s+)?(.+)"
                r"|have\s+(?:you\s+)?got\s+(?:a\s+|an\s+|any\s+)?(.+)",
                lower.strip("?!.,;: "),
            )

            if have_match is not None:

                have_app = self._extract_app(
                    tokens, (), extra_stop=("do", "i", "have", "got",
                                            "a", "an", "any")
                )

                if have_app is not None:

                    candidates.append(
                        Intent(
                            name=IntentType.APPLICATION_SEARCH,
                            confidence=0.9,
                            entities={"application": have_app},
                            original_text=lower,
                        )
                    )

        # ----- installed applications as a list -----

        if (
            re.search(r"\bwhat\b", lower)
            and re.search(r"\b(application|applications|apps?|programs?|"
                          r"software)\b", lower)
            and re.search(r"\b(installed|have)\b", lower)
        ) or (
            re.search(r"\binstalled\b", lower)
            and re.search(r"\b(apps?|applications?|programs?|software)\b",
                          lower)
        ):

            candidates.append(
                Intent(
                    name=IntentType.APPLICATION_SEARCH,
                    confidence=0.85,
                    entities={},
                    original_text=lower,
                )
            )

        # ----- system specifications / OS -----

        if (
            re.search(r"\b(specifications|specs)\b", lower)
            or (
                re.search(r"\bwhat\b", lower)
                and re.search(r"\b(computer|pc|laptop|machine|system)\b",
                              lower)
                and re.search(r"\b(specs?|specifications|have|is)\b",
                              lower)
            )
        ):

            candidates.append(
                Intent(
                    name=IntentType.SYSTEM_INFORMATION,
                    confidence=0.9,
                    entities={"topic": "specs"},
                    original_text=lower,
                )
            )

        if re.search(r"\boperating\s+system\b|\bwindows\s+version\b",
                     lower):

            candidates.append(
                Intent(
                    name=IntentType.SYSTEM_INFORMATION,
                    confidence=0.9,
                    entities={"topic": "os"},
                    original_text=lower,
                )
            )

        # ----- computer status -----

        if re.search(
            r"\bhow\b.*\b(computer|pc|laptop|machine|system)\b.*"
            r"\b(doing|status)\b",
            lower,
        ):

            candidates.append(
                Intent(
                    name=IntentType.COMPUTER_STATUS,
                    confidence=0.9,
                    entities={},
                    original_text=lower,
                )
            )

        # ----- process information -----

        if (
            re.search(r"\bwhat\b.*\b(using|use|consuming|taking)\b.*"
                      r"\b(most|top)\b", lower)
            or re.search(r"\b(which|what)\b.*\b(process|processes|"
                         r"program|programs)\b.*\b(ram|memory|cpu)\b",
                         lower)
        ):

            kind = "cpu" if (
                "cpu" in tokens or "processor" in tokens
            ) else "memory"

            candidates.append(
                Intent(
                    name=IntentType.PROCESS_INFORMATION,
                    confidence=0.85,
                    entities={"kind": kind},
                    original_text=lower,
                )
            )

        # ----- network -----

        wifi_mention = bool(re.search(r"\b(wifi|wi-fi)\b", lower))

        if wifi_mention and re.search(r"\bwhat\b", lower):

            candidates.append(
                Intent(
                    name=IntentType.NETWORK_STATUS,
                    confidence=0.9,
                    entities={"kind": "wifi"},
                    original_text=lower,
                )
            )

        if (
            not wifi_mention
            and re.search(
                r"\b(connected\s+to\s+the\s+internet|internet\s+"
                r"connection|am\s+i\s+connected|are\s+we\s+connected|"
                r"is\s+the\s+network|online)\b",
                lower,
            )
        ):

            candidates.append(
                Intent(
                    name=IntentType.NETWORK_STATUS,
                    confidence=0.9,
                    entities={"kind": "internet"},
                    original_text=lower,
                )
            )

        if re.search(r"\b(my\s+)?ip\s+address\b", lower):

            candidates.append(
                Intent(
                    name=IntentType.NETWORK_STATUS,
                    confidence=0.9,
                    entities={"kind": "ip"},
                    original_text=lower,
                )
            )

        # ----- file search -----

        find_hits = self._signal_hits(tokens, FIND_SIGNALS, bigram_hits)

        file_type = self._extract_file_type(lower)

        location = self._extract_location(lower, context)

        date_days = self._extract_date_days(lower)

        on_web = re.search(r"\b(web|internet|online)\b", lower) is not None

        if (
            (find_hits or lower.startswith("where"))
            and not on_web
            and (
                file_type is not None
                or location is not None
                or date_days is not None
                or re.search(r"\b(containing|the\s+word|the\s+phrase)\b",
                             lower)
            )
        ):

            entities = {
                "query": self._extract_file_query(
                    lower, file_type, location
                ),
                "location": None,
                "path": None,
                "modified_within_days": date_days,
            }

            if file_type is not None:
                entities["file_type"] = file_type[0]
                entities["extensions"] = file_type[1]

            if location is not None:
                entities["location"] = location[0]
                entities["path"] = location[1]

            candidates.append(
                Intent(
                    name=IntentType.FILE_SEARCH,
                    confidence=0.9,
                    entities=entities,
                    original_text=lower,
                )
            )

            file_search = True

        # ----- folder operation (open / list) -----

        if location is not None:

            if re.search(r"\b(open|go|navigate|take|show)\b", lower):

                candidates.append(
                    Intent(
                        name=IntentType.FOLDER_OPERATION,
                        confidence=0.9,
                        entities={
                            "action": "open",
                            "location": location[0],
                            "path": location[1],
                        },
                        original_text=lower,
                    )
                )

            elif re.search(r"\b(list|in|inside|what|contents)\b", lower):

                candidates.append(
                    Intent(
                        name=IntentType.FOLDER_OPERATION,
                        confidence=0.85,
                        entities={
                            "action": "list",
                            "location": location[0],
                            "path": location[1],
                        },
                        original_text=lower,
                    )
                )

        return candidates, file_search

    # ==============================================
    # ENTITY EXTRACTION (Phase 7)
    # ==============================================

    @staticmethod
    def _extract_question_target(lower, verb):
        """Target of "is X running?" / "is X installed?", or None."""

        match = re.fullmatch(
            rf"is\s+(.+?)\s+{verb}\??",
            lower.strip("?!.,;: "),
        )

        if not match:
            return None

        target = match.group(1).strip()

        if not target or target in ("the internet", "the network", "my pc"):
            return None

        return target

    @staticmethod
    def _extract_file_type(lower):
        """(category, extensions) for a file-type word, or None."""

        for category in sorted(FILE_TYPES, key=len, reverse=True):

            if re.search(rf"\b{re.escape(category)}\b", lower):
                return (category, FILE_TYPES[category])

        return None

    @staticmethod
    def _extract_location(lower, context):
        """(canonical name, path) for a folder mention, or None."""

        for alias in sorted(LOCATION_ALIASES, key=len, reverse=True):

            if re.search(rf"\b{re.escape(alias)}\b", lower):

                name = LOCATION_ALIASES[alias]

                if name == "__here__":
                    path = None

                    if context is not None:
                        path = context.current_location

                    return ("__here__", path)

                return (name, None)

        for hint in DOWNLOAD_HINTS:

            if re.search(rf"\b{hint}\b", lower):
                return ("downloads", None)

        return None

    @staticmethod
    def _extract_drive(lower):
        """Drive letter from "c drive" / "c:", or None."""

        match = DRIVE_PATTERN.search(lower)

        if match:
            return match.group(1).upper()

        return None

    @staticmethod
    def _extract_date_days(lower):
        """Days-ago bound from "yesterday" etc., or None."""

        import datetime

        if re.search(r"\byesterday\b", lower):
            return 1

        if re.search(r"\btoday\b", lower):
            return 0

        if re.search(r"\blast\s+week\b", lower):
            return 7

        if re.search(r"\bthis\s+week\b", lower):
            return datetime.datetime.now(tz=datetime.timezone.utc).date().weekday()

        if re.search(r"\bthis\s+month\b", lower):
            return max(datetime.datetime.now(tz=datetime.timezone.utc).date().day - 1, 1)

        return None

    @staticmethod
    def _extract_file_query(lower, file_type, location):
        """Residual words after stripping type / location / verbs."""

        query = lower

        if file_type is not None:
            query = query.replace(file_type[0], " ")

        if location is not None:

            for alias in sorted(LOCATION_ALIASES, key=len, reverse=True):

                if LOCATION_ALIASES[alias] == location[0]:
                    query = re.sub(
                        rf"\b{re.escape(alias)}\b", " ", query
                    )

        for word in ("downloaded", "download", "yesterday", "today",
                     "this week", "last week", "this month"):
            query = query.replace(word, " ")

        query = re.sub(
            r"\b(?:find|locate|search|for|me|my|the|a|an|is|are|was|"
            r"were|do|does|did|please|can|could|you|have|i|we|in|on|"
            r"at|of|that|this|it|files?|folder|word|phrase)\b",
            " ",
            query,
        )

        query = re.sub(r"\s+", " ", query).strip().strip("?!.,;: ")

        return query

    # ==============================================
    # HELPERS
    # ==============================================

    @staticmethod
    def _signal_hits(tokens, signals, bigram_hits):

        count = 0

        for token in tokens:

            if token in signals:
                count += 1

        for bigram in bigram_hits:

            words = bigram.split()

            if any(word in signals for word in words):
                count += 1

        return count

    @staticmethod
    def _confidence(hits, entity):

        score = 0.45 + 0.2 * min(hits, 2)

        if entity:
            score += 0.15

        if entity and hits >= 2:
            score += 0.1

        return round(min(score, 0.95), 2)

    @staticmethod
    def _status_confidence(hits, entity):
        """Status intents sit above the generic open/search groups
        (0.65) but below the precise patterns (0.9)."""

        score = 0.75 + 0.05 * min(hits - 1, 2)

        if entity:
            score += 0.1

        return round(min(score, 0.85), 2)

    def _extract_app(self, tokens, open_hits, extra_stop=()):

        if self.discovery is None:
            return None

        remaining = [
            token for token in tokens
            if token not in POLITE_STOP
            and token not in OPEN_SIGNALS
            and token not in SEARCH_SIGNALS
            and token not in extra_stop
        ]

        for n in range(min(len(remaining), 4), 0, -1):

            for start in range(len(remaining) - n + 1):

                candidate = " ".join(remaining[start:start + n])

                info = self.discovery.find(candidate)

                if info is not None:
                    return info["name"]

        return None

    @staticmethod
    def _extract_site(lower):

        for site in KNOWN_SITES:

            if re.search(rf"\b{site}\b", lower):
                return site

        match = re.search(r"\b[a-z0-9-]+(?:\.[a-z0-9-]+)+\b", lower)

        if match:
            return match.group(0)

        return None

    @staticmethod
    def _extract_query(lower):

        match = SEARCH_MARKERS.search(lower)

        if match:

            query = match.group(1).strip().strip("?!")

            if query and query.lower() not in ("web", "internet"):
                return query

        return None

    @staticmethod
    def _pronoun_open(raw):

        lower = raw.lower().strip("?!.,;: ")

        if re.fullmatch(
            r"(?:please\s+)?(?:open|launch|start|run|open up|start up|"
            r"bring up|fire up)\s+(?:it|that|this|those|them)"
            r"(?:\s+for\s+me)?",
            lower,
        ):
            return Intent(
                name=IntentType.OPEN_APPLICATION,
                confidence=0.7,
                entities={},
                original_text=raw,
            )

        return None

    @staticmethod
    def _date_ellipsis(raw, context):

        lower = raw.lower().strip("?!.,;: ")

        match = re.fullmatch(
            r"(?:and\s+)?(?:what\s+about\s+|how\s+about\s+)?"
            r"(tomorrow|yesterday|today|next\s+week|next\s+month|"
            r"next\s+year)",
            lower,
        )

        if not match:
            return None

        if context is None or context.topic not in (
            IntentType.GET_TIME, IntentType.GET_DATE
        ):
            return None

        return Intent(
            name=IntentType.GET_DATE,
            confidence=0.9,
            entities={"day": match.group(1)},
            original_text=raw,
        )