#!/usr/bin/env python3
"""
Script semplice per leggere e visualizzare il contenuto delle email con label 'consumi Spiaggia'.
"""

import os
import sys
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configurazione
SERVICE_ACCOUNT_FILE = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account-key.json')
TARGET_EMAIL = 'magazzino@panoramagroup.it'
TARGET_LABEL = 'consumi Spiaggia'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Legge e mostra le email con la label specificata."""

    # Verifica che il file delle credenziali esista
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ File delle credenziali non trovato: {SERVICE_ACCOUNT_FILE}")
        print("Crea il file o imposta GOOGLE_SERVICE_ACCOUNT_FILE")
        sys.exit(1)

    try:
        # Carica le credenziali
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        # Delega all'utente target
        delegated_credentials = credentials.with_subject(TARGET_EMAIL)

        # Costruisci il servizio Gmail
        service = build('gmail', 'v1', credentials=delegated_credentials)

        print(f"✅ Connesso a Gmail per {TARGET_EMAIL}")

        # Trova l'ID della label
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        label_id = None
        for label in labels:
            if label['name'] == TARGET_LABEL:
                label_id = label['id']
                print(f"✅ Trovata label '{TARGET_LABEL}' con ID: {label_id}")
                break

        if not label_id:
            print(f"❌ Label '{TARGET_LABEL}' non trovata")
            print("\nLabel disponibili:")
            for label in labels:
                print(f"  - {label['name']}")
            return

        # Cerca email dal mittente specifico
        sender_email = 'no-reply@pinapp.pro'
        query = f'from:{sender_email}'
        print(f"\n🔍 Cerco email da: {sender_email}")

        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=10
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print(f"❌ Nessuna email trovata da {sender_email}")

            # Proviamo a cercare senza filtri per vedere cosa c'è
            print("\n🔍 Cerco le ultime 10 email senza filtri...")
            results = service.users().messages().list(
                userId='me',
                maxResults=10
            ).execute()

            messages = results.get('messages', [])
            if messages:
                print(f"\n📧 Trovate {len(messages)} email recenti. Mostro mittenti:")
                for msg_id in messages[:5]:
                    msg = service.users().messages().get(userId='me', id=msg_id['id']).execute()
                    headers = msg['payload'].get('headers', [])
                    for header in headers:
                        if header['name'] == 'From':
                            print(f"  - {header['value']}")
                            break
            return

        print(f"\n📧 Trovate {len(messages)} email da {sender_email}. Analizzo le prime 3...\n")

        # Analizza ogni email
        for i, message in enumerate(messages[:3], 1):
            print(f"\n{'='*80}")
            print(f"EMAIL {i}")
            print('='*80)

            # Recupera i dettagli dell'email
            msg = service.users().messages().get(
                userId='me',
                id=message['id']
            ).execute()

            # Estrai headers
            headers = msg['payload'].get('headers', [])
            headers_dict = {}
            for header in headers:
                headers_dict[header['name']] = header['value']
                if header['name'] in ['Subject', 'From', 'Date']:
                    print(f"{header['name']}: {header['value']}")

            # Estrai il corpo
            body = extract_body(msg['payload'])

            if body:
                # Determina il tipo
                is_html = '<html' in body.lower() or '<table' in body.lower()
                print(f"\nTipo contenuto: {'HTML' if is_html else 'Testo'}")
                print(f"Lunghezza: {len(body)} caratteri")

                # Mostra i primi 1000 caratteri
                print(f"\nContenuto (primi 1000 caratteri):")
                print("-" * 40)
                print(body[:1000])

                # Se è HTML, mostra anche il testo puro
                if is_html:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(body, 'html.parser')
                    text = soup.get_text()
                    print(f"\n\nTesto estratto da HTML (primi 1000 caratteri):")
                    print("-" * 40)
                    print(text[:1000])

                    # Cerca tabelle
                    tables = soup.find_all('table')
                    if tables:
                        print(f"\n\n🔍 Trovate {len(tables)} tabelle")

                        # Cerca la tabella principale con i dati
                        for j, table in enumerate(tables, 1):
                            rows = table.find_all('tr')
                            if len(rows) > 5:  # Tabella con dati significativi
                                print(f"\nTabella {j} ({len(rows)} righe):")
                                print("-" * 80)

                                # Mostra tutte le righe per capire la struttura
                                for row in rows:
                                    cells = row.find_all(['td', 'th'])
                                    if cells and len(cells) >= 2:
                                        # Estrai il testo e formatta
                                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                                        if len(cell_texts) >= 3:
                                            # Formato: Descrizione | Numero ordini | Totale | Media
                                            print(f"  {cell_texts[0]:<40} | {cell_texts[1]:>12} | {cell_texts[2]:>12}")
                                        elif len(cell_texts) == 2:
                                            # Formato: Chiave | Valore
                                            print(f"  {cell_texts[0]:<40} | {cell_texts[1]:>12}")

                                # Estrai dati chiave
                                print("\n📊 Dati chiave estratti:")
                                for row in rows:
                                    cells = row.find_all(['td', 'th'])
                                    if cells and len(cells) >= 2:
                                        key = cells[0].get_text(strip=True).lower()
                                        value = cells[1].get_text(strip=True)

                                        # Cerca pattern specifici
                                        if any(term in key for term in ['totale incassi', 'totale scontrini', 'totale ordini']):
                                            print(f"    - {cells[0].get_text(strip=True)}: {value}")
                                        elif 'data' in key or 'dal' in key:
                                            print(f"    - Periodo: {value}")

                # Salva un esempio completo
                if i == 1:
                    filename = f"esempio_email_{message['id'][:8]}.{'html' if is_html else 'txt'}"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(body)
                    print(f"\n✅ Email di esempio salvata in: {filename}")

                    # Salva anche una versione con i dati estratti
                    if is_html:
                        data_filename = f"dati_estratti_{message['id'][:8]}.txt"
                        with open(data_filename, 'w', encoding='utf-8') as f:
                            f.write(f"DATI ESTRATTI DA: {headers_dict.get('Subject', 'N/A')}\n")
                            f.write(f"DATA: {headers_dict.get('Date', 'N/A')}\n")
                            f.write("="*80 + "\n\n")
                            f.write(text)
                        print(f"✅ Dati estratti salvati in: {data_filename}")

    except HttpError as e:
        print(f"❌ Errore API: {e}")
        if e.resp.status == 403:
            print("\nPossibili cause:")
            print("- Il service account non ha la delega per leggere Gmail")
            print("- Gmail API non è abilitata nel progetto")
            print("- Permessi insufficienti")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

def extract_body(payload):
    """Estrae il corpo dell'email dal payload."""
    body = ''

    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/html':
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                break
            elif part['mimeType'] == 'text/plain' and not body:
                data = part['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        if payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

    return body

if __name__ == '__main__':
    main()
