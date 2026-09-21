"""System-tray integration for Astra.

Astra keeps running quietly in the tray while the overlay is hidden.
The tray owns the only way to shut Astra down cleanly (Exit), plus
quick controls to open the overlay and pause/resume listening.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QVBoxLayout,
)

from config.settings import AI_MODEL, AI_PROVIDER, ASTRA_VERSION
from ui import theme


def build_tray_icon(size=64):
    """Draw the Astra orb as the tray icon (no image assets)."""

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)

    center = QPointF(size / 2, size / 2)

    glow = QRadialGradient(center, size * 0.45)
    glow.setColorAt(0.0, QColor(34, 211, 238, 220))
    glow.setColorAt(0.6, QColor(34, 211, 238, 90))
    glow.setColorAt(1.0, QColor(34, 211, 238, 0))

    painter.setPen(Qt.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(QRectF(2, 2, size - 4, size - 4))

    core = QRadialGradient(center, size * 0.22)
    core.setColorAt(0.0, QColor(255, 255, 255, 240))
    core.setColorAt(0.4, QColor(34, 211, 238, 255))
    core.setColorAt(1.0, QColor(34, 211, 238, 60))

    painter.setBrush(core)
    painter.drawEllipse(center, size * 0.20, size * 0.20)

    painter.end()

    return QIcon(pixmap)


def settings_text():
    return (
        f"Astra version: {ASTRA_VERSION}\n"
        f"AI provider: {AI_PROVIDER or 'none'}\n"
        f"AI model: {AI_MODEL or '(not configured)'}"
    )


class AstraTray:

    def __init__(self, parent, signals, overlay=None):
        self._signals = signals
        self._overlay = overlay
        self._paused = False

        self._tray = None

        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self._tray = QSystemTrayIcon(build_tray_icon(), parent)
        self._tray.setToolTip("Astra")

        menu = QMenu(parent)

        self._open_action = QAction("Open", menu)
        self._open_action.triggered.connect(self._open)

        self._pause_action = QAction("Pause Listening", menu)
        self._pause_action.triggered.connect(self._pause)

        self._resume_action = QAction("Resume Listening", menu)
        self._resume_action.triggered.connect(self._resume)
        self._resume_action.setVisible(False)

        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self._show_settings)

        about_action = QAction("About", menu)
        about_action.triggered.connect(self._show_about)

        exit_action = QAction("Exit", menu)
        exit_action.triggered.connect(self._exit)

        menu.addAction(self._open_action)
        menu.addSeparator()
        menu.addAction(self._pause_action)
        menu.addAction(self._resume_action)
        menu.addSeparator()
        menu.addAction(settings_action)
        menu.addAction(about_action)
        menu.addSeparator()
        menu.addAction(exit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._activated)

        self._signals.paused_changed.connect(self._set_paused_ui)

    # ==============================================
    # TRAY LIFECYCLE
    # ==============================================

    def show(self):
        if self._tray is not None:
            self._tray.show()

    def hide(self):
        if self._tray is not None:
            self._tray.hide()

    # ==============================================
    # ACTIONS
    # ==============================================

    def _activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick and self._overlay is not None:
            self._overlay.show_overlay(keep_seconds=8)

    def _open(self):
        if self._overlay is not None:
            self._overlay.show_overlay(keep_seconds=8)

    def _pause(self):
        self._signals.pause_requested.emit()

    def _resume(self):
        self._signals.resume_requested.emit()

    def _set_paused_ui(self, paused):
        self._paused = paused
        if self._tray is None:
            return
        self._pause_action.setVisible(not paused)
        self._resume_action.setVisible(paused)
        self._tray.setToolTip(
            "Astra (paused)" if paused else "Astra"
        )

    def _exit(self):
        self._signals.exit_requested.emit()

    # ==============================================
    # DIALOGS
    # ==============================================

    def _show_settings(self):
        dialog = QDialog()
        dialog.setWindowTitle("Astra Settings")
        dialog.setMinimumWidth(300)

        layout = QVBoxLayout(dialog)
        label = QLabel(settings_text())
        label.setFont(QFont(theme.FONT_FAMILY, 10))
        layout.addWidget(label)

        dialog.exec()

    def _show_about(self):
        QMessageBox.about(
            None,
            "About Astra",
            f"Astra version {ASTRA_VERSION}\n"
            "A local-first Windows voice assistant.\n"
            "\n"
            "Say the wake word, then speak a command.\n"
            "The floating orb appears while Astra listens.",
        )
