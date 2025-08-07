#!/usr/bin/env python3
"""
Script per rimuovere i duplicati dal foglio Google Sheets e riprocessare tutto.
"""

import pickle
import os
import re
import json
import hashlib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime
from bs4 import BeautifulSoup
import base64
from collections import defaultdict

# Scopes necessari
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

class RimuoviDuplicati:
    def __init__(self):
        self.creds = None
        self.gmail_service = None
        self.sheets_service = None
        self.target_label = "consumi Spiaggia"
        self.spreadsheet_id = "1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"
        self.sheet_name = "Totali"
        self.base_path = "/Users/stefanodellapietra/Documents"
        self.processed_hashes_file = os.path.join(self.base_path, "processed_emails.json")

    def authenticate(self):
        """Autentica e crea i servizi Google."""
        # Controlla token salvato
        token_path = os.path.join(self.base_path, 'token.pickle')
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                self.creds = pickle.load(token)

        # Se non ci sono credenziali valide, richiedile
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                credentials_path = os.path.join(self.base_path, 'credentials.json')
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Salva le credenziali per la prossima volta
            with open(token_path, 'wb') as token:
                pickle.dump(self.creds, token)

        # Crea i servizi
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)

    def reset_processed_emails(self):
        """Resetta il file degli hash processati."""
        if os.path.exists(self.processed_hashes_file):
            print(f"🗑️  Rimuovo il file {self.processed_hashes_file}...")
            os.remove(self.processed_hashes_file)
            print("✅ File rimosso")
        else:
            print("ℹ️  Nessun file di hash da rimuovere")

    def clear_google_sheet(self):
        """Pulisce completamente il foglio Google Sheets."""
        try:
            print(f"🧹 Pulizia del foglio '{self.sheet_name}'...")

            # Prima ottieni le dimensioni del foglio
            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            # Trova il foglio specifico
            sheet_info = None
            for sheet in sheet_metadata.get('sheets', []):
                if sheet['properties']['title'] == self.sheet_name:
                    sheet_info = sheet['properties']
                    break

            if sheet_info:
                rows = sheet_info.get('gridProperties', {}).get('rowCount', 1000)
                cols = sheet_info.get('gridProperties', {}).get('columnCount', 26)

                # Pulisci tutto il contenuto
                self.sheets_service.spreadsheets().values().clear(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{self.sheet_name}!A1:{self._get_column_letter(cols)}{rows}'
                ).execute()

                print(f"✅ Foglio pulito completamente")
            else:
                print(f"⚠️  Foglio '{self.sheet_name}' non trovato")

        except Exception as e:
            print(f"❌ Errore nella pulizia del foglio: {e}")

    def _get_column_letter(self, col_num):
        """Converte un numero di colonna in lettera (1=A, 27=AA, etc)."""
        result = ""
        while col_num > 0:
            col_num -= 1
            result = chr(col_num % 26 + ord('A')) + result
            col_num //= 26
        return result

    def check_current_data(self):
        """Controlla i dati attuali nel foglio."""
        try:
            print("\n📊 Controllo dati attuali nel foglio...")

            # Leggi i dati attuali
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:J'
            ).execute()

            values = result.get('values', [])

            if not values:
                print("   Il foglio è vuoto")
                return

            # Salta l'header
            data_rows = values[1:] if len(values) > 1 else []

            if not data_rows:
                print("   Nessun dato presente (solo header)")
                return

            print(f"   Totale righe di dati: {len(data_rows)}")

            # Trova duplicati
            seen = {}
            duplicates = []

            for i, row in enumerate(data_rows):
                if len(row) >= 3:  # Almeno data report, periodo dal, periodo al
                    # Crea una chiave unica
                    key = f"{row[0]}|{row[1] if len(row) > 1 else ''}|{row[2] if len(row) > 2 else ''}"

                    if key in seen:
                        duplicates.append({
                            'row_num': i + 2,  # +2 perché partiamo da riga 2 (dopo header)
                            'data': row[0] if row else '',
                            'first_occurrence': seen[key]
                        })
                    else:
                        seen[key] = i + 2

            if duplicates:
                print(f"\n⚠️  Trovati {len(duplicates)} duplicati:")
                for dup in duplicates[:10]:  # Mostra solo i primi 10
                    print(f"   - Riga {dup['row_num']}: {dup['data']} (prima occorrenza: riga {dup['first_occurrence']})")
                if len(duplicates) > 10:
                    print(f"   ... e altri {len(duplicates) - 10} duplicati")
            else:
                print("   ✅ Nessun duplicato trovato")

        except Exception as e:
            print(f"❌ Errore nel controllo dei dati: {e}")

def main():
    print("🧹 PULIZIA DUPLICATI E RESET SISTEMA")
    print("=" * 60)

    rimuovi = RimuoviDuplicati()

    # Autentica
    print("\n🔐 Autenticazione in corso...")
    rimuovi.authenticate()

    # Controlla situazione attuale
    rimuovi.check_current_data()

    # Chiedi conferma
    print("\n⚠️  ATTENZIONE: Questa operazione:")
    print("   1. Cancellerà TUTTI i dati dal foglio Google Sheets")
    print("   2. Resetterà la memoria delle email processate")
    print("   3. Permetterà di riprocessare tutto da zero")

    conferma = input("\n❓ Vuoi procedere? (s/N): ").strip().lower()

    if conferma != 's':
        print("\n❌ Operazione annullata")
        return

    # Procedi con la pulizia
    print("\n🚀 Inizio pulizia...")

    # 1. Pulisci il foglio Google Sheets
    rimuovi.clear_google_sheet()

    # 2. Resetta il file degli hash
    rimuovi.reset_processed_emails()

    print("\n✅ Pulizia completata!")
    print("\n📌 Prossimi passi:")
    print("   1. Esegui: python3 estrai_consumi_spiaggia.py")
    print("   2. Tutti i dati verranno riprocessati senza duplicati")
    print("   3. D'ora in poi, solo le nuove email verranno aggiunte")

if __name__ == "__main__":
    main()
