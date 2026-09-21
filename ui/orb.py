"""AstraOrb: the animated indicator for the floating overlay.

A lightweight painted widget (no image assets) animating at roughly
UI_ANIM_FPS via a single QTimer.  It supports the five GUI states
and an optional amplitude feed while speaking.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from config.settings import UI_ANIM_FPS
from ui import theme
from ui.state import ERROR, IDLE, LISTENING, SPEAKING, THINKING

MODE_COLORS = {
    IDLE: theme.IDLE_GLOW,
    LISTENING: theme.LISTENING_GLOW,
    THINKING: theme.THINKING_GLOW,
    SPEAKING: theme.SPEAKING_GLOW,
    ERROR: theme.ERROR_GLOW,
}


class AstraOrb(QWidget):

    clicked = Signal()

    def __init__(self, parent=None, size=theme.ORB_SIZE):
        super().__init__(parent)

        self._size = size
        self._phase = 0.0
        self._mode = IDLE
        self._amplitude = 0.0

        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.setInterval(max(16, int(1000 / max(1, UI_ANIM_FPS))))
        self._timer.timeout.connect(self._tick)

    # ==============================================
    # PUBLIC API
    # ==============================================

    def set_mode(self, mode):
        if mode != self._mode:
            self._mode = mode
            self._phase = 0.0
            self._redraw()

    def mode(self):
        return self._mode

    def set_amplitude(self, value):
        self._amplitude = max(0.0, min(1.0, float(value)))

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def isActive(self):
        return self._timer.isActive()

    # ==============================================
    # ANIMATION
    # ==============================================

    def _tick(self):
        self._phase += 0.09
        self._redraw()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def _redraw(self):
        if self.isVisible():
            self.update()

    # ==============================================
    # MODE MATH
    # ==============================================

    def _core_radius(self, size):
        if self._mode == SPEAKING and self._amplitude > 0.0:
            return size * (0.20 + 0.16 * self._amplitude)

        if self._mode == IDLE:
            return size * 0.28 * (0.70 + 0.30 * (0.5 + 0.5 * math.sin(self._phase * 1.2)))

        if self._mode == ERROR:
            return size * 0.26

        return size * 0.26 * (0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._phase * 1.8)))

    def _ring_radius(self, size):
        if self._mode == IDLE:
            return size * 0.42

        if self._mode == LISTENING:
            return size * (0.40 + 0.08 * (0.5 + 0.5 * math.sin(self._phase * 1.6)))

        if self._mode == THINKING:
            return size * (0.40 + 0.05 * (0.5 + 0.5 * math.sin(self._phase * 0.7)))

        if self._mode == ERROR:
            return size * 0.40

        if self._amplitude > 0.0:
            return size * (0.34 + 0.16 * self._amplitude)

        return size * (0.36 + 0.10 * (0.5 + 0.5 * math.sin(self._phase * 2.2)))

    def _listening_rings(self):
        if self._mode != LISTENING:
            return []

        ring = (self._phase / (2 * math.pi)) % 1.0

        return [(ring, 1.0 - ring), ((ring + 0.5) % 1.0, 1.0 - ((ring + 0.5) % 1.0))]

    def _rotating_angle(self):
        if self._mode != THINKING:
            return None

        return math.degrees(self._phase * 1.1)

    # ==============================================
    # PAINT
    # ==============================================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        size = min(rect.width(), rect.height())
        center = QPointF(rect.center().x(), rect.center().y())
        color = MODE_COLORS.get(self._mode, theme.IDLE_GLOW)

        # Inner glow.
        glow = QRadialGradient(center, size * 0.5)
        glow.setColorAt(0.0, QColor(color.red(), color.green(), color.blue(), 200))
        glow.setColorAt(0.55, QColor(color.red(), color.green(), color.blue(), 70))
        glow.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 0))

        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(rect)

        # Core.
        core_radius = self._core_radius(size)
        core = QRadialGradient(center, max(1.0, core_radius * 1.6))
        core.setColorAt(0.0, QColor(255, 255, 255, 235))
        core.setColorAt(0.35, QColor(color.red(), color.green(), color.blue(), 255))
        core.setColorAt(1.0, QColor(color.red(), color.green(), color.blue(), 40))

        painter.setBrush(core)
        painter.drawEllipse(center, core_radius, core_radius)

        # Outer ring.
        ring_radius = self._ring_radius(size)
        ring_width = 2.0 + (2.0 if self._mode == SPEAKING else 0.0)

        painter.setPen(
            QPen(
                QColor(color.red(), color.green(), color.blue(), 150),
                ring_width,
            )
        )
        painter.setBrush(Qt.NoBrush)

        if self._mode == THINKING:
            start = self._rotating_angle()
            painter.drawArc(
                QRectF(
                    center.x() - ring_radius,
                    center.y() - ring_radius,
                    ring_radius * 2,
                    ring_radius * 2,
                ),
                int(start),
                220 * 16,
            )
        else:
            painter.drawEllipse(center, ring_radius, ring_radius)

        # Expanding rings while listening.
        for fraction, alpha in self._listening_rings():
            r = size * (0.35 + 0.35 * fraction)
            painter.setPen(
                QPen(
                    QColor(color.red(), color.green(), color.blue(), int(110 * alpha)),
                    1.5,
                )
            )
            painter.drawEllipse(center, r, r)

        painter.end()