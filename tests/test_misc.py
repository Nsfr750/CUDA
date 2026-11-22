"""Test trasversali: versione, logger, widget sparkline."""
import re

import version
from logger import get_logger


def test_versione_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+", version.__version__)
    assert version.__version__ == (
        f"{version.VERSION_MAJOR}.{version.VERSION_MINOR}"
        f".{version.VERSION_PATCH}")
    assert version.APP_NAME


def test_get_logger():
    log = get_logger("test")
    assert log.name == "cuda_core_monitor.test"


def test_update_parse_e_confronto():
    import update
    assert update.parse_version("1.2.3") == (1, 2, 3)
    assert update.parse_version("v1.2.3") == (1, 2, 3)
    assert update.is_newer("1.4.0", "1.3.9")
    assert not update.is_newer("1.3.0", "1.3.0")
    assert not update.is_newer("1.2", "1.2.1")


def test_update_fetch_github_json(monkeypatch):
    import io
    import update

    class _Resp:
        def read(self):
            return b'{"tag_name": "v9.9.9", "html_url": "https://x/r"}'
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(update.urllib.request, "urlopen",
                        lambda *a, **k: _Resp())
    v, page = update.fetch_latest_version()
    assert v == "9.9.9" and page == "https://x/r"


def test_update_fetch_file_testo(monkeypatch):
    import update

    class _Resp:
        def read(self):
            return b"9.8.7\n"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(update.urllib.request, "urlopen",
                        lambda *a, **k: _Resp())
    v, page = update.fetch_latest_version()
    assert v == "9.8.7" and page == ""


def test_sparkline(qapp=None):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from widgets import Sparkline

    QApplication.instance() or QApplication([])
    s = Sparkline(maxlen=10, max_value=100)
    s.push(50)
    assert list(s.data)[-1] == 50
    assert s.current_max() == 100

    auto = Sparkline(maxlen=10, max_value=None)
    auto.push(30)
    assert auto.current_max() == 30
    auto.push(80)
    assert auto.current_max() == 80

    s.set_theme("light")
    assert s.bg_color == "#f2f5f8"
    s.clear()
    assert max(s.data) == 0


def test_menu_presente():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QMenu
    import cuda_core_monitor as m

    QApplication.instance() or QApplication([])
    w = m.MainWindow()
    menus = w.menuBar().findChildren(QMenu)
    texts = [a.text() for mn in menus for a in mn.actions() if a.text()]
    assert len(menus) >= 1
    assert len(texts) >= 4  # guida, aggiornamenti, info, sponsor
