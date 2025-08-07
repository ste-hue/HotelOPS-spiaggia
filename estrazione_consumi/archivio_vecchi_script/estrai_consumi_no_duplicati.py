#!/usr/bin/env python3
"""
Script per estrarre i dati dai report di consumo della spiaggia senza duplicati.
Tiene traccia delle email già processate usando un hash del contenuto.
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

class EstrattoreConsumiNoDuplicati:
    def __init__(self):
        self.creds = None
        self.gmail_service = None
        self.sheets_service = None
        self.target_label = "consumi Spiaggia"
        self.spreadsheet_id = "1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"
        self.sheet_name = "Totali"
        self.processed_hashes_file = "processed_emails.json"
        self.processed_hashes = self.load_processed_hashes()

    def load_processed_hashes(self):
        """Carica gli hash delle email già processate."""
        if os.path.exists(self.processed_hashes_file):
            try:
                with open(self.processed_hashes_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_processed_hashes(self):
        """Salva gli hash delle email processate."""
        with open(self.processed_hashes_file, 'w') as f:
            json.dump(self.processed_hashes, f, indent=2)

    def authenticate(self):
        """Autentica e crea i servizi Google."""
        # Controlla token salvato
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)

        # Se non ci sono credenziali valide, richiedile
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Salva le credenziali per la prossima volta
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        # Crea i servizi
        self.gmail_service = build('gmail', 'v1', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)

    def get_label_id(self):
        """Ottieni l'ID della label."""
        try:
            results = self.gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            for label in labels:
                if label['name'] == self.target_label:
                    return label['id']

            return None
        except Exception as e:
            print(f"⚠️ Errore nel recupero della label: {e}")
            return None

    def get_emails_with_label(self, label_id=None):
        """Recupera TUTTE le email con la label specificata."""
        try:
            # Query diretta con il nome della label
            query = f'label:"{self.target_label}"'

            all_messages = []
            page_token = None

            while True:
                results = self.gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token,
                    maxResults=500  # Massimo per pagina
                ).execute()

                messages = results.get('messages', [])
                all_messages.extend(messages)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            print(f"📧 Trovate {len(all_messages)} email totali con label '{self.target_label}'")
            return all_messages

        except Exception as e:
            print(f"❌ Errore nel recupero delle email: {e}")
            return []

    def get_email_content(self, msg_id):
        """Recupera il contenuto di un'email specifica."""
        try:
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=msg_id
            ).execute()

            # Estrai le informazioni principali
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            # Trova il corpo HTML
            html_content = self.extract_html_body(message['payload'])

            return {
                'id': msg_id,
                'subject': subject,
                'date': date,
                'html': html_content
            }

        except Exception as e:
            print(f"❌ Errore nel recupero dell'email {msg_id}: {e}")
            return None

    def extract_html_body(self, payload):
        """Estrae il corpo HTML dall'email."""
        html_content = ""

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
                elif 'parts' in part:
                    # Cerca ricorsivamente nelle sottparti
                    html_content = self.extract_html_body(part)
                    if html_content:
                        break
        elif payload.get('body', {}).get('data'):
            if payload.get('mimeType') == 'text/html':
                data = payload['body']['data']
                html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return html_content

    def generate_content_hash(self, email_data):
        """Genera un hash univoco basato sul contenuto dell'email."""
        if not email_data or not email_data.get('html'):
            return None

        # Estrai i dati chiave dal report per creare un hash univoco
        soup = BeautifulSoup(email_data['html'], 'html.parser')

        # Cerca informazioni univoche del report
        unique_data = []

        # Data del report
        data_match = re.search(r'Data Report[:\s]*(\d{2}/\d{2}/\d{4})', email_data['html'])
        if data_match:
            unique_data.append(data_match.group(1))

        # Periodo Dal/Al
        periodo_dal_match = re.search(r'Periodo Dal[:\s]*([^<\n]+)', email_data['html'])
        periodo_al_match = re.search(r'Periodo Al[:\s]*([^<\n]+)', email_data['html'])
        if periodo_dal_match:
            unique_data.append(periodo_dal_match.group(1).strip())
        if periodo_al_match:
            unique_data.append(periodo_al_match.group(1).strip())

        # Totali (per essere sicuri)
        totale_incassi_match = re.search(r'Tot\. Incassi[:\s]*€\s*([\d.,]+)', email_data['html'])
        if totale_incassi_match:
            unique_data.append(totale_incassi_match.group(1))

        # Crea hash dall'insieme di dati univoci
        if unique_data:
            content_string = "|".join(unique_data)
            return hashlib.md5(content_string.encode()).hexdigest()

        # Fallback: usa l'intero HTML
        return hashlib.md5(email_data['html'].encode()).hexdigest()

    def parse_email_content(self, email_data):
        """Estrae tutti i dati dal contenuto HTML dell'email."""
        if not email_data or not email_data.get('html'):
            return None

        html_content = email_data['html']
        soup = BeautifulSoup(html_content, 'html.parser')

        # Dizionario per i risultati
        result = {
            'email_id': email_data['id'],
            'email_date': email_data['date'],
            'email_subject': email_data['subject']
        }

        # 1. ESTRAI DATI GENERALI
        # Data Report
        data_match = re.search(r'Data Report[:\s]*(\d{2}/\d{2}/\d{4})', html_content)
        if data_match:
            result['data_report'] = data_match.group(1)

        # Periodo Dal/Al
        periodo_dal_match = re.search(r'Periodo Dal[:\s]*([^<\n]+)', html_content)
        periodo_al_match = re.search(r'Periodo Al[:\s]*([^<\n]+)', html_content)
        if periodo_dal_match:
            result['periodo_dal'] = periodo_dal_match.group(1).strip()
        if periodo_al_match:
            result['periodo_al'] = periodo_al_match.group(1).strip()

        # 2. ESTRAI TOTALI
        # N. Incassi
        n_incassi_match = re.search(r'N\. Incassi[:\s]*(\d+)', html_content)
        if n_incassi_match:
            result['numero_incassi'] = int(n_incassi_match.group(1))

        # Tot. Incassi
        tot_incassi_match = re.search(r'Tot\. Incassi[:\s]*€\s*([\d.,]+)', html_content)
        if tot_incassi_match:
            value = tot_incassi_match.group(1).replace('.', '').replace(',', '.')
            result['totale_incassi_importo'] = float(value)

        # N. Scontrini
        n_scontrini_match = re.search(r'N\. Scontrini[:\s]*(\d+)', html_content)
        if n_scontrini_match:
            result['numero_scontrini'] = int(n_scontrini_match.group(1))

        # Tot. Scontrini
        tot_scontrini_match = re.search(r'Tot\. Scontrini[:\s]*€\s*([\d.,]+)', html_content)
        if tot_scontrini_match:
            value = tot_scontrini_match.group(1).replace('.', '').replace(',', '.')
            result['totale_scontrini_importo'] = float(value)

        # 3. ESTRAI VENDUTO PER PRODOTTO
        prodotti = []

        # Trova la sezione "VENDUTO PER PRODOTTO"
        venduto_section = re.search(r'VENDUTO PER PRODOTTO(.*?)(?:VENDUTO PER REPARTO|CANCELLAZIONI|$)',
                                  html_content, re.DOTALL | re.IGNORECASE)

        if venduto_section:
            section_html = venduto_section.group(1)
            section_soup = BeautifulSoup(section_html, 'html.parser')

            # Trova tutte le righe della tabella
            rows = section_soup.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 5:  # Assicurati che ci siano abbastanza colonne
                    # Salta l'header
                    if 'Prodotto' in cells[0].get_text() or 'PRODOTTO' in cells[0].get_text():
                        continue

                    try:
                        prodotto = {
                            'nome': cells[0].get_text().strip(),
                            'quantita': int(cells[1].get_text().strip()),
                            'importo': float(cells[2].get_text().strip().replace('€', '').replace('.', '').replace(',', '.')),
                            'qta_omaggio': int(cells[3].get_text().strip()),
                            'importo_omaggio': float(cells[4].get_text().strip().replace('€', '').replace('.', '').replace(',', '.'))
                        }
                        prodotti.append(prodotto)
                    except:
                        continue

        result['prodotti'] = prodotti

        # 4. ESTRAI VENDUTO PER REPARTO
        reparti = []

        # Trova la sezione "VENDUTO PER REPARTO"
        reparto_section = re.search(r'VENDUTO PER REPARTO(.*?)(?:CANCELLAZIONI|$)',
                                   html_content, re.DOTALL | re.IGNORECASE)

        if reparto_section:
            section_html = reparto_section.group(1)
            section_soup = BeautifulSoup(section_html, 'html.parser')

            rows = section_soup.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    if 'Reparto' in cells[0].get_text() or 'REPARTO' in cells[0].get_text():
                        continue

                    try:
                        reparto = {
                            'nome': cells[0].get_text().strip(),
                            'importo': float(cells[1].get_text().strip().replace('€', '').replace('.', '').replace(',', '.'))
                        }
                        reparti.append(reparto)
                    except:
                        continue

        result['reparti'] = reparti

        # 5. ESTRAI CANCELLAZIONI
        cancellazioni = []

        # Trova la sezione "CANCELLAZIONI"
        cancellazioni_section = re.search(r'CANCELLAZIONI E MODIFICHE(.*?)$',
                                        html_content, re.DOTALL | re.IGNORECASE)

        if cancellazioni_section:
            section_html = cancellazioni_section.group(1)
            section_soup = BeautifulSoup(section_html, 'html.parser')

            rows = section_soup.find_all('tr')

            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 5:
                    if 'Data/Ora' in cells[0].get_text():
                        continue

                    try:
                        cancellazione = {
                            'data_ora': cells[0].get_text().strip(),
                            'operatore': cells[1].get_text().strip(),
                            'articolo': cells[2].get_text().strip(),
                            'quantita': cells[3].get_text().strip(),
                            'importo': cells[4].get_text().strip()
                        }
                        cancellazioni.append(cancellazione)
                    except:
                        continue

        result['cancellazioni'] = cancellazioni

        return result

    def update_sheet_totali(self, all_data):
        """Aggiorna il foglio Totali evitando duplicati."""
        if not all_data:
            print("❌ Nessun dato da salvare")
            return

        # Ordina per data report (più recente prima)
        sorted_data = sorted(all_data, key=lambda x: self.parse_date(x.get('data_report', '')), reverse=True)

        # Prepara i dati per il foglio
        headers = [
            'Data Report', 'Periodo Dal', 'Periodo Al',
            'N. Incassi', 'Tot. Incassi €', 'N. Scontrini', 'Tot. Scontrini €',
            'Email ID', 'Data Email', 'Hash'
        ]

        values = [headers]

        for data in sorted_data:
            row = [
                data.get('data_report', ''),
                data.get('periodo_dal', ''),
                data.get('periodo_al', ''),
                data.get('numero_incassi', ''),
                f"€{data.get('totale_incassi_importo', 0):,.2f}".replace(',', '.'),
                data.get('numero_scontrini', ''),
                f"€{data.get('totale_scontrini_importo', 0):,.2f}".replace(',', '.'),
                data.get('email_id', ''),
                data.get('email_date', ''),
                data.get('content_hash', '')
            ]
            values.append(row)

        try:
            # Pulisci il foglio
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:AZ'
            ).execute()

            # Inserisci i nuovi dati
            body = {'values': values}
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            print(f"✅ Foglio aggiornato: {result.get('updatedCells')} celle modificate")

            # Mostra riepilogo
            print(f"\n📊 Riepilogo dati inseriti:")
            print(f"   - Totale record unici: {len(sorted_data)}")

        except Exception as e:
            print(f"❌ Errore nell'aggiornamento del foglio: {e}")

    def parse_date(self, date_str):
        """Converte la data dal formato DD/MM/YYYY a un oggetto datetime."""
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            return datetime.min

    def process_all_emails(self):
        """Processa TUTTE le email con la label evitando duplicati."""
        print("🚀 Estrazione dati consumi spiaggia (senza duplicati)")
        print("=" * 60)

        # Recupera TUTTE le email con la label
        emails = self.get_emails_with_label()

        if not emails:
            print("❌ Nessuna email trovata")
            return

        # Processa ogni email
        all_data = []
        duplicati_trovati = 0
        nuove_email = 0

        for i, msg in enumerate(emails, 1):
            print(f"\n📧 Elaborazione email {i}/{len(emails)}...")

            # Recupera il contenuto
            email_content = self.get_email_content(msg['id'])
            if not email_content:
                print("   ⚠️ Impossibile leggere il contenuto")
                continue

            # Genera hash del contenuto
            content_hash = self.generate_content_hash(email_content)
            if not content_hash:
                print("   ⚠️ Impossibile generare hash")
                continue

            # Controlla se già processata
            if content_hash in self.processed_hashes:
                print(f"   ⏭️  Email già processata (hash: {content_hash[:8]}...)")
                duplicati_trovati += 1
                continue

            # Estrai i dati
            parsed_data = self.parse_email_content(email_content)
            if parsed_data:
                parsed_data['content_hash'] = content_hash
                all_data.append(parsed_data)
                self.processed_hashes[content_hash] = {
                    'email_id': msg['id'],
                    'processed_at': datetime.now().isoformat(),
                    'data_report': parsed_data.get('data_report', '')
                }
                nuove_email += 1
                print(f"   ✅ Dati estratti - Report del {parsed_data.get('data_report', 'N/A')}")
            else:
                print("   ⚠️ Nessun dato estratto")

        # Salva gli hash aggiornati
        self.save_processed_hashes()

        print(f"\n📊 Riepilogo elaborazione:")
        print(f"   - Email totali: {len(emails)}")
        print(f"   - Nuove email processate: {nuove_email}")
        print(f"   - Duplicati evitati: {duplicati_trovati}")

        # Aggiorna il foglio Google Sheets solo con i nuovi dati
        if all_data:
            print("\n📤 Aggiornamento Google Sheets...")
            self.update_sheet_totali(all_data)
            print(f"\n✅ Processo completato! {len(all_data)} nuovi record aggiunti")
        else:
            print("\n✅ Nessun nuovo dato da aggiungere")

def main():
    estrattore = EstrattoreConsumiNoDuplicati()

    # Autentica
    print("🔐 Autenticazione in corso...")
    estrattore.authenticate()

    # Processa tutte le email
    estrattore.process_all_emails()

if __name__ == "__main__":
    main()
