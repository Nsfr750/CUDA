"""Test del sistema di internazionalizzazione."""
from lang.language_manager import LanguageManager, lang_manager
from lang.translations import TRANSLATIONS


def test_lingue_allineate():
    """Tutte le lingue devono definire le stesse chiavi dell'italiano."""
    base = set(TRANSLATIONS["it"])
    for code, strings in TRANSLATIONS.items():
        assert set(strings) == base, f"chiavi mancanti in '{code}'"


def test_tr_italiano():
    lm = LanguageManager("it")
    assert lm.tr("theme_dark") == "Scuro"


def test_tr_inglese():
    lm = LanguageManager("en")
    assert lm.tr("theme_dark") == "Dark"


def test_tr_con_format():
    lm = LanguageManager("it")
    assert lm.tr("source", src="NVML") == "Fonte: NVML"


def test_tr_fallback_chiave_mancante():
    lm = LanguageManager("en")
    assert lm.tr("chiave_inesistente") == "chiave_inesistente"


def test_lingua_non_valida_ripiega_it():
    lm = LanguageManager("xx")
    assert lm.language == "it"


def test_set_language_notifica():
    lm = LanguageManager("it")
    seen = []
    lm.subscribe(seen.append)
    lm.set_language("en")
    assert seen == ["en"]
    lm.set_language("en")  # nessuna notifica se invariata
    assert seen == ["en"]


def test_singleton_condiviso():
    assert lang_manager.language in TRANSLATIONS
