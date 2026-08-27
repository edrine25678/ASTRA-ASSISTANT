"""
Command normalization and intent detection for Astra.

Flow:

    Whisper text
        -> normalize_text()
        -> detect_intent()
        -> action

Everything here is deterministic and fully local.  The layer tolerates
natural command variations ("please open chrome for me") and safe,
well-known Whisper misrecognitions ("open not bad" -> notepad).

Interpretations with low confidence are rejected: detect_intent()
returns None in that case, and the caller falls back to the standard
"I don't know how to do that yet." response.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher


OPEN_APPLICATION = "OPEN_APPLICATION"

OPEN_VERBS = ("open", "launch", "start", "run", "opening")

VERB_PHRASES = {
    "open up": "open",
    "bring up": "open",
}

FILLER_PHRASES = (
    "could you",
    "can you",
    "would you",
    "will you",
    "do you mind",
    "do you",
    "for me",
)

FILLER_TOKENS = (
    "please",
    "kindly",
    "just",
    "maybe",
    "the",
    "a",
    "an",
    "my",
)

APP_ALIASES = {
    "chrome": ("chrome", "google chrome", "chrome browser", "browser"),
    "notepad": ("notepad", "not bad", "note pad"),
    "calculator": ("calculator", "calc"),
    "file explorer": (
        "file explorer",
        "file manager",
        "files explorer",
        "explorer",
    ),
    "vs code": ("vs code", "vscode", "visual studio code", "code editor"),
    "google": ("google", "google search"),
    "youtube": (
        "youtube",
        "your tube",
        "you tube",
        "utube",
        "youtube dot com",
        "youtube com",
    ),
    "gmail": ("gmail", "g mail", "gmail dot com", "gmail com"),
    "chatgpt": ("chatgpt", "chat gpt", "chat gbt"),
}

# Fuzzy matches at or above this score are accepted.  Below this
# the interpretation is considered unsafe.
FUZZY_THRESHOLD = 0.90


@dataclass
class Intent:
    name: str
    target: str
    confidence: float
    raw_text: str = ""


# ==============================================
# NORMALIZATION
# ==============================================

def canonical(text):
    """Collapse whitespace and strip the edges."""
    return re.sub(r"\s+", " ", text).strip()


def _strip_fillers(text):

    t = text

    for phrase, replacement in VERB_PHRASES.items():
        t = re.sub(r"\b" + re.escape(phrase) + r"\b", replacement, t)

    for phrase in FILLER_PHRASES:
        t = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", t)

    for token in FILLER_TOKENS:
        t = re.sub(r"\b" + re.escape(token) + r"\b", " ", t)

    # A trailing "app" is never meaningful.
    t = re.sub(r"\s+app$", "", t)

    return canonical(t)


def normalize_text(text):
    """Prepare raw Whisper text for intent detection.

    Lowercases, removes punctuation and filler words, and normalizes
    whitespace.

    Examples:
        "Please open the Chrome for me" -> "open chrome"
        "Could you open Chrome?"        -> "open chrome"
    """

    t = text.lower()

    t = re.sub(r"[^a-z0-9\s]+", " ", t)

    t = re.sub(r"^(hey\s+)?(astra\s+)?", "", t)

    return _strip_fillers(t)


# ==============================================
# INTENT DETECTION
# ==============================================

def _extract_open_verb(text):
    """Remove the first open-verb and report whether one existed."""

    words = text.split()

    for index, word in enumerate(words):

        if word in OPEN_VERBS:

            remaining = words[:index] + words[index + 1:]

            return True, canonical(" ".join(remaining))

    return False, canonical(text)


def _exact_alias_match(target):

    compact_target = target.replace(" ", "")

    for app, aliases in APP_ALIASES.items():

        for alias in aliases:

            if (
                target == alias
                or compact_target == alias.replace(" ", "")
            ):

                return app

    return None


def _fuzzy_alias_match(target):

    candidates = {target, target.replace(" ", "")}

    best_app = None
    best_score = 0.0

    for app, aliases in APP_ALIASES.items():

        for alias in aliases:

            references = {alias, alias.replace(" ", "")}

            for candidate in candidates:

                for reference in references:

                    score = SequenceMatcher(
                        None, candidate, reference
                    ).ratio()

                    if score > best_score:
                        best_score = score
                        best_app = app

    if best_score >= FUZZY_THRESHOLD:

        return best_app, best_score

    return None, 0.0


def detect_intent(text):
    """Detect the user's intent from raw Whisper text.

    Returns an Intent, or None when nothing is recognized with
    sufficient confidence.
    """

    if not text:
        return None

    normalized = normalize_text(text)

    if not normalized:
        return None

    # A leading "and" is a whisper artifact
    # ("and file the explorer", "and open chrome").
    and_artifact = normalized.startswith("and ")

    if and_artifact:

        normalized = canonical(normalized[4:])

        if not normalized:
            return None

    verb_found, target = _extract_open_verb(normalized)

    if verb_found and target:

        app = _exact_alias_match(target)

        if app:
            return Intent(OPEN_APPLICATION, app, 1.0, text)

        app, score = _fuzzy_alias_match(target)

        if app:
            return Intent(OPEN_APPLICATION, app, score, text)

        return None

    # No open verb.  Only safe repairs are accepted, and only when
    # the remainder is an exact alias:
    #   "on youtube" -> "open youtube"
    #   "and gmail"  -> "open gmail"
    match = re.match(r"^on\s+(.+)$", target)

    if match:

        app = _exact_alias_match(match.group(1))

        if app:
            return Intent(OPEN_APPLICATION, app, 0.9, text)

    if and_artifact:

        app = _exact_alias_match(target)

        if app:
            return Intent(OPEN_APPLICATION, app, 0.9, text)

    return None
