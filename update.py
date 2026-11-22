"""Sistema di controllo degli aggiornamenti.

Recupera la versione più recente da ``UPDATE_URL`` e la confronta con
quella locale (SemVer). Sorgenti supportate:

- API GitHub Releases (default): JSON con ``tag_name``/``html_url``
- file di testo contenente solo ``x.y.z`` (es. su tuxxle.org)

Nota: se il repo GitHub è privato l'API risponde 404; serve una release
pubblica oppure un UPDATE_URL verso un file di testo pubblico.
"""
import json
import urllib.request

from PySide6.QtWidgets import QMessageBox

from version import APP_NAME, __version__
from lang.language_manager import lang_manager
from logger import get_logger

log = get_logger(__name__)
tr = lang_manager.tr

GITHUB_REPO = "Nsfr750/CUDA"
UPDATE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"


def parse_version(text: str) -> tuple[int, ...]:
    """Converte ``"1.2.3"`` (o ``"v1.2.3"``) in ``(1, 2, 3)``."""
    parts = tuple(int(p) for p in text.strip().lstrip("vV").split("."))
    if not parts:
        raise ValueError("versione vuota")
    return parts


def is_newer(remote: str, local: str) -> bool:
    """True se la versione ``remote`` è più recente di ``local``."""
    r, l = parse_version(remote), parse_version(local)
    n = max(len(r), len(l))
    return r + (0,) * (n - len(r)) > l + (0,) * (n - len(l))


def fetch_latest_version(timeout: int = 5) -> tuple[str, str]:
    """Scarica la versione più recente.

    Returns:
        ``(versione, url_pagina)`` — url_pagina può essere vuoto.
    """
    req = urllib.request.Request(
        UPDATE_URL,
        headers={"User-Agent": APP_NAME,
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode("utf-8").strip()
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        # File di testo semplice: contiene solo la versione
        return parse_version(data) and data.strip(), ""
    tag = str(payload.get("tag_name", "")).lstrip("vV")
    return parse_version(tag) and tag, payload.get("html_url", "")


def check_for_updates(parent=None):
    """Mostra un dialog con l'esito del controllo aggiornamenti."""
    title = tr("update_title")
    if not UPDATE_URL:
        QMessageBox.information(parent, title, tr("update_no_source"))
        return
    try:
        remote, page = fetch_latest_version()
    except Exception as e:
        log.warning("Controllo aggiornamenti fallito: %s", e)
        QMessageBox.warning(parent, title, tr("update_error", e=e))
        return
    if is_newer(remote, __version__):
        msg = tr("update_available", v=remote)
        if page:
            msg += f"\n{page}"
        QMessageBox.information(parent, title, msg)
    else:
        QMessageBox.information(parent, title,
                                tr("update_up_to_date", v=__version__))
