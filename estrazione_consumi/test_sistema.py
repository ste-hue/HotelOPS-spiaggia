#!/usr/bin/env python3
"""
Test del sistema con debug dettagliato per diagnosticare problemi di autenticazione.
"""

import os
import json
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def test_authentication():
    """Test dettagliato dell'autenticazione."""
    print("🧪 TEST SISTEMA CONSUMI - DEBUG DETTAGLIATO")
    print("=" * 60)

    # 1. Verifica Service Account
    print("\n1️⃣ VERIFICA SERVICE ACCOUNT")
    print("-" * 30)

    sa_paths = [
        "HotelOps Suite.json",
        os.path.expanduser("~/HotelOps Suite.json"),
        os.path.expanduser("~/Documents/HotelOps Suite.json"),
        os.path.expanduser("~/Desktop/HotelOps Suite.json")
    ]

    sa_file = None
    for path in sa_paths:
        if os.path.exists(path):
            sa_file = path
            break

    if not sa_file:
        print("❌ Service account file non trovato!")
        return

    print(f"✅ Service account trovato: {sa_file}")

    # Leggi info dal service account
    with open(sa_file, 'r') as f:
        sa_info = json.load(f)

    print(f"   • Email: {sa_info.get('client_email')}")
    print(f"   • ID: {sa_info.get('client_id')}")
    print(f"   • Project: {sa_info.get('project_id')}")

    # 2. Test Google Sheets (senza delega)
    print("\n2️⃣ TEST GOOGLE SHEETS API")
    print("-" * 30)

    try:
        credentials = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )

        sheets_service = build('sheets', 'v4', credentials=credentials)

        # Test lettura spreadsheet
        spreadsheet_id = "1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"

        result = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()

        print(f"✅ Accesso Google Sheets OK")
        print(f"   • Titolo: {result.get('properties', {}).get('title')}")
        print(f"   • Fogli:")
        for sheet in result.get('sheets', []):
            print(f"     - {sheet['properties']['title']}")

    except Exception as e:
        print(f"❌ Errore Sheets API: {e}")

    # 3. Test Gmail con delega
    print("\n3️⃣ TEST GMAIL API CON DELEGA")
    print("-" * 30)

    target_email = "magazzino@panoramagroup.it"
    print(f"Target email: {target_email}")

    try:
        # Prima prova senza delega per vedere se funziona
        print("\n   a) Test senza delega...")
        credentials = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )

        gmail_service = build('gmail', 'v1', credentials=credentials)

        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            print(f"   ✅ Accesso diretto funziona: {profile.get('emailAddress')}")
        except Exception as e:
            print(f"   ❌ Accesso diretto fallito (normale): {str(e)[:100]}...")

    except Exception as e:
        print(f"   ❌ Errore creazione servizio: {e}")

    try:
        # Ora prova con delega
        print("\n   b) Test con delega domain-wide...")
        credentials = service_account.Credentials.from_service_account_file(
            sa_file,
            scopes=['https://www.googleapis.com/auth/gmail.readonly']
        )

        # Applica delega
        delegated_credentials = credentials.with_subject(target_email)

        gmail_service = build('gmail', 'v1', credentials=delegated_credentials)

        # Test profilo
        try:
            profile = gmail_service.users().getProfile(userId='me').execute()
            print(f"   ✅ Delega funzionante! Email: {profile.get('emailAddress')}")
            print(f"   • Messages total: {profile.get('messagesTotal')}")
            print(f"   • Threads total: {profile.get('threadsTotal')}")
        except HttpError as e:
            error_details = json.loads(e.content.decode('utf-8'))
            print(f"   ❌ Errore HTTP {e.resp.status}:")
            print(f"      {error_details.get('error', {}).get('message', str(error_details))}")

            if 'unauthorized_client' in str(e):
                print("\n   ⚠️  POSSIBILI SOLUZIONI:")
                print("   1. Verifica che la delega domain-wide sia configurata in Google Admin")
                print("   2. Assicurati che l'ID client sia: 114448341733699832547")
                print("   3. Gli scope devono includere: https://www.googleapis.com/auth/gmail.readonly")
                print("   4. Potrebbe servire qualche minuto per la propagazione")

    except Exception as e:
        print(f"   ❌ Errore generale: {type(e).__name__}: {str(e)}")

    # 4. Test ricerca email con label
    print("\n4️⃣ TEST RICERCA EMAIL")
    print("-" * 30)

    try:
        # Se la delega funziona, prova a cercare email
        if 'gmail_service' in locals():
            query = 'label:"consumi Spiaggia"'
            print(f"Query: {query}")

            results = gmail_service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5
            ).execute()

            messages = results.get('messages', [])
            print(f"✅ Email trovate: {len(messages)}")

            if messages:
                print("   Ultime 5 email:")
                for msg in messages[:5]:
                    try:
                        message = gmail_service.users().messages().get(
                            userId='me',
                            id=msg['id']
                        ).execute()

                        headers = message['payload'].get('headers', [])
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

                        print(f"   • {date[:30]}: {subject[:50]}...")
                    except:
                        print(f"   • Email {msg['id']}: (errore lettura)")

    except Exception as e:
        print(f"❌ Impossibile cercare email: {str(e)[:200]}...")

    # 5. Verifica database locale
    print("\n5️⃣ DATABASE LOCALE")
    print("-" * 30)

    if os.path.exists("database_consumi.json"):
        with open("database_consumi.json", 'r') as f:
            db = json.load(f)

        print("✅ Database trovato:")
        print(f"   • Email processate: {len(db.get('processed_emails', {}))}")
        print(f"   • Record totali: {len(db.get('consumi_data', []))}")
        print(f"   • Ultimo aggiornamento: {db.get('last_update', 'Mai')}")
    else:
        print("ℹ️  Database non ancora creato (verrà creato al primo utilizzo)")

    print("\n" + "=" * 60)
    print("TEST COMPLETATO")
    print("=" * 60)


if __name__ == "__main__":
    test_authentication()
