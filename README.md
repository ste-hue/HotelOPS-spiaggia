# 📊 HotelOPS – Modulo SPIAGGIA

Business-Intelligence per vendite, prenotazioni e incassi della spiaggia

---

## 1. Overview

Questo modulo integra **due mondi dati**:

| Fonte                 | File                                                                             | Contenuto                                    |
| --------------------- | -------------------------------------------------------------------------------- | -------------------------------------------- |
| **Moolty**      | `data/moolty/prodotti/prodotti_YYYY-MM-DD.xlsx`                                | Vendite per reparto (SPIAGGIA, FOOD, BAR …) |
|                       | `data/moolty/totali/totali_YYYY-MM-DD.xlsx`                                    | Incassi di cassa (totale scontrini, ordini)  |
|                       | `data/moolty/primanota/primanota_YYYY-MM-DD.xlsx`                              | Movimenti contabili                          |
| **Spiaggie.it** | `data/spiaggieit/prenotazioni_online_*.csv` / `prenotazioni_online_full.csv` | Stato completo prenotazioni                  |
|                       | `data/spiaggieit/non_pagati_online_full.csv`                                   | Prenotazioni con saldo > 0 €                |
|                       | `arrivi_oggi.csv` / `partenze_oggi.csv`                                      | Flusso presenze del giorno                   |

Obiettivi BI:

1. **Incasso reale** vs **incasso teorico** (prenotazioni).
2. Gap dovuto a prenotazioni non pagate o walk-in.
3. Trend feriali / week-end.
4. Tracciamento giornaliero delle prenotazioni che passano da *aperte* a *chiuse*.

---

## 2. Struttura repository

```
spiaggia/
  data/
    moolty/          # excel esportati da Moolty
    spiaggieit/      # csv dal portale Spiaggie.it
      snap_non_pagati/  # snapshot giornalieri prenotazioni aperte
  notebooks/
    monitor_YYYY-MM-DD.py   # dashboard incassi  (singolo giorno o storico)
    monitor_closure.py      # tracking chiusure prenotazioni
    outputs/                # Excel/PDF/KPI generati
README.md
```

---

## 3. Installazione ambiente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # pandas, openpyxl, pyarrow, matplotlib, etc.
```

---

## 4. Script principali

### 4.1 Dashboard incassi

Analizza vendite (Moolty) e prenotazioni (Spiaggie.it)

```bash
# Singolo giorno (es.: 2025-06-21)
python notebooks/monitor_YYYY-MM-DD.py --date 2025-06-21

# Storico completo – genera spiaggia_kpi_storico.xlsx
python notebooks/monitor_YYYY-MM-DD.py --all
```

Output:
`notebooks/outputs/spiaggia_dashboard_<date>.xlsx` + `.pdf`
(se `--all` → `spiaggia_kpi_storico.xlsx`)

### 4.2 Monitor chiusura prenotazioni non pagate

```bash
python notebooks/monitor_closure.py --date 2025-06-22   # default = oggi
```

Output:

* `notebooks/outputs/closure_kpi_history.xlsx` (append giornaliero)
* `data/spiaggieit/snap_non_pagati/open_<date>.csv` (snapshot prenotazioni ancora aperte)

KPI tracciati:

* **Chiusure** – numero prenotazioni passate a saldo 0.
* **Rimanenza recuperata** – € incassati perché il saldo si è azzerato.
* **Pagato totale chiusure** – somma Pagato Totale finale di tali prenotazioni.

---

## 5. Workflow giornaliero consigliato

| Time  | Job                                | Script                                                 |
| ----- | ---------------------------------- | ------------------------------------------------------ |
| 00:30 | Estrai vendite Moolty              | `extract/pull_moolty.py` *(da implementare)*       |
| 00:45 | Estrai prenotazioni Spiaggie.it    | `extract/download_spiaggie.py` *(da implementare)* |
| 00:50 | Salva snapshot prenotazioni aperte | `notebooks/monitor_closure.py --date <oggi>`         |
| 00:55 | Calcola KPI incassi F-1            | `notebooks/monitor_YYYY-MM-DD.py --date <ieri>`      |
| 01:05 | Aggiorna storico KPI               | `notebooks/monitor_YYYY-MM-DD.py --all`              |

Schedulabile via **cron** o **APScheduler**.

---

## 6. Esempi rapidi

```python
import pandas as pd
# Leggi KPI storico e filtra solo weekend
kpi = pd.read_excel("notebooks/outputs/spiaggia_kpi_storico.xlsx")
print(kpi[kpi['Tipo']=='Weekend'].tail())
```

---

## 7. TODO / Roadmap

- [ ] Script `extract/` per automatizzare il download/generazione file.
- [ ] Logica di matching fuzzy prenotazioni ↔ vendite (walk-in, errori).
- [ ] Streamlit dashboard live (grafici, filtri, export).
- [ ] Alert e-mail/Slack se copertura < 90 % o gap cassa > 5 €.

Con questo README hai una guida completa per installare, eseguire e schedulare la pipeline di analisi della spiaggia. 