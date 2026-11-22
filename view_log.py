"""Finestra di visualizzazione del log dell'applicazione."""
import re

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QLabel, QComboBox,
)

from version import APP_NAME
from lang.language_manager import lang_manager
from logger import LOG_DIR, LOG_FILE
from widgets import close_button

tr = lang_manager.tr

MAX_LINES = 5000
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
_LEVEL_RE = re.compile(r"\[(" + "|".join(LEVELS) + r")\]")


def load_log_text(max_lines: int = MAX_LINES) -> str:
    """Ultime ``max_lines`` righe del file di log (vuoto se assente)."""
    try:
        with open(LOG_FILE, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return ""
    return "".join(lines[-max_lines:])


def filter_log_text(text: str, level: str) -> str:
    """Filtra il log per livello esatto.

    ``"ALL"`` restituisce tutto; le righe di continuazione (es. traceback,
    senza marcatore di livello) seguono la riga di livello che le precede.
    """
    if level == "ALL":
        return text
    out = []
    take = False
    for line in text.splitlines(keepends=True):
        m = _LEVEL_RE.search(line)
        if m:
            take = m.group(1) == level
        if take:
            out.append(line)
    return "".join(out)


class LogDialog(QDialog):
    """Dialog read-only con il contenuto del log, aggiornabile."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("log_title", app=APP_NAME))
        self.resize(760, 480)
        lay = QVBoxLayout(self)

        # Filtro livello
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("log_level")))
        self.level = QComboBox()
        self.level.addItems(["ALL", *LEVELS])
        self.level.currentTextChanged.connect(self.reload)
        top.addWidget(self.level)
        top.addStretch(1)
        lay.addLayout(top)

        self.text = QPlainTextEdit(readOnly=True)
        self.text.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        lay.addWidget(self.text, 1)

        row = QHBoxLayout()
        btn_refresh = QPushButton(tr("log_refresh"))
        btn_refresh.clicked.connect(self.reload)
        row.addWidget(btn_refresh)
        btn_folder = QPushButton(tr("log_open_folder"))
        btn_folder.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR))))
        row.addWidget(btn_folder)
        row.addStretch(1)
        btn = close_button(tr("close"))
        btn.clicked.connect(self.accept)
        row.addWidget(btn)
        lay.addLayout(row)
        self.reload()

    def reload(self):
        """Ricarica il contenuto del log e scorre in fondo."""
        text = filter_log_text(load_log_text(), self.level.currentText())
        self.text.setPlainText(text or tr("log_empty"))
        self.text.moveCursor(QTextCursor.End)


def show_log(parent=None):
    """Mostra il dialog del log (modale)."""
    LogDialog(parent).exec()
