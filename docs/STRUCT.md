# Struttura del progetto

```
CUDA/
├── main.py                  # entry point (chiama cuda_core_monitor.main)
├── cuda_core_monitor.py     # GUI principale: MainWindow, temi, icona, avvisi
├── gpu_backend.py           # backend GPU: GpuBackend (NVML), AmdBackend,
│                            #   IntelBackend, GpuManager (multi-vendor)
├── report.py                # generazione report PNG/PDF con Wand
├── widgets.py               # widget custom (Sparkline, close_button)
├── menu.py                  # barra dei menu (Help)
├── help.py                  # dialog Guida
├── about.py                 # dialog Informazioni
├── sponsor.py               # dialog Sponsor (PayPal, Monero, QR)
├── update.py                # controllo aggiornamenti (UPDATE_URL)
├── logger.py                # logging su file rotante (logs/)
├── version.py               # versione SemVer 2.0.0 e nome app
├── lang/
│   ├── __init__.py
│   ├── language_manager.py  # LanguageManager + istanza condivisa
│   └── translations.py      # stringhe it/en (nessun JSON)
├── COMPILER/
│   └── comp.py              # script di compilazione Nuitka (dist/)
├── assets/
│   └── icon.png             # icona dell'applicazione
├── tests/
│   ├── test_backend.py      # backend NVML con pynvml finto
│   ├── test_report.py       # PDF puro + render PNG/PDF
│   ├── test_lang.py         # traduzioni e LanguageManager
│   └── test_misc.py         # versione, logger, Sparkline
├── conftest.py              # sys.path + QT_QPA_PLATFORM=offscreen
├── docs/                    # documentazione
├── logs/                    # file di log generati a runtime
├── requirements.txt         # dipendenze runtime
├── requirements-dev.txt     # dipendenze sviluppo (pytest)
├── README.md
├── CHANGELOG.md
└── TO_DO.md
```

## Dipendenze tra moduli

- `main.py` → `cuda_core_monitor`
- `cuda_core_monitor` → `gpu_backend`, `report`, `widgets`, `logger`,
  `lang.language_manager`, `version`
- `report` → `gpu_backend` (tipi), `lang.language_manager`, `logger`, Wand
- `gpu_backend` → `logger`, `pynvml` (opzionale a runtime), `torch`
  (opzionale, solo fallback)
- `tests/` importano i moduli di primo livello tramite `conftest.py`
