"""Sistema di logging dell'applicazione.

Scrive su file rotante in ``logs/cuda_core_monitor.log`` e mostra solo i
warning (e superiori) sulla console.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "cuda_core_monitor.log"
_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_ROOT_NAME = "cuda_core_monitor"


def _configure_root() -> logging.Logger:
    """Configura il logger radice dell'applicazione (una sola volta)."""
    root = logging.getLogger(_ROOT_NAME)
    if root.handlers:
        return root
    root.setLevel(logging.DEBUG)
    LOG_DIR.mkdir(exist_ok=True)

    fh = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3,
                             encoding="utf-8")
    fh.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(ch)
    return root


def get_logger(name: str = "") -> logging.Logger:
    """Restituisce un logger figlio di ``cuda_core_monitor``.

    Args:
        name: nome del modulo chiamante (usare ``__name__``).

    Returns:
        Un ``logging.Logger`` che propaga gli handler al logger radice.
    """
    root = _configure_root()
    if not name or name == _ROOT_NAME:
        return root
    return logging.getLogger(f"{_ROOT_NAME}.{name}")
