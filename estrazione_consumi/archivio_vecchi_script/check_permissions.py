#!/usr/bin/env python3
"""
Script per verificare i permessi del service account e diagnosticare problemi di autenticazione.
"""

import os
import sys
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def check_service_account_file(filepath):
    """Verifica e mostra informazioni sul file del service account."""
    print("🔍 Verifica Service Account")
    print("=" * 80)

    if not os.path.exists(filepath):
        print(f"❌ File non trovato: {filepath}")
        return None

    try:
        with open(filepath, 'r') as f:
            sa_info = json.load(f)

        print(f"✅ File trovato: {filepath}")
        print(f"📧 Service Account Email: {sa_info.get('client_email', 'N/A')}")
        print(f"🆔 Project ID: {sa_info.get('project_id', 'N/A')}")
        print(f"🔑 Private Key ID: {sa_info.get('private_key_id', 'N/A')[:8]}...")

        return sa_info
    except Exception as e:
        print(f"❌ Errore nel leggere il file: {e}")
        return None

def test_sheets_api(service_account_file, spreadsheet_id):
    """Testa l'accesso a Google Sheets API."""
    print("\n📊 Test Google Sheets API")
    print("=" * 80)

    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        service = build('sheets', 'v4', credentials=credentials)

        # Prova a leggere le proprietà dello spreadsheet
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()

        print(f"✅ Accesso a Sheets API funzionante")
        print(f"📄 Titolo Spreadsheet: {spreadsheet.get('properties', {}).get('title', 'N/A')}")

        # Mostra i fogli disponibili
        sheets = spreadsheet.get('sheets', [])
        print(f"\n📑 Fogli disponibili:")
        for sheet in sheets:
            sheet_props = sheet.get('properties', {})
            print(f"   - {sheet_props.get('title')} (ID: {sheet_props.get('sheetId')})")

        return True

    except HttpError as e:
        print(f"❌ Errore HTTP: {e}")
        if e.resp.status == 403:
            print("   ⚠️  Il service account non ha accesso allo spreadsheet")
            print("   💡 Soluzione: Condividi lo spreadsheet con l'email del service account")
        elif e.resp.status == 404:
            print("   ⚠️  Spreadsheet non trovato")
        return False
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

def test_gmail_api(service_account_file, delegated_email):
    """Testa l'accesso a Gmail API con delega."""
    print(f"\n📧 Test Gmail API (con delega a {delegated_email})")
    print("=" * 80)

    try:
        # Prima prova senza delega
        print("\n1️⃣ Test senza delega:")
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )

        service = build('gmail', 'v1', credentials=credentials)

        try:
            # Questo dovrebbe fallire perché un service account non può accedere a Gmail senza delega
            profile = service.users().getProfile(userId='me').execute()
            print(f"   ✅ Accesso diretto funzionante (inaspettato)")
        except Exception as e:
            print(f"   ℹ️  Accesso diretto non disponibile (normale per service account)")

        # Ora prova con delega
        print(f"\n2️⃣ Test con delega a {delegated_email}:")
        delegated_credentials = credentials.with_subject(delegated_email)
        delegated_service = build('gmail', 'v1', credentials=delegated_credentials)

        profile = delegated_service.users().getProfile(userId='me').execute()
        print(f"   ✅ Delega funzionante!")
        print(f"   📧 Email: {profile.get('emailAddress')}")
        print(f"   📨 Messaggi totali: {profile.get('messagesTotal', 0)}")

        # Prova a listare le label
        labels = delegated_service.users().labels().list(userId='me').execute()
        print(f"\n   🏷️  Label trovate: {len(labels.get('labels', []))}")

        # Cerca la label specifica
        target_label = 'consumi Spiaggia'
        for label in labels.get('labels', []):
            if label['name'] == target_label:
                print(f"   ✅ Label '{target_label}' trovata (ID: {label['id']})")
                break

        return True

    except HttpError as e:
        print(f"❌ Errore HTTP: {e}")
        if e.resp.status == 403:
            print("\n   ⚠️  Problemi di autorizzazione. Possibili cause:")
            print("   1. Domain-wide delegation non configurata")
            print("   2. Scopes non autorizzati nella delega")
            print("   3. Email di delega non valida")
            print("\n   💡 Soluzione:")
            print("   1. Vai su Google Admin Console")
            print("   2. Sicurezza → Controllo accesso e dati → Controlli API")
            print("   3. Gestisci delega a livello di dominio")
            print("   4. Aggiungi il Client ID del service account con scope:")
            print("      https://www.googleapis.com/auth/gmail.readonly")
        return False
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

def main():
    """Funzione principale."""
    print("🔧 Diagnostica Service Account per Estrazione Consumi")
    print("=" * 80)

    # Configurazione
    service_account_file = os.environ.get(
        'GOOGLE_SERVICE_ACCOUNT_FILE',
        '/Users/stefanodellapietra/Desktop/Projects/Companies/INTUR/INTUR_development/HotelOPS/modules/spiaggia/estrazione_consumi/HotelOps Suite.json'
    )
    spreadsheet_id = '1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA'
    delegated_email = 'magazzino@panoramagroup.it'

    # Verifica il file
    sa_info = check_service_account_file(service_account_file)
    if not sa_info:
        sys.exit(1)

    # Test Sheets API
    sheets_ok = test_sheets_api(service_account_file, spreadsheet_id)

    # Test Gmail API
    gmail_ok = test_gmail_api(service_account_file, delegated_email)

    # Riepilogo
    print("\n📋 RIEPILOGO")
    print("=" * 80)
    print(f"Service Account Email: {sa_info.get('client_email', 'N/A')}")
    print(f"Google Sheets API: {'✅ OK' if sheets_ok else '❌ ERRORE'}")
    print(f"Gmail API con delega: {'✅ OK' if gmail_ok else '❌ ERRORE'}")

    if not sheets_ok:
        print("\n⚠️  Per risolvere i problemi con Sheets:")
        print(f"   1. Vai su https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print(f"   2. Clicca su 'Condividi'")
        print(f"   3. Aggiungi: {sa_info.get('client_email')}")
        print(f"   4. Dai permessi di 'Editor'")

    if not gmail_ok:
        print("\n⚠️  Per risolvere i problemi con Gmail:")
        print(f"   1. Trova il Client ID nel file del service account")
        print(f"      Client ID: {sa_info.get('client_id', 'Non trovato')}")
        print(f"   2. Configura la delega in Google Admin Console")
        print(f"   3. Autorizza lo scope: https://www.googleapis.com/auth/gmail.readonly")

if __name__ == '__main__':
    main()
