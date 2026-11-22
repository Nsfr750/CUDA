"""Sistema di controllo degli aggiornamenti.

Scarica una stringa di versione da ``UPDATE_URL`` (file di testo che
contiene solo ``x.y.z``) e la confronta con la versione locale.
"""
import urllib.request

from version import APP_NAME, __version__
from lang.language_manager import lang_manager
from logger import get_logger
from PySide6.QtWidgets import QMessageBox

log = get_logger(__name__)
tr = lang_manager.tr

# URL di un file di testo contenente solo la versione (es. "1.4.0").
# Lasciare vuoto per disabilitare il controllo online.
UPDATE_URL = ""


def parse_version(text: str) -> tuple[int, ...]:
    """Converte ``"1.2.3"`` in ``(1, 2, 3)``; solleva ValueError se invalida."""
    parts = tuple(int(p) for p in text.strip().split("."))
    if not parts:
        raise ValueError("versione vuota")
    return parts


def is_newer(remote: str, local: str) -> bool:
    """True se la versione ``remote`` è più recente di ``local``."""
    r, l = parse_version(remote), parse_version(local)
    n = max(len(r), len(l))
    return r + (0,) * (n - len(r)) > l + (0,) * (n - len(l))


def fetch_latest_version(timeout: int = 5) -> str:
    """Scarica la versione più recente da ``UPDATE_URL``."""
    with urllib.request.urlopen(UPDATE_URL, timeout=timeout) as r:
        text = r.read().decode("utf-8").strip()
    return parse_version(text) and text  # valida e restituisce la stringa


def check_for_updates(parent=None):
    """Mostra un dialog con l'esito del controllo aggiornamenti."""
    title = tr("update_title")
    if not UPDATE_URL:
        QMessageBox.information(parent, title, tr("update_no_source"))
        return
    try:
        remote = fetch_latest_version()
    except Exception as e:
        log.warning("Controllo aggiornamenti fallito: %s", e)
        QMessageBox.warning(parent, title, tr("update_error", e=e))
        return
    if is_newer(remote, __version__):
        QMessageBox.information(parent, title,
                                tr("update_available", v=remote))
    else:
        QMessageBox.information(parent, title,
                                tr("update_up_to_date", v=__version__))
