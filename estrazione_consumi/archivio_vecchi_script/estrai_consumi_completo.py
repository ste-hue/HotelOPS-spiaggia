#!/usr/bin/env python3
"""
Estrattore Completo Consumi Spiaggia - Cattura TUTTI i dati
Versione: 2.0
Autore: HotelOPS Development Team
"""

import os
import base64
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import json
from html.parser import HTMLParser

from google.oauth2 import service_account
from googleapiclient.discovery import build

class ConsumiSpiaggiaCompletExtractor:
    """Estrattore completo per tutti i dati dei consumi spiaggia."""

    def __init__(self):
        self.service_account_file = 'HotelOps Suite.json'
        self.target_email = 'magazzino@panoramagroup.it'
        self.spreadsheet_id = '1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA'

        # Nomi dei fogli nel Google Sheet
        self.sheets = {
            'totali': 'Totali',
            'prodotti': 'Prodotti',
            'reparti': 'Reparti',
            'movimentazioni': 'Movimentazioni',
            'addetti': 'Addetti',
            'ambienti': 'Ambienti'
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

    def get_label_id(self, label_name: str) -> Optional[str]:
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

    def get_emails_with_label(self, label_name: str) -> List[Dict]:
        """Recupera tutte le email con una specifica label."""
        label_id = self.get_label_id(label_name)
        if not label_id:
            print(f"⚠️  Label '{label_name}' non trovata")
            return []

        try:
            results = self.gmail_service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=100
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

    def _extract_body(self, msg_data: Dict) -> str:
        """Estrae il corpo dell'email."""
        body = ""
        html_body = ""

        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif msg_data['payload']['body'].get('data'):
            body = base64.urlsafe_b64decode(
                msg_data['payload']['body']['data']
            ).decode('utf-8', errors='ignore')

        # Preferisci HTML se disponibile
        return html_body if html_body else body

    def _parse_currency(self, value: str) -> float:
        """Converte stringhe di valuta in float."""
        if not value or value == '-':
            return 0.0

        value = value.replace('€', '').replace(',', '.').strip()
        try:
            return float(value)
        except:
            return 0.0

    def _parse_totali_section(self, body: str) -> Dict[str, Any]:
        """Estrae i dati dalla sezione Totali."""
        totali = {}

        # Pattern per data report e periodo in HTML
        date_pattern = r'<h1>Report Panorama Beach</h1>.*?dal\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\s+al\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})'

        date_match = re.search(date_pattern, body, re.DOTALL)
        if date_match:
            totali['periodo_dal'] = date_match.group(1)
            totali['periodo_al'] = date_match.group(2)
            # Estrai data dal periodo_al
            data_report_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_match.group(2))
            if data_report_match:
                totali['data_report'] = data_report_match.group(1)

        # Pattern per totali nella tabella HTML
        # Formato: <td>Descrizione</td><td align="right">numero</td><td align="right">&euro; importo</td>
        totali_patterns = {
            'totale_incassi': r'<td[^>]*>Totale incassi</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_scontrini': r'<td[^>]*>Totale scontrini</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_coperti': r'<td[^>]*>Totale coperti</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d+)</td>',
            'totale_costo_coperti': r'<td[^>]*>Totale costo coperti</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_lordo': r'<td[^>]*>Totale lordo</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_ordini_ritiro': r'<td[^>]*>Totale ordini a ritiro</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_ordini_postazione': r'<td[^>]*>Totale ordini alla postazione</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_pagamento_contanti': r'<td[^>]*>Totale pagamento contanti</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'totale_pagamento_carta': r'<td[^>]*>Totale pagamento carta di credito</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>',
            'ambiente_spiaggia': r'<td[^>]*>Spiaggia</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>'
        }

        for key, pattern in totali_patterns.items():
            match = re.search(pattern, body, re.DOTALL)
            if match:
                if key == 'totale_coperti':
                    # totale_coperti ha formato diverso (numero, numero, media)
                    totali[f'{key}_numero'] = int(match.group(1))
                    totali[f'{key}_importo'] = float(match.group(2))
                else:
                    totali[f'{key}_numero'] = int(match.group(1))
                    importo = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    totali[f'{key}_importo'] = self._parse_currency(importo)

        # Pattern per reparti specifici nella tabella HTML
        rep_spiaggia = re.search(r'<td>SPIAGGIA</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>', body, re.DOTALL)
        if rep_spiaggia:
            # Dobbiamo prendere il penultimo numero (ordini) dalla riga
            spiaggia_row = re.search(r'<td>SPIAGGIA</td>.*?<td[^>]*>\d+</td>.*?<td[^>]*>\d+</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>', body, re.DOTALL)
            if spiaggia_row:
                totali['reparto_spiaggia_ordini'] = int(spiaggia_row.group(1))
                totali['reparto_spiaggia_totale'] = self._parse_currency(spiaggia_row.group(2))

        rep_alloggiati = re.search(r'<td>SPIAGGIA ALLOGGIATI</td>.*?<td[^>]*>\d+</td>.*?<td[^>]*>\d+</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>', body, re.DOTALL)
        if rep_alloggiati:
            totali['reparto_alloggiati_ordini'] = int(rep_alloggiati.group(1))
            totali['reparto_alloggiati_totale'] = self._parse_currency(rep_alloggiati.group(2))

        return totali

    def _parse_prodotti_section(self, body: str) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Prodotti dalla tabella HTML."""
        prodotti = []

        # Trova la sezione Prodotti nella tabella HTML
        prodotti_start = body.find('<h2>Prodotti</h2>')
        if prodotti_start == -1:
            return prodotti

        # Trova la fine della sezione (prossima h2 o fine body)
        prodotti_end = body.find('<h2>Varianti</h2>', prodotti_start)
        if prodotti_end == -1:
            prodotti_end = body.find('</body>', prodotti_start)

        prodotti_html = body[prodotti_start:prodotti_end] if prodotti_end != -1 else body[prodotti_start:]

        # Estrai righe dalla tabella HTML
        # Pattern per estrarre righe <tr> con dati prodotto
        row_pattern = r'<tr>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>.*?</tr>'

        matches = re.finditer(row_pattern, prodotti_html, re.DOTALL)

        for match in matches:
            try:
                # Salta header e totali
                if 'Prodotto' in match.group(1) or 'Totali:' in match.group(1):
                    continue

                prodotto = {
                    'prodotto': match.group(1).strip(),
                    'reparto': match.group(2).strip(),
                    'famiglia': match.group(3).strip(),
                    'unita_misura': match.group(4).strip(),
                    'magazzino': int(match.group(5).strip()) if match.group(5).strip().isdigit() else 0,
                    'quantita': int(match.group(6).strip()) if match.group(6).strip().isdigit() else 0,
                    'ordini': int(match.group(7).strip()) if match.group(7).strip().isdigit() else 0,
                    'totale': self._parse_currency(match.group(8))
                }
                prodotti.append(prodotto)
            except:
                continue

        return prodotti

    def _parse_reparti_section(self, body: str) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Reparti dalla tabella HTML."""
        reparti = []

        # Trova la sezione Reparti nella tabella HTML
        reparti_start = body.find('<h2>Reparti</h2>')
        if reparti_start == -1:
            return reparti

        # Trova la fine della sezione
        reparti_end = body.find('<h2>Prodotti</h2>', reparti_start)
        if reparti_end == -1:
            reparti_end = body.find('</table>', reparti_start) + 8

        reparti_html = body[reparti_start:reparti_end] if reparti_end != -1 else body[reparti_start:]

        # Estrai righe dalla tabella HTML
        # Pattern per estrarre righe <tr> con dati reparto
        row_pattern = r'<tr>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>(.*?)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>.*?</tr>'

        matches = re.finditer(row_pattern, reparti_html, re.DOTALL)

        for match in matches:
            try:
                # Salta header e totali
                if 'Reparto' in match.group(1) or 'Totali:' in match.group(1):
                    continue

                reparto = {
                    'reparto': match.group(1).strip(),
                    'famiglia': match.group(2).strip(),
                    'unita_misura': match.group(3).strip(),
                    'magazzino': int(match.group(4).strip()) if match.group(4).strip().isdigit() else 0,
                    'quantita': float(match.group(5).strip()) if match.group(5).strip() else 0.0,
                    'ordini': int(match.group(6).strip()) if match.group(6).strip().isdigit() else 0,
                    'totale': self._parse_currency(match.group(7))
                }
                reparti.append(reparto)
            except:
                continue

        return reparti

    def _parse_movimentazioni_section(self, body: str) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Movimentazione dalla tabella HTML."""
        movimentazioni = []

        # Trova la sezione Movimentazione nella tabella HTML
        mov_start = body.find('<h2>Movimentazione</h2>')
        if mov_start == -1:
            return movimentazioni

        # Trova la fine della sezione
        mov_end = body.find('<h2>Reparti</h2>', mov_start)
        if mov_end == -1:
            mov_end = body.find('</table>', mov_start) + 8

        mov_html = body[mov_start:mov_end] if mov_end != -1 else body[mov_start:]

        # Pattern per estrarre righe dalla tabella movimentazioni
        # Nota: il campo ordine contiene un link <a>
        row_pattern = r'<tr>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?<td>.*?>(.*?)</a></td>.*?<td>(.*?)</td>.*?<td>(.*?)</td>.*?</tr>'

        matches = re.finditer(row_pattern, mov_html, re.DOTALL)

        for match in matches:
            try:
                mov = {
                    'data': match.group(1).strip(),
                    'utente': match.group(2).strip() if match.group(2).strip() != '-' else '',
                    'tipologia': match.group(3).strip(),
                    'ordine': match.group(4).strip(),
                    'valore': match.group(5).strip(),
                    'descrizione': match.group(6).strip()
                }
                movimentazioni.append(mov)
            except:
                continue

        return movimentazioni

    def _parse_addetti_section(self, body: str) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Addetti dalla tabella HTML."""
        addetti = []

        # Pattern per addetti cassa nella tabella HTML
        # Formato: <td>NOME Incassi/Scontrini</td><td align="right">numero</td><td align="right">&euro; totale</td><td align="right">media</td>
        addetti_pattern = r'<td>([A-Z\s]+)\s+(Incassi|Scontrini)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>.*?<td[^>]*>([\d,]+)</td>'

        matches = re.finditer(addetti_pattern, body, re.DOTALL)
        for match in matches:
            addetto = {
                'nome': match.group(1).strip(),
                'tipo': match.group(2),
                'numero': int(match.group(3)),
                'totale': self._parse_currency(match.group(4)),
                'media': self._parse_currency(match.group(5))
            }
            addetti.append(addetto)

        return addetti

    def _parse_ambienti_section(self, body: str) -> List[Dict[str, Any]]:
        """Estrae i dati dalla sezione Ambienti dalla tabella HTML."""
        ambienti = []

        # Pattern per ambienti nella tabella HTML
        # Formato: <td>nome ambiente</td><td align="right">numero</td><td align="right">&euro; totale</td><td align="right">media</td>
        ambienti_pattern = r'<td>(dipendenti|Spiaggia|Tavoli Lido)</td>.*?<td[^>]*>(\d+)</td>.*?<td[^>]*>&euro;\s*([\d,]+)</td>.*?<td[^>]*>([\d,]+)</td>'

        matches = re.finditer(ambienti_pattern, body, re.DOTALL)
        for match in matches:
            ambiente = {
                'ambiente': match.group(1),
                'numero': int(match.group(2)),
                'totale': self._parse_currency(match.group(3)),
                'media': self._parse_currency(match.group(4))
            }
            ambienti.append(ambiente)

        return ambienti

    def extract_complete_data_from_email(self, email_data: Dict) -> Optional[Dict[str, Any]]:
        """Estrae TUTTI i dati da un'email."""
        try:
            msg_data = email_data['data']
            body = self._extract_body(msg_data)

            if not body:
                return None

            # Estrai timestamp email
            headers = msg_data['payload']['headers']
            date_header = next((h for h in headers if h['name'] == 'Date'), None)
            email_date = date_header['value'] if date_header else ''

            # Estrai tutte le sezioni
            data = {
                'email_id': email_data['id'],
                'email_date': email_date,
                'totali': self._parse_totali_section(body),
                'prodotti': self._parse_prodotti_section(body),
                'reparti': self._parse_reparti_section(body),
                'movimentazioni': self._parse_movimentazioni_section(body),
                'addetti': self._parse_addetti_section(body),
                'ambienti': self._parse_ambienti_section(body)
            }

            # Aggiungi email_id e email_date ai totali per compatibilità
            data['totali']['email_id'] = email_data['id']
            data['totali']['email_date'] = email_date

            return data

        except Exception as e:
            print(f"❌ Errore nell'estrazione dati: {e}")
            return None

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
        """Aggiorna tutti i fogli con i dati completi."""
        self._ensure_sheets_exist()

        # 1. Aggiorna foglio Totali
        self._update_totali_sheet([d['totali'] for d in all_data])

        # 2. Aggiorna foglio Prodotti
        self._update_prodotti_sheet(all_data)

        # 3. Aggiorna foglio Reparti
        self._update_reparti_sheet(all_data)

        # 4. Aggiorna foglio Movimentazioni
        self._update_movimentazioni_sheet(all_data)

        # 5. Aggiorna foglio Addetti
        self._update_addetti_sheet(all_data)

        # 6. Aggiorna foglio Ambienti
        self._update_ambienti_sheet(all_data)

    def _update_totali_sheet(self, totali_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Totali (come prima)."""
        if not totali_data:
            return

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
        sorted_data = sorted(totali_data, key=lambda x: x.get('data_report', ''), reverse=True)

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

    def _update_addetti_sheet(self, all_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Addetti."""
        headers = [
            'Data Report', 'Nome', 'Tipo', 'Numero', 'Totale €', 'Media €'
        ]

        values = [headers]

        for data in sorted(all_data, key=lambda x: x['totali'].get('data_report', ''), reverse=True):
            data_report = data['totali'].get('data_report', '')
            for addetto in data['addetti']:
                row = [
                    data_report,
                    addetto.get('nome', ''),
                    addetto.get('tipo', ''),
                    str(addetto.get('numero', 0)),
                    f"€ {addetto.get('totale', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"€ {addetto.get('media', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ]
                values.append(row)

        self._write_to_sheet(self.sheets['addetti'], values)

    def _update_ambienti_sheet(self, all_data: List[Dict[str, Any]]):
        """Aggiorna il foglio Ambienti."""
        headers = [
            'Data Report', 'Ambiente', 'Numero', 'Totale €', 'Media €'
        ]

        values = [headers]

        for data in sorted(all_data, key=lambda x: x['totali'].get('data_report', ''), reverse=True):
            data_report = data['totali'].get('data_report', '')
            for ambiente in data['ambienti']:
                row = [
                    data_report,
                    ambiente.get('ambiente', ''),
                    str(ambiente.get('numero', 0)),
                    f"€ {ambiente.get('totale', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                    f"€ {ambiente.get('media', 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                ]
                values.append(row)

        self._write_to_sheet(self.sheets['ambienti'], values)

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
        """Processa tutte le email e aggiorna tutti i fogli."""
        print("🚀 Estrazione COMPLETA dati consumi spiaggia")
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
            data = self.extract_complete_data_from_email(email)
            if data:
                all_data.append(data)
            else:
                errors += 1

        print(f"\n✅ Elaborazione completata:")
        print(f"   - Email processate: {len(emails)}")
        print(f"   - Dati estratti: {len(all_data)}")
        print(f"   - Errori: {errors}")

        if all_data:
            print("\n📊 Aggiornamento database multi-foglio...")
            self.update_all_sheets(all_data)

            # Riepilogo per foglio
            print("\n📈 Riepilogo aggiornamenti:")
            print(f"   - Foglio Totali: {len(all_data)} record")

            # Conta prodotti totali
            total_products = sum(len(d['prodotti']) for d in all_data)
            print(f"   - Foglio Prodotti: {total_products} righe")

            # Conta reparti totali
            total_reparti = sum(len(d['reparti']) for d in all_data)
            print(f"   - Foglio Reparti: {total_reparti} righe")

            # Conta movimentazioni
            total_mov = sum(len(d['movimentazioni']) for d in all_data)
            print(f"   - Foglio Movimentazioni: {total_mov} righe")

            # Conta addetti
            total_addetti = sum(len(d['addetti']) for d in all_data)
            print(f"   - Foglio Addetti: {total_addetti} righe")

            # Conta ambienti
            total_ambienti = sum(len(d['ambienti']) for d in all_data)
            print(f"   - Foglio Ambienti: {total_ambienti} righe")

            # Mostra ultime date processate
            dates = sorted([d['totali'].get('data_report', '') for d in all_data], reverse=True)
            if dates:
                print(f"\n📅 Date più recenti processate:")
                for date in dates[:5]:
                    print(f"   - {date}")

        print("\n✅ Processo completato!")


def main():
    """Funzione principale."""
    try:
        extractor = ConsumiSpiaggiaCompletExtractor()
        extractor.process_all_emails()
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        raise


if __name__ == "__main__":
    main()
