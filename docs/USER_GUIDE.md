# Guida utente

## Avvio

```bash
python main.py
# oppure
py -3.14 cuda_core_monitor.py
```

## Interfaccia

- **GPU**: selezione della scheda in sistemi multi-GPU.
- **Aggiornamento (ms)**: intervallo di campionamento (100–5000 ms).
- **Tema**: Scuro o Chiaro (applicato a palette e grafici).
- **Lingua**: Italiano o English, applicata a caldo a tutta l'interfaccia.

## Sezioni

1. **CUDA core totali**: numero di core con la fonte del dato (NVML o
   stima `SM x core/SM`).
2. **Dettagli GPU**: compute capability, SM, memoria totale, driver.
3. **Stato live**: barre di utilizzo GPU e memoria, core attivi stimati,
   temperatura, potenza, clock, velocità ventola e P-state.
4. **Grafici**: storico di utilizzo (%), memoria (%), temperatura
   (°C, scala 0–110) e potenza (W, scala sul limite NVML o autoscala).
5. **Avvisi**: se abilitati, un messaggio rosso appare quando temperatura o
   potenza superano le soglie impostate; con la tray attiva arriva anche
   una notifica di sistema (evento registrato nel log).
6. **Processi GPU**: tabella dei processi che usano la scheda (PID, nome
   via psutil, memoria occupata), aggiornata a ogni campionamento.

## System tray

L'icona nella tray permette di riaprire la finestra (click o voce
**Mostra**) e di chiudere l'applicazione (**Esci**). Attivando
**Riduci nella tray alla chiusura**, la X della finestra nasconde il
programma nella tray: il monitoraggio e gli avvisi restano attivi.

## GPU non NVIDIA

Le GPU AMD vengono rilevate tramite `amdsmi` o `pyadl` se installati
(metriche live), altrimenti dal registro di Windows (solo info statiche).
Le GPU Intel sono rilevate dal registro di Windows (solo info statiche):
il conteggio dei core e le metriche live risultano `n/d`.

## Menu Aiuto

- **Guida**: riepilogo delle funzionalità.
- **Controlla aggiornamenti**: confronta la versione installata con quella
  pubblicata a `UPDATE_URL` in `update.py` (vuoto = disabilitato).
- **Informazioni**: versione, autore, licenza e sito.
- **Sponsor**: donazioni via PayPal o Monero (con QR code).

## Export CSV

**Esporta storico CSV** salva i campioni raccolti dalla GPU selezionata
(fino a 3600) in formato CSV con separatore `;`: timestamp, utilizzo,
memoria, temperatura, potenza, clock e ventola.

## Preferenze

Tema, lingua, intervallo di aggiornamento, soglie e stato degli avvisi
vengono salvati automaticamente alla chiusura (QSettings, voce
`Tuxxle/CudaCoreMonitor`) e ripristinati all'avvio successivo.

## Export report

Il pulsante **Esporta report (Wand)** salva un'istantanea dello stato della
GPU come PNG oppure PDF (richiede ImageMagick installato nel sistema).

## Log

I log sono scritti in `logs/cuda_core_monitor.log` (rotazione: 3 file da
1 MB). In console vengono mostrati solo warning ed errori.

## Test

```bash
pip install -r requirements-dev.txt
py -3.14 -m pytest tests/ -v
```

I test del report con Wand vengono saltati automaticamente se ImageMagick
non è disponibile.
