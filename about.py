"""Finestra 'Informazioni' dell'applicazione."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel

from version import APP_NAME, __version__
from lang.language_manager import lang_manager
from widgets import close_button

tr = lang_manager.tr

AUTHOR = "Nsfr750"
WEBSITE = "https://www.tuxxle.org"
ORGANIZATION = "Tuxxle"
COPYRIGHT = "© Copyright 2024-2026 Nsfr750 - All rights reserved."

def show_about(parent=None):
    """Mostra il dialog 'Informazioni' (modale)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("about_title", app=APP_NAME))
    lay = QVBoxLayout(dlg)

    icon = QLabel()
    icon.setPixmap(parent.windowIcon().pixmap(64, 64) if parent else None)
    lay.addWidget(icon, alignment=Qt.AlignCenter)

    title = QLabel(f"<b>{APP_NAME}</b>  v{__version__}")
    title.setStyleSheet("font-size:16px;")
    lay.addWidget(title, alignment=Qt.AlignCenter)

    lines = QLabel(
        f"{tr('about_author', author=AUTHOR, org=ORGANIZATION)}<br>"
        f"{tr('about_license')}: GPLv3<br>"
        f"<a href='{WEBSITE}'>{WEBSITE}</a><br><br>{COPYRIGHT}")
    lines.setOpenExternalLinks(True)
    lines.setWordWrap(True)
    lay.addWidget(lines)

    row = QHBoxLayout()
    row.addStretch(1)
    btn = close_button(tr("close"))
    btn.clicked.connect(dlg.accept)
    row.addWidget(btn)
    lay.addLayout(row)
    dlg.exec()
