"""Finestra di aiuto dell'applicazione."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel

from version import APP_NAME
from lang.language_manager import lang_manager
from widgets import close_button

tr = lang_manager.tr


def show_help(parent=None):
    """Mostra il dialog di aiuto (modale)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("help_title", app=APP_NAME))
    dlg.setMinimumWidth(480)
    lay = QVBoxLayout(dlg)

    body = QLabel(tr("help_body"))
    body.setWordWrap(True)
    lay.addWidget(body, 1)

    row = QHBoxLayout()
    row.addStretch(1)
    btn = close_button(tr("close"))
    btn.clicked.connect(dlg.accept)
    row.addWidget(btn)
    lay.addLayout(row)
    dlg.exec()
