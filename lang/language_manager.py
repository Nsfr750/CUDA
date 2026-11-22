"""Gestore delle lingue dell'interfaccia."""
from typing import Callable

from lang.translations import LANGUAGES, TRANSLATIONS


class LanguageManager:
    """Fornisce le stringhe tradotte e notifica i cambi di lingua."""

    def __init__(self, language: str = "it"):
        self._language = language if language in TRANSLATIONS else "it"
        self._listeners: list[Callable[[str], None]] = []

    @property
    def language(self) -> str:
        return self._language

    def languages(self) -> dict:
        """Dizionario ``{codice: nome}`` delle lingue disponibili."""
        return dict(LANGUAGES)

    def tr(self, key: str, **kwargs) -> str:
        """Traduce ``key`` nella lingua corrente.

        Ricade sull'italiano (poi sulla chiave stessa) se la traduzione
        manca. Gli ``kwargs`` sono interpolati con ``str.format``.
        """
        text = TRANSLATIONS.get(self._language, {}).get(key)
        if text is None:
            text = TRANSLATIONS["it"].get(key, key)
        return text.format(**kwargs) if kwargs else text

    def set_language(self, language: str):
        """Cambia lingua e notifica gli osservatori registrati."""
        if language == self._language or language not in TRANSLATIONS:
            return
        self._language = language
        for fn in self._listeners:
            fn(language)

    def subscribe(self, fn: Callable[[str], None]):
        """Registra un callback invocato al cambio di lingua."""
        self._listeners.append(fn)


# Istanza condivisa dall'applicazione
lang_manager = LanguageManager()
