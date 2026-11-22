"""Barra dei menu dell'applicazione."""
from PySide6.QtWidgets import QMainWindow, QMenuBar

import about
import help as help_mod
import sponsor
import update
from lang.language_manager import lang_manager

tr = lang_manager.tr


def build_menu(window: QMainWindow) -> QMenuBar:
    """Costruisce la barra dei menu sulla finestra data.

    Il menu Help contiene: aiuto, controllo aggiornamenti, informazioni
    e sponsor. Chiamare di nuovo dopo un cambio lingua per ritradurre.
    """
    bar = window.menuBar()
    bar.clear()

    m_help = bar.addMenu(tr("menu_help"))
    act_help = m_help.addAction(tr("menu_help_contents"))
    act_help.triggered.connect(lambda: help_mod.show_help(window))
    act_upd = m_help.addAction(tr("menu_check_updates"))
    act_upd.triggered.connect(lambda: update.check_for_updates(window))
    act_about = m_help.addAction(tr("menu_about"))
    act_about.triggered.connect(lambda: about.show_about(window))
    m_help.addSeparator()
    act_sp = m_help.addAction(tr("menu_sponsor"))
    act_sp.triggered.connect(lambda: sponsor.show_sponsor(window))
    return bar
