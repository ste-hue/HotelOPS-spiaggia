#!/usr/bin/env python3
"""
Script per verificare quali dati sono già presenti nel Google Sheets
e capire la struttura corrente.
"""

import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def check_spreadsheet_data():
    """Verifica i dati esistenti nel foglio Google Sheets."""

    # Configurazione
    service_account_file = os.environ.get(
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        '/Users/stefanodellapietra/Desktop/Projects/Companies/INTUR/INTUR_development/HotelOPS/modules/spiaggia/estrazione_consumi/HotelOps Suite.json'
    )
    spreadsheet_id = '1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA'
    sheet_name = 'Foglio1'

    if not os.path.exists(service_account_file):
        print(f"❌ File credenziali non trovato: {service_account_file}")
        sys.exit(1)

    try:
        # Inizializza il servizio Sheets
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=credentials)

        print(f"📊 Controllo dati esistenti nello spreadsheet...")
        print(f"   ID: {spreadsheet_id}")
        print(f"   Foglio: {sheet_name}")
        print("=" * 80)

        # Recupera tutti i dati
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f'{sheet_name}!A:Z'
        ).execute()

        values = result.get('values', [])

        if not values:
            print("❌ Il foglio è vuoto")
            return

        # Mostra l'header (prima riga)
        print(f"\n📋 Header trovato ({len(values[0])} colonne):")
        print("-" * 80)
        for i, col in enumerate(values[0]):
            print(f"Colonna {chr(65+i)}: {col}")

        # Mostra statistiche
        print(f"\n📈 Statistiche:")
        print(f"   - Totale righe: {len(values)}")
        print(f"   - Righe dati: {len(values) - 1}")

        # Mostra alcune righe di esempio
        if len(values) > 1:
            print(f"\n📝 Prime 3 righe di dati:")
            print("-" * 80)

            for row_idx in range(1, min(4, len(values))):
                print(f"\nRiga {row_idx + 1}:")
                row = values[row_idx]
                for i, value in enumerate(row):
                    if i < len(values[0]):  # Solo se c'è un header corrispondente
                        print(f"   {values[0][i]}: {value}")

        # Analizza i dati
        if len(values) > 1:
            print(f"\n🔍 Analisi dati:")
            print("-" * 80)

            # Trova colonna data
            date_col = None
            for i, header in enumerate(values[0]):
                if 'data' in header.lower() and 'report' in header.lower():
                    date_col = i
                    break

            if date_col is not None:
                # Estrai tutte le date
                dates = []
                for row in values[1:]:
                    if len(row) > date_col and row[date_col]:
                        dates.append(row[date_col])

                if dates:
                    dates.sort()
                    print(f"   - Date range: {dates[0]} → {dates[-1]}")
                    print(f"   - Totale giorni: {len(set(dates))}")

            # Trova colonna totale incassi
            incassi_col = None
            for i, header in enumerate(values[0]):
                if 'tot' in header.lower() and 'incassi' in header.lower() and '€' in header:
                    incassi_col = i
                    break

            if incassi_col is not None:
                # Calcola totale
                totale = 0.0
                for row in values[1:]:
                    if len(row) > incassi_col and row[incassi_col]:
                        try:
                            # Converti da formato italiano
                            val = row[incassi_col].replace(',', '.')
                            totale += float(val)
                        except:
                            pass

                print(f"   - Totale incassi complessivo: € {totale:,.2f}")

        # Suggerimenti per miglioramenti
        print(f"\n💡 Suggerimenti per nuovi campi da aggiungere:")
        print("-" * 80)

        # Controlla quali campi mancano basandosi sull'esempio fornito
        headers_lower = [h.lower() for h in values[0]]

        suggested_fields = [
            ('Totale lordo', 'totale_lordo'),
            ('Totale ordini alla postazione', 'ordini_postazione'),
            ('Ambiente dipendenti', 'ambiente_dipendenti'),
            ('Reparti SPIAGGIA', 'reparti_spiaggia'),
            ('Reparti SPIAGGIA ALLOGGIATI', 'reparti_spiaggia_alloggiati')
        ]

        for field_name, field_key in suggested_fields:
            found = False
            for header in headers_lower:
                if field_key.replace('_', ' ') in header:
                    found = True
                    break

            if not found:
                print(f"   ➕ {field_name}")

    except HttpError as e:
        print(f"❌ Errore API: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    check_spreadsheet_data()
