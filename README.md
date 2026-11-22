# CUDA Core Monitor

Monitor GUI per GPU scritto in Python con PySide6. Mostra il numero di
CUDA core (NVIDIA), lo stato live della scheda (utilizzo, memoria,
temperatura, potenza, clock, ventola), grafici storici, avvisi su soglie
ed esporta report PNG/PDF e storico CSV. Supporta anche GPU AMD
(via `amdsmi` o `pyadl`, opzionali) e Intel (rilevamento da registro).

## Funzionalità

- Conteggio dei CUDA core tramite NVML (`nvmlDeviceGetNumGpuCores`) con
  fallback sulla stima `SM x core/SM` (via PyTorch, se installato) in base alla
  compute capability
- Selezione della GPU in caso di sistemi multi-GPU
- Monitoraggio live con intervallo configurabile (100–5000 ms):
  - utilizzo GPU e memoria con barre di avanzamento
  - stima dei core attivi
  - temperatura, potenza, clock SM e clock memoria
- Grafici storici di utilizzo, memoria, temperatura e potenza (sparkline)
- Elenco dei processi che usano la GPU (PID, nome, memoria via psutil)
- Lettura ventola (%) e P-state della GPU
- Avvisi configurabili su soglie di temperatura e potenza, con notifica tray
- Icona nella system tray (mostra/esci, notifiche sugli avvisi)
- Esportazione di un report PNG o PDF (richiede ImageMagick)
- Temi scuro/chiaro e interfaccia multilingua (italiano/inglese)
- Preferenze persistenti tra le sessioni (QSettings)
- Riduzione a icona nella system tray alla chiusura (opzionale)
- Esportazione dello storico campioni in CSV
- Supporto multi-vendor: NVIDIA (NVML), AMD (`amdsmi`/`pyadl`, opzionali),
  Intel (info statiche dal registro)
- Logging su file rotante in `logs/`

## Requisiti

- Python 3.12+
- GPU NVIDIA con driver e NVML funzionanti
- ImageMagick installato nel sistema (richiesto da Wand per l'export)
- PyTorch (opzionale, solo per il fallback di stima dei core)

## Installazione

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
# oppure
py -3.14 cuda_core_monitor.py
```

1. Seleziona la GPU dal menu a tendina.
2. Regola intervallo, tema e lingua a piacere.
3. Configura le soglie di avviso nella sezione **Avvisi**.
4. Premi **Esporta report (Wand)** per salvare un report PNG o PDF.

Vedi [docs/USER_GUIDE.md](docs/USER_GUIDE.md) per la guida completa.

## Sviluppo

```bash
pip install -r requirements-dev.txt
py -3.14 -m pytest tests/ -v
```

Struttura del progetto: [docs/STRUCT.md](docs/STRUCT.md)

## Licenza

Distribuito sotto licenza [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html).

© Copyright 2024-2026 Nsfr750 - All rights reserved.
