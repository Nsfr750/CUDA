"""Finestra 'Sponsor' dell'applicazione."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap, QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
)

from lang.language_manager import lang_manager
from widgets import close_button

tr = lang_manager.tr

PAYPAL_URL = "https://paypal.me/3dmega"
MONERO_ADDRESS = ("47Jc6MC47WJVFhiQFYwHyBNQP5BEsjUPG6tc8R37FwcTY8K5Y3LvFzveS"
                  "XoGiaDQSxDrnCUBJ5WBj6Fgmsfix8VPD4w3gXF")


def _qr_pixmap(data: str, size: int = 160):
    """QR code come QPixmap via segno (nessun PIL); None se non disponibile."""
    try:
        import io
        import segno
        buf = io.BytesIO()
        segno.make(data).save(buf, kind="png", scale=4, border=2)
        pm = QPixmap()
        pm.loadFromData(buf.getvalue())
        return pm.scaled(size, size, Qt.KeepAspectRatio,
                         Qt.SmoothTransformation)
    except Exception:
        return None


def show_sponsor(parent=None):
    """Mostra il dialog 'Sponsor' (modale)."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(tr("menu_sponsor"))
    lay = QVBoxLayout(dlg)

    text = QLabel(tr("sponsor_text"))
    text.setWordWrap(True)
    lay.addWidget(text)

    # PayPal
    row = QHBoxLayout()
    btn_pay = QPushButton(tr("sponsor_paypal"))
    btn_pay.clicked.connect(
        lambda: QDesktopServices.openUrl(QUrl(PAYPAL_URL)))
    row.addWidget(btn_pay)
    row.addStretch(1)
    lay.addLayout(row)

    # Monero
    lay.addWidget(QLabel(tr("sponsor_monero")))
    row = QHBoxLayout()
    addr = QLineEdit(MONERO_ADDRESS)
    addr.setReadOnly(True)
    row.addWidget(addr, 1)
    btn_copy = QPushButton(tr("sponsor_copy"))
    btn_copy.clicked.connect(lambda: (
        QGuiApplication.clipboard().setText(MONERO_ADDRESS),
        btn_copy.setText(tr("sponsor_copied"))))
    row.addWidget(btn_copy)
    lay.addLayout(row)

    qr = _qr_pixmap(f"monero:{MONERO_ADDRESS}")
    if qr:
        lay.addWidget(QLabel(pixmap=qr), alignment=Qt.AlignCenter)

    row = QHBoxLayout()
    row.addStretch(1)
    btn = close_button(tr("close"))
    btn.clicked.connect(dlg.accept)
    row.addWidget(btn)
    lay.addLayout(row)
    dlg.exec()
