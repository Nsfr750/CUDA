# Changelog

Tutte le modifiche rilevanti a questo progetto sono documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto aderisce al [Semantic Versioning 2.0.0](https://semver.org/lang/it/).

## [1.4.3] - 2026-11-22

### Modificato

- `update.py` configurato per l'API GitHub Releases (`Nsfr750/CUDA`) con
  parsing `tag_name` (prefisso `v` gestito), link alla release nel dialog
  e fallback su file di testo `x.y.z` per sorgenti non GitHub

## [1.4.2] - 2026-11-22

### Modificato

- Icona dell'applicazione caricata da `assets/icon.png` (finestra e tray),
  con fallback sull'icona disegnata via QPainter se il file manca;
  inclusa nella build Nuitka via `--include-data-files`

## [1.4.1] - 2026-11-22

### Aggiunto

- Script di compilazione Nuitka `COMPILER/comp.py` (standalone o
  `--onefile`, plugin PySide6, metadati di versione, torch escluso)
- `nuitka` in `requirements-dev.txt`

## [1.4.0] - 2026-11-22

### Aggiunto

- Barra dei menu con menu Aiuto: Guida, Controlla aggiornamenti,
  Informazioni, Sponsor (`menu.py`)
- Dialog "Informazioni" (`about.py`), "Aiuto" (`help.py`) e "Sponsor"
  (`sponsor.py` con PayPal, indirizzo Monero e QR via segno)
- Sistema di controllo aggiornamenti (`update.py`): confronto SemVer con
  versione remota scaricata da `UPDATE_URL` (configurabile)
- Dipendenza `segno` per i QR code (senza PIL)
- Helper `close_button()` in `widgets.py` (pulsante Chiudi standard)

## [1.3.1] - 2026-11-22

### Modificato

- Layout a due colonne: controlli/info a sinistra, grafici e processi a
  destra — tutte le sezioni visibili anche su display bassi (es. 1900x600);
  dimensione minima finestra ~1190x551

## [1.3.0] - 2026-11-22

### Aggiunto

- Supporto multi-vendor: `GpuManager` aggrega backend NVIDIA (NVML),
  AMD (`amdsmi`, `pyadl` o registro Windows) e Intel (registro Windows)
- Esportazione dello storico campioni in CSV (separatore `;`)
- Opzione "Riduci nella tray alla chiusura" (persistente): il monitoraggio
  continua in background con notifiche tray attive
- Campo `vendor` in `GpuInfo` e prefisso vendor nella selezione GPU
- Cleanup centralizzato su `aboutToQuit` (salvataggio preferenze + NVML)

## [1.2.0] - 2026-11-22

### Aggiunto

- Monitoraggio per-processo: tabella con PID, nome e memoria GPU usata
  (via `nvmlDeviceGetCompute/GraphicsRunningProcesses` + psutil)
- Icona nella system tray con menu Mostra/Esci e notifiche sugli avvisi
- Lettura velocità ventola (%) e P-state nello stato live
- Grafico storico dell'uso memoria (%)
- Persistenza delle preferenze tra le sessioni (QSettings: tema, lingua,
  intervallo, soglie, avvisi)
- Dipendenza `psutil` per la risoluzione dei nomi dei processi

## [1.1.0] - 2026-11-22

### Aggiunto

- Grafici storici anche per temperatura e potenza (sparkline)
- Export del report in formato PDF (generazione interna, senza delegate)
- Tema scuro/chiaro selezionabile e icona dell'applicazione
- Avvisi configurabili su soglie di temperatura e potenza
- Internazionalizzazione italiano/inglese (pacchetto `lang/`)
- Logging su file rotante (`logger.py`, cartella `logs/`)
- `version.py` per il controllo della versione (SemVer 2.0.0)
- `main.py` come entry point
- Test pytest in `tests/` per backend, report, i18n e widget
- Documentazione in `docs/` (STRUCT.md, USER_GUIDE.md)
- `requirements-dev.txt` per le dipendenze di sviluppo

### Modificato

- Ristrutturazione modulare: `gpu_backend.py`, `report.py` e `widgets.py`
  estratti da `cuda_core_monitor.py`

## [1.0.0] - 2026-11-22

### Aggiunto

- GUI PySide6 per il monitoraggio delle GPU NVIDIA
- Conteggio CUDA core via NVML con fallback `SM x core/SM` (PyTorch opzionale)
- Monitoraggio live: utilizzo, memoria, temperatura, potenza, clock SM/memoria
- Grafico sparkline dell'utilizzo GPU
- Esportazione report PNG tramite Wand/ImageMagick
- `requirements.txt` con le dipendenze del progetto
