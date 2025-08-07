#!/usr/bin/env python3
"""
Estrattore Consumi Spiaggia V2 - Versione semplificata e funzionante
Estrae TUTTI i dati rilevanti dalle email HTML
"""

import os
import base64
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from bs4 import BeautifulSoup


class ConsumiExtractorV2:
    """Estrattore semplificato per i dati dei consumi spiaggia."""

    def __init__(self):
        self.service_account_file = 'HotelOps Suite.json'
        self.target_email = 'magazzino@panoramagroup.it'
        self.spreadsheet_id = '1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA'

        # Fogli necessari
        self.sheets = {
            'totali': 'Totali',
            'prodotti': 'Prodotti',
            'reparti': 'Reparti',
            'movimentazioni': 'Movimentazioni'
        }

        self._initialize_services()

    def _initialize_services(self):
        """Inizializza i servizi Google API."""
        try:
            # Gmail con delega
            gmail_credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )
            gmail_delegated = gmail_credentials.with_subject(self.target_email)
            self.gmail_service = build('gmail', 'v1', credentials=gmail_delegated)

            # Sheets
            sheets_credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.sheets_service = build('sheets', 'v4', credentials=sheets_credentials)

            print("✅ Servizi Google API inizializzati")

        except Exception as e:
            print(f"❌ Errore nell'inizializzazione: {e}")
            raise

    def get_emails_with_label(self, label_name: str) -> List[Dict]:
        """Recupera tutte le email con una specifica label."""
        try:
            # Prima ottieni l'ID della label
            results = self.gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            label_id = None
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    label_id = label['id']
                    break

            if not label_id:
                print(f"⚠️  Label '{label_name}' non trovata")
                return []

            # Recupera le email con quella label
            results = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=50
            ).execute()

            messages = results.get('messages', [])
            print(f"✅ Trovate {len(messages)} email con label '{label_name}'")

            email_data = []
            for msg in messages:
                msg_data = self.gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()

                email_data.append({
                    'id': msg['id'],
                    'data': msg_data
                })

            return email_data

        except Exception as e:
            print(f"❌ Errore nel recupero email: {e}")
            return []

    def _extract_html_body(self, msg_data: Dict) -> str:
        """Estrae il corpo HTML dell'email."""
        html_body = ""

        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
        elif msg_data['payload']['body'].get('data'):
            html_body = base64.urlsafe_b64decode(
                msg_data['payload']['body']['data']
            ).decode('utf-8', errors='ignore')

        return html_body

    def _parse_currency(self, value: str) -> float:
        """Converte stringhe di valuta in float."""
        if not value or value == '-':
            return 0.0

        # Rimuovi simboli e spazi
        value = value.replace('€', '').replace('&euro;', '').strip()
        value = value.replace('.', '').replace(',', '.')

        try:
            return float(value)
        except:
            return 0.0

    def extract_data_from_email(self, email_data: Dict) -> Optional[Dict[str, Any]]:
        """Estrae tutti i dati da un'email."""
        try:
            msg_data = email_data['data']
            html_body = self._extract_html_body(msg_data)

            if not html_body:
                return None

            # Usa BeautifulSoup per parsing HTML
            soup = BeautifulSoup(html_body, 'html.parser')

            # Estrai timestamp email
            headers = msg_data['payload']['headers']
            date_header = next((h for h in headers if h['name'] == 'Date'), None)
            email_date = date_header['value'] if date_header else ''

            # Estrai le varie sezioni
            data = {
                'email_id': email_data['id'],
                'email_date': email_date,
                'totali': self._extract_totali(soup),
                'prodotti': self._extract_prodotti(soup),
                'reparti': self._extract_reparti(soup),
                'movimentazioni': self._extract_movimentazioni(soup)
            }

            # Aggiungi email_id e email_date ai totali
            data['totali']['email_id'] = email_data['id']
            data['totali']['email_date'] = email_date

            return data

        except Exception as e:
            print(f"❌ Errore nell'estrazione dati: {e}")
            return None

    def _extract_totali(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Estrae i dati dalla sezione Totali."""
        totali = {}

        # Estrai data report e periodo
        h1 = soup.find('h1')
        if h1 and h1.text == 'Report Panorama Beach':
            p = h1.find_next_sibling('p')
            if p:
                periodo_match = re.search(r'dal\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\s+al\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', p.text)
                if periodo_match:
                    totali['periodo_dal'] = periodo_match.group(1)
                    totali['periodo_al'] = periodo_match.group(2)
                    # Estrai solo la data dal periodo_al
                    data_match = re.search(r'(\d{2}/\d{2}/\d{4})', periodo_match.group(2))
                    if data_match:
                        totali['data_report'] = data_match.group(1)

        # Trova la tabella dei totali
        totali_header = soup.find('h2', string='Totali')
        if totali_header:
            table = totali_header.find_next('table')
            if table:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        descrizione = cells[0].text.strip()
                        numero = cells[1].text.strip()
                        importo = cells[2].text.strip()

                        # Mappa descrizioni ai campi del database
                        mapping = {
                            'Totale incassi': 'totale_incassi',
                            'Totale scontrini': 'totale_scontrini',
                            'Totale coperti': 'totale_coperti',
                            'Totale costo coperti': 'totale_costo_coperti',
                            'Totale lordo': 'totale_lordo',
                            'Totale ordini a ritiro': 'totale_ordini_ritiro',
                            'Totale ordini alla postazione': 'totale_ordini_postazione',
                            'Totale pagamento contanti': 'totale_pagamento_contanti',
                            'Totale pagamento carta di credito': 'totale_pagamento_carta',
                            'Spiaggia': 'ambiente_spiaggia'
                        }

                        if descrizione in mapping:
                            key = mapping[descrizione]
                            totali[f'{key}_numero'] = int(numero) if numero.isdigit() else 0
                            totali[f'{key}_importo'] = self._parse_currency(importo)

        # Estrai dati dai reparti SPIAGGIA
        reparti_header = soup.find('h2', string='Reparti')
        if reparti_header:
            table = reparti_header.find_next('table')
            if table:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 7:
                        reparto = cells[0].text.strip()
                        if reparto == 'SPIAGGIA':
                            totali['reparto_spiaggia_ordini'] = int(cells[5].text.strip()) if cells[5].text.strip().isdigit() else 0
                            totali['reparto_spiaggia_totale'] = self._parse_currency(cells[6].text.strip())
                        elif reparto == 'SPIAGGIA ALLOGGIATI':
                            totali['reparto_alloggiati_ordini'] = int(cells[5].text.strip()) if cells[5].text.strip().isdigit() else 0
                            totali['reparto_alloggiati_totale'] = self._parse_currency(cells[6].text.strip())

        return totali

    def _extract_prodotti(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Prodotti."""
        prodotti = []

        prodotti_header = soup.find('h2', string='Prodotti')
        if prodotti_header:
            table = prodotti_header.find_next('table')
            if table:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:
                        # Salta header e totali
                        if cells[0].text.strip() in ['Prodotto', 'Totali:']:
                            continue

                        prodotto = {
                            'prodotto': cells[0].text.strip(),
                            'reparto': cells[1].text.strip(),
                            'famiglia': cells[2].text.strip(),
                            'unita_misura': cells[3].text.strip(),
                            'magazzino': int(cells[4].text.strip()) if cells[4].text.strip().isdigit() else 0,
                            'quantita': int(cells[5].text.strip()) if cells[5].text.strip().isdigit() else 0,
                            'ordini': int(cells[6].text.strip()) if cells[6].text.strip().isdigit() else 0,
                            'totale': self._parse_currency(cells[7].text.strip())
                        }
                        prodotti.append(prodotto)

        return prodotti

    def _extract_reparti(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Reparti."""
        reparti = []

        reparti_header = soup.find('h2', string='Reparti')
        if reparti_header:
            table = reparti_header.find_next('table')
            if table:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 7:
                        # Salta header e totali
                        if cells[0].text.strip() in ['Reparto', 'Totali:']:
                            continue

                        reparto = {
                            'reparto': cells[0].text.strip(),
                            'famiglia': cells[1].text.strip(),
                            'unita_misura': cells[2].text.strip(),
                            'magazzino': int(cells[3].text.strip()) if cells[3].text.strip().isdigit() else 0,
                            'quantita': float(cells[4].text.strip()) if cells[4].text.strip() else 0.0,
                            'ordini': int(cells[5].text.strip()) if cells[5].text.strip().isdigit() else 0,
                            'totale': self._parse_currency(cells[6].text.strip())
                        }
                        reparti.append(reparto)

        return reparti

    def _extract_movimentazioni(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Movimentazioni."""
        movimentazioni = []

        mov_header = soup.find('h2', string='Movimentazione')
        if mov_header:
            table = mov_header.find_next('table')
            if table:
                rows = table.find_all('tr')

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 6:
                        # Salta header
                        if cells[0].text.strip() == 'Data':
                            continue

                        # Estrai numero ordine dal link
                        ordine_link = cells[3].find('a')
                        ordine = ordine_link.text.strip() if ordine_link else cells[3].text.strip()

                        mov = {
                            'data': cells[0].text.strip(),
                            'utente': cells[1].text.strip() if cells[1].text.strip() != '-' else '',
                            'tipologia': cells[2].text.strip(),
                            'ordine': ordine,
                            'valore': cells[4].text.strip(),
                            'descrizione': cells[5].text.strip()
                        }
                        movimentazioni.append(mov)

        return movimentazioni

    def _ensure_sheets_exist(self):
        """Assicura che tutti i fogli necessari esistano."""
        try:
            # Ottieni informazioni sul foglio
            spreadsheet = self.sheets_service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

            # Crea fogli mancanti
            requests = []
            for sheet_name in self.sheets.values():
                if sheet_name not in existing_sheets:
                    requests.append({
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    })

            if requests:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=body
                ).execute()
                print(f"✅ Creati {len(requests)} nuovi fogli")

        except Exception as e:
            print(f"❌ Errore nella creazione fogli: {e}")

    def update_all_sheets(self, all_data: List[Dict[str, Any]]):
        """Aggiorna tutti i fogli con i dati."""
        self._ensure_sheets_exist()

        # 1. Aggiorna foglio Totali
        self._update_totali_sheet([d['totali'] for d in all_data])

        # 2. Aggiorna foglio Prodotti
        self._update_prodotti_sheet(all_data)

        # 3. Aggiorna foglio Reparti
        self._update_reparti_sheet(all_data)

        # 4. Aggiorna foglio Movimentazioni
        self._update_movimentazioni_sheet(all_data)

    def _update_totali_sheet(self, totali_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Totali."""
        if not totali_data:
            return

        # Colonne del foglio
        columns = [
            'data_report', 'periodo_dal', 'periodo_al',
            'totale_incassi_numero', 'totale_incassi_importo',
            'totale_scontrini_numero', 'totale_scontrini_importo',
            'totale_coperti_numero', 'totale_coperti_importo',
            'totale_costo_coperti_numero', 'totale_costo_coperti_importo',
            'totale_lordo_numero', 'totale_lordo_importo',
            'totale_ordini_ritiro_numero', 'totale_ordini_ritiro_importo',
            'totale_ordini_postazione_numero', 'totale_ordini_postazione_importo',
            'totale_pagamento_contanti_numero', 'totale_pagamento_contanti_importo',
            'totale_pagamento_carta_numero', 'totale_pagamento_carta_importo',
            'ambiente_spiaggia_numero', 'ambiente_spiaggia_importo',
            'reparto_spiaggia_ordini', 'reparto_spiaggia_totale',
            'reparto_alloggiati_ordini', 'reparto_alloggiati_totale',
            'email_date', 'email_id'
        ]

        # Headers
        headers = [
            'Data Report', 'Periodo Dal', 'Periodo Al',
            'N. Incassi', 'Tot. Incassi €', 'N. Scontrini', 'Tot. Scontrini €',
            'N. Coperti', 'Tot. Coperti €', 'N. Costo Coperti', 'Tot. Costo Coperti €',
            'N. Lordo', 'Tot. Lordo €', 'N. Ordini Ritiro', 'Tot. Ordini Ritiro €',
            'N. Ordini Postazione', 'Tot. Ordini Postazione €',
            'N. Pagamenti Contanti', 'Tot. Contanti €', 'N. Pagamenti Carta', 'Tot. Carta €',
            'N. Ordini Spiaggia', 'Tot. Spiaggia €',
            'Rep. Spiaggia Ordini', 'Rep. Spiaggia Tot €',
            'Rep. Alloggiati Ordini', 'Rep. Alloggiati Tot €',
            'Data Email', 'ID Email'
        ]

        values = [headers]

        # Ordina per data (più recenti prima)
        sorted_data = sorted(totali_data, key=lambda x: x.get('data_report', ''), reverse=True)

        # Colonne che contengono importi in euro
        euro_columns = [
            'totale_incassi_importo', 'totale_scontrini_importo',
            'totale_coperti_importo', 'totale_costo_coperti_importo',
            'totale_lordo_importo', 'totale_ordini_ritiro_importo',
            'totale_ordini_postazione_importo', 'totale_pagamento_contanti_importo',
            'totale_pagamento_carta_importo', 'ambiente_spiaggia_importo',
            'reparto_spiaggia_totale', 'reparto_alloggiati_totale'
        ]

        for data in sorted_data:
            row = []
            for col in columns:
                value = data.get(col, '')
                if col in euro_columns and isinstance(value, (int, float)):
                    # Formatta come euro
                    row.append(f"€ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                elif isinstance(value, float):
                    row.append(f"{value:.2f}".replace('.', ','))
                else:
                    row.append(str(value))
            values.append(row)

        self._write_to_sheet(self.sheets['totali'], values)

    def _update_prodotti_sheet(self, all_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Prodotti."""
        headers = [
            'Data Report', 'Prodotto', 'Reparto', 'Famiglia',
            'Unità Misura', 'Magazzino', 'Quantità', 'Ordini', 'Totale €'
        ]

        values = [headers]

        for data in sorted(all_data, key=lambda x: x['totali'].get('data_report', ''), reverse=True):
            data_report = data['totali'].get('data_report', '')
            for prodotto in data['prodotti']:
                row = [
                    data_report,
                    prodotto.get('prodotto', ''),
                    prodotto.get('reparto', ''),
                    prodotto.get('famiglia', ''),
                    prodotto.get('unita_misura', ''),
                    str(prodotto.get('magazzino', 0)),
                    str(prodotto.get('quantita', 0)),
                    str(prodotto.get('ordini', 0)),
                    f"€ {prodotto.get('totale', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ]
                values.append(row)

        self._write_to_sheet(self.sheets['prodotti'], values)

    def _update_reparti_sheet(self, all_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Reparti."""
        headers = [
            'Data Report', 'Reparto', 'Famiglia', 'Unità Misura',
            'Magazzino', 'Quantità', 'Ordini', 'Totale €'
        ]

        values = [headers]

        for data in sorted(all_data, key=lambda x: x['totali'].get('data_report', ''), reverse=True):
            data_report = data['totali'].get('data_report', '')
            for reparto in data['reparti']:
                row = [
                    data_report,
                    reparto.get('reparto', ''),
                    reparto.get('famiglia', ''),
                    reparto.get('unita_misura', ''),
                    str(reparto.get('magazzino', 0)),
                    f"{reparto.get('quantita', 0):.2f}".replace('.', ','),
                    str(reparto.get('ordini', 0)),
                    f"€ {reparto.get('totale', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ]
                values.append(row)

        self._write_to_sheet(self.sheets['reparti'], values)

    def _update_movimentazioni_sheet(self, all_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Movimentazioni."""
        headers = [
            'Data Report', 'Data Movimento', 'Utente', 'Tipologia',
            'Ordine', 'Valore', 'Descrizione'
        ]

        values = [headers]

        for data in sorted(all_data, key=lambda x: x['totali'].get('data_report', ''), reverse=True):
            data_report = data['totali'].get('data_report', '')
            for mov in data['movimentazioni']:
                row = [
                    data_report,
                    mov.get('data', ''),
                    mov.get('utente', ''),
                    mov.get('tipologia', ''),
                    mov.get('ordine', ''),
                    mov.get('valore', ''),
                    mov.get('descrizione', '')
                ]
                values.append(row)

        self._write_to_sheet(self.sheets['movimentazioni'], values)

    def _write_to_sheet(self, sheet_name: str, values: List[List[str]]):
        """Scrive i dati in un foglio specifico."""
        try:
            # Pulisci il foglio
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:Z'
            ).execute()

            # Inserisci i nuovi dati
            body = {'values': values}
            result = self.sheets_service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A1',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            print(f"✅ Foglio '{sheet_name}' aggiornato: {result.get('updatedCells')} celle")

        except Exception as e:
            print(f"❌ Errore nell'aggiornamento del foglio '{sheet_name}': {e}")

    def process_all_emails(self):
        """Processa tutte le email e aggiorna i fogli."""
        print("🚀 Estrazione Consumi Spiaggia V2")
        print("=" * 60)

        # Recupera email
        emails = self.get_emails_with_label('consumi Spiaggia')
        if not emails:
            print("⚠️  Nessuna email trovata")
            return

        # Mostra email trovate
        print(f"\n📧 Email più recenti:")
        for i, email in enumerate(emails[:5]):
            headers = email['data']['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Senza oggetto')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            print(f"   {i+1}. {subject} - {date}")

        # Estrai dati da tutte le email
        print(f"\n⏳ Elaborazione {len(emails)} email...")
        all_data = []
        errors = 0

        for email in emails:
            data = self.extract_data_from_email(email)
            if data:
                all_data.append(data)
            else:
                errors += 1

        print(f"\n✅ Elaborazione completata:")
        print(f"   - Email processate: {len(emails)}")
        print(f"   - Dati estratti: {len(all_data)}")
        print(f"   - Errori: {errors}")

        if all_data:
            print("\n📊 Aggiornamento database...")
            self.update_all_sheets(all_data)

            # Riepilogo
            print("\n📈 Riepilogo aggiornamenti:")
            print(f"   - Foglio Totali: {len(all_data)} record")

            total_products = sum(len(d['prodotti']) for d in all_data)
            print(f"   - Foglio Prodotti: {total_products} righe")

            total_reparti = sum(len(d['reparti']) for d in all_data)
            print(f"   - Foglio Reparti: {total_reparti} righe")

            total_mov = sum(len(d['movimentazioni']) for d in all_data)
            print(f"   - Foglio Movimentazioni: {total_mov} righe")

            # Mostra date processate
            dates = sorted([d['totali'].get('data_report', '') for d in all_data], reverse=True)
            if dates:
                print(f"\n📅 Date più recenti processate:")
                for date in dates[:5]:
                    if date:
                        print(f"   - {date}")

        print("\n✅ Processo completato!")


def main():
    """Funzione principale."""
    try:
        extractor = ConsumiExtractorV2()
        extractor.process_all_emails()
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        raise


if __name__ == "__main__":
    main()
