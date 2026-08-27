"""
Central configuration for Astra.

Values come from environment variables first, then from .env files,
then from defaults.  No API keys are hard-coded anywhere.
"""

import os


def _project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = _project_root()


def _load_dotenv(path):
    """Load KEY=VALUE pairs into os.environ (never overwriting).

    Standard .env semantics, implemented with the standard library.
    """

    if not path or not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as file:

        for line in file:

            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, _, value = line.partition("=")

            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
_load_dotenv(os.path.join(PROJECT_ROOT, "config", ".env"))

# A future dedicated Astra partition can be configured here.
# Large items (models, memory, logs, cache) can then live there.
ASTRA_DATA_DIR = os.environ.get(
    "ASTRA_DATA_DIR",
    PROJECT_ROOT
)

_load_dotenv(os.path.join(ASTRA_DATA_DIR, ".env"))

# ==============================================
# AI PROVIDER
# ==============================================

# "none" (default), "ollama", "local", or "cloud". Anything else is "none".
AI_PROVIDER = os.environ.get("AI_PROVIDER", "none").strip().lower()

AI_MODEL = os.environ.get("AI_MODEL", "").strip()

# Optional cloud credentials.  Never store these in the repository.
ASTRA_API_KEY = os.environ.get("ASTRA_API_KEY", "").strip()
ASTRA_API_BASE = os.environ.get(
    "ASTRA_API_BASE",
    "https://api.openai.com/v1"
).strip().rstrip("/")

ASTRA_OLLAMA_BASE = os.environ.get(
    "ASTRA_OLLAMA_BASE",
    "http://127.0.0.1:11434"
).strip().rstrip("/")

ASTRA_OLLAMA_TIMEOUT = float(
    os.environ.get("ASTRA_OLLAMA_TIMEOUT", "30")
)

# ==============================================
# VOICE PIPELINE
# ==============================================

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")

WAKE_WORD_THRESHOLD = float(
    os.environ.get("WAKE_WORD_THRESHOLD", "0.7")
)

# Wake-word model filename. The current OpenWakeWord package bundled with
# Astra provides alexa_v0.1.onnx. This is configurable so a future
# custom "Hey Astra" model can be dropped in without changing code.
WAKE_WORD_MODEL = os.environ.get(
    "WAKE_WORD_MODEL", "alexa_v0.1.onnx"
).strip()

VOICE_RATE = int(os.environ.get("VOICE_RATE", "175"))

# ==============================================
# MEMORY
# ==============================================

MEMORY_ENABLED = os.environ.get(
    "MEMORY_ENABLED", "true"
).strip().lower() in ("1", "true", "yes", "on")

MEMORY_DB_PATH = os.path.join(
    ASTRA_DATA_DIR,
    "memory",
    "astra.db"
)

# ==============================================
# CONVERSATION (Phase 6)
# ==============================================

# Seconds of silence after the wake word before Astra goes back
# to wake-word listening.  The user does not need to repeat the
# wake word while an active conversation is happening.
CONVERSATION_TIMEOUT = float(
    os.environ.get("ASTRA_CONVERSATION_TIMEOUT", "10")
)

# Bounded conversation memory.
MAX_CONTEXT_MESSAGES = int(
    os.environ.get("ASTRA_MAX_CONTEXT_MESSAGES", "8")
)

MAX_CONTEXT_TOKENS = int(
    os.environ.get("ASTRA_MAX_CONTEXT_TOKENS", "400")
)

# ==============================================
# APPLICATION DISCOVERY (Phase 6)
# ==============================================

# Cache of discovered applications.  The disk is scanned at most
# once per cache age window, never on every command.
APP_CACHE_PATH = os.path.join(
    ASTRA_DATA_DIR,
    "data",
    "apps_cache.json"
)

APP_CACHE_MAX_AGE_DAYS = int(
    os.environ.get("ASTRA_APP_CACHE_MAX_AGE_DAYS", "7")
)

# ==============================================
# WINDOWS AWARENESS (Phase 7)
# ==============================================

# Astra's own version, reported in system specifications.
ASTRA_VERSION = "0.11.0"

# Project directory override (normally the source tree root).
ASTRA_PROJECT_DIR = os.environ.get(
    "ASTRA_PROJECT_DIR", PROJECT_ROOT
)

# Approved locations for filesystem operations.  Astra only reads
# and searches inside these roots; anything else is denied.
ALLOWED_DIRECTORIES = {
    "desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
    "documents": os.path.join(os.path.expanduser("~"), "Documents"),
    "downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
    "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
    "videos": os.path.join(os.path.expanduser("~"), "Videos"),
    "music": os.path.join(os.path.expanduser("~"), "Music"),
    "home": os.path.expanduser("~"),
    "astra": ASTRA_PROJECT_DIR,
}

# Maximum number of file-search results to report in one response.
SEARCH_RESULT_LIMIT = int(
    os.environ.get("ASTRA_SEARCH_RESULT_LIMIT", "5")
)

# Maximum directory depth walked during a file search.
MAX_FILE_SEARCH_DEPTH = int(
    os.environ.get("ASTRA_MAX_FILE_SEARCH_DEPTH", "5")
)

# ==============================================
# FLOATING UI (Phase 11B)
# ==============================================

# Seconds after Astra finishes speaking before the overlay fades out.
UI_AUTO_HIDE_SECONDS = float(
    os.environ.get("ASTRA_UI_AUTO_HIDE_SECONDS", "2.5")
)

# Overlay fade-in and fade-out durations.
UI_FADE_IN_MS = int(
    os.environ.get("ASTRA_UI_FADE_IN_MS", "250")
)

UI_FADE_OUT_MS = int(
    os.environ.get("ASTRA_UI_FADE_OUT_MS", "300")
)

# Orb animation refresh rate (frames per second).
UI_ANIM_FPS = int(
    os.environ.get("ASTRA_UI_ANIM_FPS", "30")
)

# ==============================================
# LOGGING
# ==============================================

LOG_LEVEL = os.environ.get(
    "LOG_LEVEL", "INFO"
).strip().upper()

LOG_DIR = os.path.join(ASTRA_DATA_DIR, "logs")
