"""Widget custom per la GUI."""
from collections import deque
from typing import Optional

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF
from PySide6.QtWidgets import QWidget, QPushButton


def close_button(text: str) -> QPushButton:
    """Pulsante di chiusura standard: rosso con testo bianco."""
    btn = QPushButton(text)
    btn.setStyleSheet("background-color:#c0392b;color:white;"
                      "font-weight:bold;padding:6px 18px;")
    return btn

class Sparkline(QWidget):
    """Grafico sparkline a linea singola con riempimento.

    Args:
        maxlen: numero massimo di campioni mantenuti.
        max_value: valore massimo della scala; ``None`` per autoscala.
        line: colore della linea/riempimento.
    """

    _THEMES = {
        "dark": ("#12181f", "#2a3340"),
        "light": ("#f2f5f8", "#c9d3dd"),
    }

    def __init__(self, maxlen: int = 120, max_value: Optional[float] = 100.0,
                 line: str = "#76b900", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.data = deque([0] * maxlen, maxlen=maxlen)
        self.max_value = max_value
        self.line_color = line
        self.bg_color, self.grid_color = self._THEMES["dark"]
        self.setMinimumHeight(50)

    def set_theme(self, theme: str):
        """Applica i colori di sfondo/griglia del tema scelto."""
        self.bg_color, self.grid_color = self._THEMES.get(
            theme, self._THEMES["dark"])
        self.update()

    def clear(self):
        """Azzera lo storico dei campioni."""
        self.data = deque([0] * self.data.maxlen, maxlen=self.data.maxlen)
        self.update()

    def push(self, v: float):
        self.data.append(v)
        self.update()

    def current_max(self) -> float:
        """Massimo della scala: fisso o calcolato sui dati (autoscala)."""
        if self.max_value:
            return self.max_value
        return max(1.0, max(self.data))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.fillRect(r, QColor(self.bg_color))
        mx = self.current_max()
        p.setPen(QPen(QColor(self.grid_color), 1))
        for q in (25, 50, 75):
            y = r.bottom() - r.height() * q / 100
            p.drawLine(r.left(), int(y), r.right(), int(y))
        n = len(self.data)
        pts = [QPointF(r.left() + i * r.width() / (n - 1),
                       r.bottom() - r.height() * min(v, mx) / mx)
               for i, v in enumerate(self.data)]
        poly = QPolygonF([QPointF(r.left(), r.bottom())] + pts +
                         [QPointF(r.right(), r.bottom())])
        fill = QColor(self.line_color)
        fill.setAlpha(60)
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawPolygon(poly)
        p.setPen(QPen(QColor(self.line_color), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF(pts))
