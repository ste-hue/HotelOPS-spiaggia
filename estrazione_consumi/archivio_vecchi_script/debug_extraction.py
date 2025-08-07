#!/usr/bin/env python3
"""
Debug script per analizzare l'estrazione dei dati dalle email
"""

import os
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build

class DebugExtractor:
    def __init__(self):
        self.service_account_file = 'HotelOps Suite.json'
        self.target_email = 'magazzino@panoramagroup.it'
        self._initialize_services()

    def _initialize_services(self):
        """Inizializza i servizi Google API."""
        try:
            gmail_credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            gmail_delegated = gmail_credentials.with_subject(self.target_email)
            self.gmail_service = build('gmail', 'v1', credentials=gmail_delegated)
            print("✅ Servizi inizializzati")
        except Exception as e:
            print(f"❌ Errore: {e}")
            raise

    def get_label_id(self, label_name):
        """Ottieni l'ID di una label Gmail."""
        try:
            results = self.gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']
            return None
        except Exception as e:
            print(f"❌ Errore nel recupero label: {e}")
            return None

    def get_first_email(self):
        """Recupera la prima email con label 'consumi Spiaggia'."""
        label_id = self.get_label_id('consumi Spiaggia')
        if not label_id:
            print("⚠️  Label 'consumi Spiaggia' non trovata")
            return None

        try:
            results = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=1
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                print("⚠️  Nessuna email trovata")
                return None

            msg_data = self.gmail_service.users().messages().get(
                userId='me',
                id=messages[0]['id']
            ).execute()

            return msg_data

        except Exception as e:
            print(f"❌ Errore nel recupero email: {e}")
            return None

    def extract_body(self, msg_data):
        """Estrae il corpo dell'email."""
        body = ""

        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
        elif msg_data['payload']['body'].get('data'):
            body = base64.urlsafe_b64decode(
                msg_data['payload']['body']['data']
            ).decode('utf-8', errors='ignore')

        return body

    def debug_sections(self, body):
        """Analizza le varie sezioni del body."""
        print("\n📊 ANALISI SEZIONI")
        print("=" * 60)

        # Cerca le varie sezioni
        sections = {
            'Totali': body.find('Totali'),
            'Addetti Cassa': body.find('Addetti Cassa'),
            'Ambienti': body.find('Ambienti'),
            'Movimentazione': body.find('Movimentazione'),
            'Reparti': body.find('Reparti'),
            'Prodotti': body.find('Prodotti'),
            'Varianti': body.find('Varianti')
        }

        for section, pos in sections.items():
            if pos != -1:
                print(f"✅ {section}: trovata alla posizione {pos}")
            else:
                print(f"❌ {section}: NON TROVATA")

        # Analizza sezione Reparti
        print("\n📊 SEZIONE REPARTI")
        print("-" * 40)

        reparti_start = body.find('RepartiReparto')
        if reparti_start == -1:
            reparti_start = body.find('Reparti')

        if reparti_start != -1:
            # Trova fine sezione
            prodotti_start = body.find('ProdottiProdotto', reparti_start)
            if prodotti_start == -1:
                prodotti_start = body.find('Prodotti', reparti_start + 10)

            if prodotti_start != -1:
                reparti_text = body[reparti_start:prodotti_start]
            else:
                reparti_text = body[reparti_start:reparti_start + 1000]

            print(f"Lunghezza sezione: {len(reparti_text)} caratteri")
            print("\nPrimi 500 caratteri:")
            print(repr(reparti_text[:500]))

            # Conta occorrenze di €
            euro_count = reparti_text.count('€')
            print(f"\nNumero di € trovati: {euro_count}")

            # Mostra le prime righe con €
            lines = reparti_text.split('€')
            print("\nPrime 3 righe con €:")
            for i, line in enumerate(lines[:3]):
                print(f"  Riga {i}: {repr(line[-50:])}")

        # Analizza sezione Prodotti
        print("\n📊 SEZIONE PRODOTTI")
        print("-" * 40)

        prodotti_start = body.find('ProdottiProdotto')
        if prodotti_start == -1:
            prodotti_start = body.find('Prodotti')
            if prodotti_start != -1:
                # Skip fino a dopo l'header
                temp_start = body.find('Totale', prodotti_start)
                if temp_start != -1 and temp_start - prodotti_start < 100:
                    prodotti_start = temp_start + 10

        if prodotti_start != -1:
            # Trova fine sezione
            varianti_start = body.find('Varianti', prodotti_start)
            totali_start = body.find('Totali:', prodotti_start)

            end_pos = min(x for x in [varianti_start, totali_start, prodotti_start + 2000] if x > prodotti_start)
            prodotti_text = body[prodotti_start:end_pos]

            print(f"Lunghezza sezione: {len(prodotti_text)} caratteri")
            print("\nPrimi 800 caratteri:")
            print(repr(prodotti_text[:800]))

            # Conta occorrenze di €
            euro_count = prodotti_text.count('€')
            print(f"\nNumero di € trovati: {euro_count}")

            # Mostra pattern di prodotti
            print("\nPattern di prodotti trovati:")
            import re
            # Cerca pattern tipo "pz" seguito da numeri
            pz_matches = re.findall(r'pz(\d+)(\d+)(\d+)', prodotti_text[:500])
            for i, match in enumerate(pz_matches[:5]):
                print(f"  Pattern {i}: pz{match[0]}{match[1]}{match[2]}")

    def analyze_email_structure(self):
        """Analizza la struttura completa di una email."""
        print("🔍 DEBUG ESTRAZIONE DATI EMAIL")
        print("=" * 60)

        # Recupera prima email
        msg_data = self.get_first_email()
        if not msg_data:
            return

        # Info email
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Senza oggetto')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

        print(f"\n📧 Email analizzata:")
        print(f"   Oggetto: {subject}")
        print(f"   Data: {date}")

        # Estrai body
        body = self.extract_body(msg_data)
        print(f"\n📄 Corpo email:")
        print(f"   Lunghezza totale: {len(body)} caratteri")

        # Salva body per analisi
        with open('debug_email_body.txt', 'w', encoding='utf-8') as f:
            f.write(body)
        print("   ✅ Body salvato in 'debug_email_body.txt'")

        # Analizza sezioni
        self.debug_sections(body)

        # Mostra caratteri speciali
        print("\n🔤 CARATTERI SPECIALI")
        print("-" * 40)

        # Cerca tab, newline, etc
        special_chars = {
            '\\t (tab)': body.count('\t'),
            '\\n (newline)': body.count('\n'),
            '\\r (carriage return)': body.count('\r'),
            'Spazi': body.count(' ')
        }

        for char, count in special_chars.items():
            print(f"  {char}: {count}")

        # Analizza formato dati
        print("\n📐 FORMATO DATI")
        print("-" * 40)

        # Cerca se ci sono tab tra i campi
        sample = body[body.find('APERITIVI E VINI'):body.find('APERITIVI E VINI') + 100] if 'APERITIVI E VINI' in body else ''
        if sample:
            print("Esempio riga APERITIVI E VINI:")
            print(f"  Raw: {repr(sample)}")
            has_tab = '\t' in sample
            has_newline = '\n' in sample
            print(f"  Contiene tab: {has_tab}")
            print(f"  Contiene newline: {has_newline}")

if __name__ == "__main__":
    debug = DebugExtractor()
    debug.analyze_email_structure()
