import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd

# Root directory (module directory)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MOOLTY_PROD_DIR = DATA_DIR / "moolty" / "prodotti"
MOOLTY_TOT_DIR = DATA_DIR / "moolty" / "totali"
SPIAGGIEIT_DIR = DATA_DIR / "spiaggieit"

PRENOTAZIONI_CSV = SPIAGGIEIT_DIR / "prenotazioni_online_full.csv"

###############################################################################
# Helper functions
###############################################################################

def _date_to_str(date: datetime) -> str:
    """Return date as YYYY-MM-DD string."""
    return date.strftime("%Y-%m-%d")


def load_totale_scontrini(date: datetime) -> float:
    """Return the value of "Totale scontrini" for the given date.

    Handles varianti di layout (skiprows=1, col names dynamic).
    """
    file_path = MOOLTY_TOT_DIR / f"totali_{_date_to_str(date)}.xlsx"
    if not file_path.exists():
        print(f"[WARN] File totali non trovato: {file_path}")
        return 0.0

    df = pd.read_excel(file_path, engine="openpyxl", sheet_name=0, skiprows=1)
    df.columns = [str(c).strip() for c in df.columns]

    descr_col = next((c for c in df.columns if "descr" in c.lower()), df.columns[0])
    total_col = next((c for c in df.columns if "totale" == c.lower() or c.lower().startswith("totale")), None)
    if total_col is None:
        print(f"[WARN] Colonna Totale non trovata in {file_path}")
        return 0.0

    ds = df[descr_col].astype(str).str.lower()
    mask = ds.str.contains("totale") & ds.str.contains("scontrini")
    if not mask.any():
        print(f"[WARN] Riga 'Totale scontrini' non trovata in {file_path}")
        return 0.0

    val = df.loc[mask, total_col].iloc[0]
    return float(val)


def load_vendite(date: datetime, only_spiaggia: bool = False) -> float:
    """Return sum of column Totale.

    If only_spiaggia True, filter rows whose categoria contains 'SPIAGGIA'.
    """
    file_path = MOOLTY_PROD_DIR / f"prodotti_{_date_to_str(date)}.xlsx"
    if not file_path.exists():
        print(f"[WARN] File prodotti non trovato: {file_path}")
        return 0.0

    df = pd.read_excel(file_path, engine="openpyxl", sheet_name=0, skiprows=1)
    df.columns = [str(c).strip() for c in df.columns]

    cat_col = next((c for c in df.columns if "categoria" in c.lower()), None)
    total_col = next((c for c in df.columns if c.lower().startswith("totale")), None)
    if total_col is None:
        print(f"[WARN] Colonna Totale non trovata in {file_path}")
        return 0.0

    if only_spiaggia and cat_col is not None:
        df = df[df[cat_col].astype(str).str.contains("spiaggia", case=False, na=False)]
    return float(df[total_col].sum())


def load_prenotazioni_df() -> pd.DataFrame:
    if not PRENOTAZIONI_CSV.exists():
        raise FileNotFoundError("Prenotazioni CSV non trovato")

    df = pd.read_csv(PRENOTAZIONI_CSV, sep=";", skiprows=1, decimal=",", dtype=str)

    if "Data Prenotazione" not in df.columns and "Data Creazione" in df.columns:
        df["Data Prenotazione"] = df["Data Creazione"]

    for col in ["Data inizio", "Data Fine", "Data Prenotazione"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    for col in ["Pagato Totale", "Rimanenza"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .astype(float)
            )
    return df


def calc_prenotazioni_metrics(df: pd.DataFrame, date: datetime):
    date_ts = pd.Timestamp(date)
    mask_range = (df["Data inizio"] <= date_ts) & (df["Data Fine"] >= date_ts)
    df_range = df[mask_range]

    mask_book = df["Data Prenotazione"] == date_ts
    df_book = df[mask_book]

    return {
        "count_range": len(df_range),
        "paid_range": df_range["Pagato Totale"].sum(),
        "count_book": len(df_book),
        "paid_book": df_book["Pagato Totale"].sum(),
        "non_paid_sum": df_range.loc[df_range["Rimanenza"] > 0, "Rimanenza"].sum(),
        "non_paid_count": (df_range["Rimanenza"] > 0).sum(),
    }


def human(val: float) -> str:
    return f"€ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

###############################################################################
# CLI
###############################################################################

def main():
    parser = argparse.ArgumentParser(description="Analizza gap cassa-vendite-prenotazioni per un giorno")
    parser.add_argument("--date", required=True, help="Data da analizzare YYYY-MM-DD")
    parser.add_argument("--allprod", action="store_true", help="Usa tutte le vendite prodotti (non solo SPIAGGIA)")
    args = parser.parse_args()

    try:
        date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print("Formato data non valido")
        return

    tot_cassa = load_totale_scontrini(date)
    vendite = load_vendite(date, only_spiaggia=not args.allprod)

    df_pren = load_prenotazioni_df()
    metrics = calc_prenotazioni_metrics(df_pren, date)

    gap1 = tot_cassa - vendite
    gap2_range = gap1 - metrics["paid_range"]

    print("\nReport", args.date)
    print("Cassa tot scontrini:", human(tot_cassa))
    label_v = "Vendite (tutti reparti)" if args.allprod else "Vendite SPIAGGIA"
    print(f"{label_v}:", human(vendite))
    print("Gap cassa - vendite:", human(gap1))
    print()
    print("Prenotazioni nel giorno:", metrics["count_range"], "Pagato:", human(metrics["paid_range"]))
    print("Prenotazioni data pren.:", metrics["count_book"], "Pagato:", human(metrics["paid_book"]))
    print("Non pagato residuo:", metrics["non_paid_count"], human(metrics["non_paid_sum"]))
    print("Gap dopo online pagato (range):", human(gap2_range))

if __name__ == "__main__":
    main() 