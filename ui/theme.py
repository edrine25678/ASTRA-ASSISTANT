"""Visual theme for the Astra floating overlay.

Colors and sizes are centralized here so the overlay, orb and tray
stay consistent.  No image assets are used anywhere.
"""

from PySide6.QtGui import QColor

# ==============================================
# COLORS
# ==============================================

BG_TOP = QColor(18, 22, 32, 236)
BG_BOTTOM = QColor(12, 15, 24, 236)
BORDER = QColor(56, 189, 248, 70)
BORDER_DIM = QColor(56, 189, 248, 30)

ACCENT = QColor(34, 211, 238)
ACCENT_SOFT = QColor(34, 211, 238, 120)
ACCENT_DIM = QColor(34, 211, 238, 45)

TEXT = QColor(241, 245, 249)
TEXT_MUTED = QColor(148, 163, 184)
TEXT_DIM = QColor(100, 116, 139)

USER_COLOR = QColor(96, 165, 250)
ASTRA_COLOR = QColor(34, 211, 238)

ERROR_COLOR = QColor(251, 191, 36)

LISTENING_GLOW = QColor(34, 211, 238, 120)
THINKING_GLOW = QColor(56, 189, 248, 110)
SPEAKING_GLOW = QColor(34, 211, 238, 150)
IDLE_GLOW = QColor(34, 211, 238, 60)
ERROR_GLOW = QColor(251, 191, 36, 90)

# ==============================================
# SIZES
# ==============================================

OVERLAY_WIDTH = 380
OVERLAY_COMPACT_HEIGHT = 132
OVERLAY_EXPANDED_HEIGHT = 440
OVERLAY_RADIUS = 18
ORB_SIZE = 64
SCREEN_MARGIN = 28

# ==============================================
# FONTS
# ==============================================

FONT_FAMILY = "Segoe UI"
TITLE_POINT_SIZE = 13
STATUS_POINT_SIZE = 11
TRANSCRIPT_POINT_SIZE = 10
INPUT_POINT_SIZE = 10

# ==============================================
# LABELS
# ==============================================

STATUS_TEXT = {
    "idle": "Ready",
    "listening": "Listening...",
    "thinking": "Thinking...",
    "speaking": "Speaking...",
    "error": "Something went wrong",
}

WAKE_WORD_ACTIVE = "Wake word active"
