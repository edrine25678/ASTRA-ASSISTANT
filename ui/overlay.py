"""AstraOverlay: the floating, frameless assistant overlay.

A small dark-glass widget that appears near the bottom-center of the
primary screen when Astra activates, fades in, shows the orb/status/
transcript, and fades away after a short inactivity timeout.  It
never takes focus from the user's active application, never appears
in the taskbar (Qt.Tool), and is purely a view: all behavior is
driven by the ui.signals hub from the voice worker.
"""

import html

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config.settings import (
    UI_FADE_IN_MS,
    UI_FADE_OUT_MS,
    UI_AUTO_HIDE_SECONDS,
)

from ui import theme
from ui.orb import AstraOrb
from ui.state import ERROR, IDLE, LISTENING, SPEAKING, THINKING

# Settings used in Tests can override the auto-hide delay.
_AUTO_HIDE_MS = max(100, int(UI_AUTO_HIDE_SECONDS * 1000))


class AstraOverlay(QWidget):

    text_submitted = Signal(str)

    def __init__(self, parent=None, auto_hide_ms=_AUTO_HIDE_MS):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._auto_hide_ms = auto_hide_ms
        self._expanded = False
        self._fading_out = False

        self.setFixedWidth(theme.OVERLAY_WIDTH)
        self._apply_size(theme.OVERLAY_COMPACT_HEIGHT)

        # ==========================================
        # CONTENT
        # ==========================================

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.orb = AstraOrb(self)
        self.orb.setCursor(Qt.PointingHandCursor)
        self.orb.clicked.connect(self.toggle_expanded)
        header.addWidget(self.orb, 0, Qt.AlignVCenter)

        titles = QVBoxLayout()
        titles.setSpacing(1)

        self._title = QLabel("ASTRA")
        self._title.setFont(QFont(theme.FONT_FAMILY, theme.TITLE_POINT_SIZE))
        self._title.setStyleSheet(
            f"color: {theme.TEXT.name()}; font-weight: 600;"
        )
        titles.addWidget(self._title)

        self._provider_label = QLabel(theme.WAKE_WORD_ACTIVE)
        self._provider_label.setFont(
            QFont(theme.FONT_FAMILY, 8)
        )
        self._provider_label.setStyleSheet(
            f"color: {theme.TEXT_DIM.name()};"
        )
        titles.addWidget(self._provider_label)

        header.addLayout(titles)
        header.addStretch(1)

        root.addLayout(header)

        self._status = QLabel(theme.STATUS_TEXT[IDLE])
        self._status.setFont(
            QFont(theme.FONT_FAMILY, theme.STATUS_POINT_SIZE)
        )
        self._status.setStyleSheet(
            f"color: {theme.TEXT_MUTED.name()};"
        )
        root.addWidget(self._status)

        # ----- transcript (expanded only) -----

        self._transcript = QScrollArea()
        self._transcript.setWidgetResizable(True)
        self._transcript.setFrameShape(QScrollArea.NoFrame)
        self._transcript.setStyleSheet("background: transparent;")

        self._transcript_box = QWidget()
        self._transcript_box.setStyleSheet("background: transparent;")

        self._transcript_layout = QVBoxLayout(self._transcript_box)
        self._transcript_layout.setContentsMargins(2, 2, 6, 2)
        self._transcript_layout.setSpacing(6)
        self._transcript_layout.addStretch(1)

        self._transcript.setWidget(self._transcript_box)

        # ----- input (expanded only) -----

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Talk to Astra...")
        self._input.setFont(
            QFont(theme.FONT_FAMILY, theme.INPUT_POINT_SIZE)
        )
        self._input.setStyleSheet(
            "QLineEdit {"
            "  background: rgba(30, 38, 54, 200);"
            "  border: 1px solid rgba(56, 189, 248, 70);"
            f"  border-radius: 14px; padding: 8px 12px; color: {theme.TEXT.name()};"
            "}"
            "QLineEdit:focus { border: 1px solid rgba(34, 211, 238, 160); }"
        )
        self._input.returnPressed.connect(self._submit_text)
        input_row.addWidget(self._input, 1)

        self._send_button = QPushButton("\u276f")
        self._send_button.setCursor(Qt.PointingHandCursor)
        self._send_button.setFixedSize(34, 34)
        self._send_button.setStyleSheet(
            "QPushButton {"
            "  background: rgba(34, 211, 238, 60);"
            "  border: 1px solid rgba(34, 211, 238, 140);"
            "  border-radius: 17px; color: white; font-weight: 600;"
            "}"
            "QPushButton:hover { background: rgba(34, 211, 238, 100); }"
            "QPushButton:pressed { background: rgba(34, 211, 238, 40); }"
        )
        self._send_button.clicked.connect(self._submit_text)
        input_row.addWidget(self._send_button, 0)

        self._transcript.setVisible(False)
        input_row_widget = QWidget()
        input_row_widget.setLayout(input_row)
        input_row_widget.setVisible(False)
        self._input_row = input_row_widget

        root.addWidget(self._transcript, 1)
        root.addWidget(self._input_row, 0)

        # ==========================================
        # FADE
        # ==========================================

        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)

        self._fade_in = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_in.setDuration(UI_FADE_IN_MS)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.OutCubic)

        self._fade_out = QPropertyAnimation(self._effect, b"opacity", self)
        self._fade_out.setDuration(UI_FADE_OUT_MS)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.InCubic)
        self._fade_out.finished.connect(self._hide_complete)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.start_fade_out)

    # ==============================================
    # SHOW / HIDE
# ==============================================

    def show_overlay(self, keep_seconds=None):
        """Show and fade in.  keep_seconds None means no auto-hide."""

        self._hide_timer.stop()
        self._fading_out = False
        self._effect.setOpacity(0.0)
        self._move_to_primary_screen_bottom()
        self.orb.start()
        self.show()
        self.raise_()

        if self._fade_in.state() == QAbstractAnimation.State.Stopped:
            self._fade_in.start()

        if keep_seconds is not None:
            self._hide_timer.start(max(100, int(keep_seconds * 1000)))

    def schedule_hide(self, seconds=None):
        """Arm the auto-hide timer (used after speaking finishes)."""

        ms = self._auto_hide_ms if seconds is None else max(100, int(seconds * 1000))
        self._hide_timer.start(ms)

    def cancel_hide(self):
        self._hide_timer.stop()

    def start_fade_out(self):
        if self._fading_out or not self.isVisible():
            return

        self._hide_timer.stop()
        self._fading_out = True

        if self._fade_out.state() == QAbstractAnimation.State.Stopped:
            self._fade_out.start()
        else:
            self._hide_complete()

    def _hide_complete(self):
        self._fading_out = False
        self.orb.stop()
        self.hide()

    # ==============================================
    # STATUS
    # ==============================================

    def set_status(self, mode, text=None):
        label = text or theme.STATUS_TEXT.get(mode, " ")

        self._status.setText(label)
        self.orb.set_mode(mode)

        if mode == ERROR:
            self._status.setStyleSheet(
                f"color: {theme.ERROR_COLOR.name()};"
            )
        elif mode in (SPEAKING, THINKING, LISTENING):
            self._status.setStyleSheet(
                f"color: {theme.TEXT.name()};"
            )
        else:
            self._status.setStyleSheet(
                f"color: {theme.TEXT_MUTED.name()};"
            )

    def set_provider(self, label, available):
        text = label if available else theme.WAKE_WORD_ACTIVE
        self._provider_label.setText(text)
        self._provider_label.setStyleSheet(
            f"color: {theme.TEXT_DIM.name()};"
        )

    def add_user_text(self, text):
        self._add_transcript("You", text, theme.USER_COLOR)

    def add_astra_text(self, text):
        self._add_transcript("Astra", text, theme.ASTRA_COLOR)

    def clear_transcript(self):
        layout = self._transcript_layout
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _add_transcript(self, who, text, color):
        label = QLabel(f"<b>{who}:</b> {html.escape(text)}")
        label.setFont(
            QFont(theme.FONT_FAMILY, theme.TRANSCRIPT_POINT_SIZE)
        )
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet(
            f"color: {color.name()}; background: transparent;"
        )
        self._transcript_layout.insertWidget(
            self._transcript_layout.count() - 1, label
        )

    # ==============================================
    # EXPANDED MODE
    # ==============================================

    def is_expanded(self):
        return self._expanded

    def toggle_expanded(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded):
        if expanded == self._expanded:
            return

        self._expanded = expanded
        self._transcript.setVisible(expanded)
        self._input_row.setVisible(expanded)
        self._apply_size(
            theme.OVERLAY_EXPANDED_HEIGHT if expanded else theme.OVERLAY_COMPACT_HEIGHT
        )
        self._clamp_to_screen()

    def _apply_size(self, height):
        self.setFixedHeight(height)

    # ==============================================
    # POSITIONING
    # ==============================================

    def _primary_screen_geometry(self):
        from PySide6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()

        if screen is not None:
            return screen.availableGeometry()

        return self.screen().availableGeometry() if self.screen() else None

    def _move_to_primary_screen_bottom(self):
        geo = self._primary_screen_geometry()

        if geo is None:
            return

        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - theme.SCREEN_MARGIN

        self.move(max(geo.x(), x), max(geo.y(), y))

    def _clamp_to_screen(self):
        geo = self._primary_screen_geometry()

        if geo is None:
            return

        x = self.x()
        y = self.y()

        if x < geo.x():
            x = geo.x()
        if x + self.width() > geo.x() + geo.width():
            x = geo.x() + geo.width() - self.width()
        if y < geo.y():
            y = geo.y()

        self.move(x, y)

    # ==============================================
    # PAINT
    # ==============================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect().adjusted(1, 1, -1, -1)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0.0, theme.BG_TOP)
        gradient.setColorAt(1.0, theme.BG_BOTTOM)

        painter.setPen(
            QPen(
                theme.BORDER if not self._fading_out else theme.BORDER_DIM,
                1.0,
            )
        )
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, theme.OVERLAY_RADIUS, theme.OVERLAY_RADIUS)

        painter.end()

    # ==============================================
    # INPUT
    # ==============================================

    def _submit_text(self):
        text = self._input.text().strip()

        if not text:
            return

        self._input.clear()
        self.text_submitted.emit(text)

