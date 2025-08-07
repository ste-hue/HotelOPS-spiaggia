#!/usr/bin/env python3
"""
Sistema ottimizzato per l'estrazione dei consumi spiaggia.
- Nessun duplicato
- Solo nuove email
- Database efficiente
- Parsing completo
"""

import os
import re
import json
import hashlib
import base64
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup


class SistemaConsumiOttimizzato:
    """Sistema unificato per gestione consumi spiaggia."""

    def __init__(self):
        self.spreadsheet_id = "1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"
        self.service_account_file = self._find_service_account_file()
        self.target_email = "magazzino@panoramagroup.it"
        self.target_label = "consumi Spiaggia"
        self.db_file = "database_consumi.json"
        self.database = self._load_database()

        # Servizi Google
        self.gmail_service = None
        self.sheets_service = None

    def _find_service_account_file(self) -> str:
        """Trova il file del service account."""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "HotelOps Suite.json"),
            os.path.expanduser("~/HotelOps Suite.json"),
            os.path.expanduser("~/Documents/HotelOps Suite.json"),
            os.path.expanduser("~/Desktop/HotelOps Suite.json"),
            os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "")
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return path

        raise FileNotFoundError("Service account file 'HotelOps Suite.json' non trovato")

    def _load_database(self) -> Dict:
        """Carica il database locale."""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "processed_emails": {},
            "consumi_data": [],
            "last_update": None
        }

    def _save_database(self):
        """Salva il database locale."""
        self.database["last_update"] = datetime.now().isoformat()
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.database, f, indent=2, ensure_ascii=False)

    def authenticate(self):
        """Autentica con Google APIs."""
        print("🔐 Autenticazione in corso...")

        try:
            # Credenziali per Sheets (senza delega)
            sheets_credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

            # Credenziali per Gmail (con delega)
            gmail_credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )

            # Applica delega per Gmail
            delegated_credentials = gmail_credentials.with_subject(self.target_email)

            # Crea i servizi
            self.gmail_service = build('gmail', 'v1', credentials=delegated_credentials)
            self.sheets_service = build('sheets', 'v4', credentials=sheets_credentials)

            # Test veloce per verificare che funzioni
            try:
                profile = self.gmail_service.users().getProfile(userId='me').execute()
                print(f"✅ Autenticazione completata - Accesso a: {profile.get('emailAddress')}")
            except Exception as e:
                print("✅ Autenticazione completata")

        except Exception as e:
            print(f"❌ Errore autenticazione: {e}")
            raise

    def get_new_emails(self) -> List[Dict]:
        """Recupera solo le email non ancora processate, prioritizzando originali su forward."""
        print("\n📧 Ricerca nuove email...")

        try:
            # Query per email con label
            query = f'label:"{self.target_label}"'

            all_messages = []
            page_token = None

            while True:
                results = self.gmail_service.users().messages().list(
                    userId='me',
                    q=query,
                    pageToken=page_token,
                    maxResults=500
                ).execute()

                messages = results.get('messages', [])
                all_messages.extend(messages)

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            # Filtra solo le non processate e arricchisci con metadata
            new_messages = []
            for msg in all_messages:
                if msg['id'] not in self.database['processed_emails']:
                    # Ottieni i dettagli dell'email per il sorting
                    try:
                        msg_detail = self.gmail_service.users().messages().get(
                            userId='me', id=msg['id']
                        ).execute()

                        headers = msg_detail['payload']['headers']
                        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

                        # Arricchisci il messaggio con metadata per sorting
                        msg['_subject'] = subject
                        msg['_date'] = date
                        msg['_is_forward'] = subject.startswith('Fwd:') or subject.startswith('FW:')
                        msg['_internal_date'] = int(msg_detail.get('internalDate', 0))

                        new_messages.append(msg)
                    except Exception as e:
                        print(f"   ⚠️  Errore nel recupero dettagli email {msg['id']}: {e}")
                        # Aggiungi comunque il messaggio base
                        msg['_subject'] = 'Unknown'
                        msg['_date'] = 'Unknown'
                        msg['_is_forward'] = False
                        msg['_internal_date'] = 0
                        new_messages.append(msg)

            # Ordinamento intelligente: prima le non-forward, poi per data (più recenti prima)
            new_messages.sort(key=lambda x: (x['_is_forward'], -x['_internal_date']))

            print(f"   Totale email: {len(all_messages)}")
            print(f"   Già processate: {len(all_messages) - len(new_messages)}")
            print(f"   Nuove da processare: {len(new_messages)}")

            # Log dell'ordine di processamento
            if new_messages:
                print("   📋 Ordine di processamento:")
                for i, msg in enumerate(new_messages[:5], 1):  # Mostra solo le prime 5
                    fwd_indicator = " [FWD]" if msg['_is_forward'] else ""
                    print(f"      {i}. {msg['_subject'][:50]}...{fwd_indicator}")
                if len(new_messages) > 5:
                    print(f"      ... e altre {len(new_messages) - 5}")

            return new_messages

        except Exception as e:
            print(f"❌ Errore nel recupero email: {e}")
            return []

    def parse_email(self, email_id: str) -> Optional[Dict]:
        """Estrae tutti i dati da un'email."""
        try:
            # Recupera email completa
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=email_id
            ).execute()

            # Estrai metadata
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')

            print(f"   📧 Subject: {subject}")
            print(f"   📅 Date: {date}")

            # Estrai HTML
            html_content = self._extract_html(message['payload'])
            if not html_content:
                print("   ⚠️ Nessun contenuto HTML trovato")
                return None

            print(f"   📄 HTML content: {len(html_content)} caratteri")

            # Parsing completo
            parsed_data = self._parse_html_content(html_content)
            if not parsed_data:
                print("   ⚠️ Parsing HTML fallito - nessun dato estratto")
                return None

            print(f"   ✅ Dati estratti: {list(parsed_data.keys())}")

            # Aggiungi metadata
            parsed_data['email_id'] = email_id
            parsed_data['email_subject'] = subject
            parsed_data['email_date'] = date
            parsed_data['processed_at'] = datetime.now().isoformat()

            # Genera hash univoco
            unique_key = f"{parsed_data.get('data_report')}|{parsed_data.get('periodo_dal')}|{parsed_data.get('periodo_al')}"
            parsed_data['content_hash'] = hashlib.md5(unique_key.encode()).hexdigest()

            return parsed_data

        except Exception as e:
            print(f"   ❌ Errore parsing email {email_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_html(self, payload) -> str:
        """Estrae contenuto HTML dall'email."""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif 'parts' in part:
                    html = self._extract_html(part)
                    if html:
                        return html
        elif payload.get('body', {}).get('data'):
            if payload.get('mimeType') == 'text/html':
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        return ""

    def _parse_html_content(self, html: str) -> Optional[Dict]:
        """Parser ottimizzato per estrarre tutti i dati."""
        result = {}

        # Debug: salva HTML per analisi
        with open('debug_last_email.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("   💾 HTML salvato in debug_last_email.html per analisi")

        # 1. ESTRAI DATA E PERIODO DAL TITOLO
        # Cerca pattern tipo "Report Panorama Beach 14/07/2025"
        title_match = re.search(r'<h1>Report Panorama Beach</h1>\s*<p>dal\s+([^<]+)\s+al\s+([^<]+)</p>', html)
        if title_match:
            periodo_dal = title_match.group(1).strip()
            periodo_al = title_match.group(2).strip()
            result['periodo_dal'] = periodo_dal
            result['periodo_al'] = periodo_al

            # Estrai data dal periodo "al" (es: "13/07/2025 19:15:32" -> "13/07/2025")
            data_match = re.search(r'(\d{2}/\d{2}/\d{4})', periodo_al)
            if data_match:
                result['data_report'] = data_match.group(1)
            print(f"      ✓ periodo_dal: {periodo_dal}")
            print(f"      ✓ periodo_al: {periodo_al}")
            print(f"      ✓ data_report: {result.get('data_report', 'N/A')}")

        # 2. ESTRAI TOTALI DALLA TABELLA
        # Cerca "Totale incassi" e "Totale scontrini" nelle righe della tabella
        patterns = {
            'numero_incassi': r'<td[^>]*>Totale incassi</td>\s*<td[^>]*>(\d+)</td>',
            'totale_incassi': r'<td[^>]*>Totale incassi</td>\s*<td[^>]*>\d+</td>\s*<td[^>]*>&euro;\s*([\d.,]+)</td>',
            'numero_scontrini': r'<td[^>]*>Totale scontrini</td>\s*<td[^>]*>(\d+)</td>',
            'totale_scontrini': r'<td[^>]*>Totale scontrini</td>\s*<td[^>]*>\d+</td>\s*<td[^>]*>&euro;\s*([\d.,]+)</td>'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if 'numero' in key:
                    result[key] = int(value)
                elif 'totale' in key:
                    result[key] = float(value.replace('.', '').replace(',', '.'))
                else:
                    result[key] = value
                print(f"      ✓ {key}: {result[key]}")
            else:
                print(f"      ✗ {key}: non trovato")

        # Verifica dati minimi
        if 'data_report' not in result:
            print("   ⚠️ Data Report non trovata - parsing fallito")
            return None

        print(f"   📊 Totali estratti: Incassi={result.get('numero_incassi', 0)} (€{result.get('totale_incassi', 0)}), Scontrini={result.get('numero_scontrini', 0)} (€{result.get('totale_scontrini', 0)})")

        # 2. PRODOTTI
        # Cerca la sezione "Prodotti" nell'HTML
        prodotti = []
        prodotti_section = re.search(r'<h2>Prodotti</h2>(.*?)(?:<h2>|</td></tr></tbody></table>)', html, re.DOTALL)
        if prodotti_section:
            # Trova tutte le righe della tabella prodotti
            rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>[^<]*</td>\s*<td>[^<]*</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>\s*<td>&euro;\s*([\d.,]+)</td>', prodotti_section.group(1))
            for row in rows:
                try:
                    prodotti.append({
                        'nome': row[0].strip(),
                        'reparto': row[1].strip(),
                        'quantita': int(row[3].strip() or 0),
                        'importo': float(row[5].replace(',', '.'))
                    })
                except:
                    continue
        result['prodotti'] = prodotti
        print(f"   📦 Prodotti trovati: {len(prodotti)}")

        # 3. REPARTI
        reparti = []
        reparti_section = re.search(r'<h2>Reparti</h2>(.*?)(?:<h2>|</tbody></table>)', html, re.DOTALL)
        if reparti_section:
            # Trova tutte le righe della tabella reparti
            rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*(?:<td>[^<]*</td>\s*)*<td[^>]*>&euro;\s*([\d.,]+)</td>', reparti_section.group(1))
            for row in rows:
                try:
                    reparti.append({
                        'nome': row[0].strip(),
                        'importo': float(row[1].replace(',', '.'))
                    })
                except:
                    continue
        result['reparti'] = reparti
        print(f"   🏬 Reparti trovati: {len(reparti)}")

        # 4. MOVIMENTAZIONI
        movimentazioni = []
        mov_section = re.search(r'<h2>Movimentazione</h2>(.*?)(?:<h2>|</tbody></table>)', html, re.DOTALL)
        if mov_section:
            # Trova tutte le righe della tabella movimentazioni
            # Pattern aggiornato per catturare meglio i dati
            rows = re.findall(r'<tr>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td[^>]*>.*?</td>\s*<td>([^<]*)</td>\s*<td>([^<]+)</td>', mov_section.group(1))
            for row in rows:
                try:
                    # Salta l'header
                    if 'Data' in row[0] or 'Utente' in row[1]:
                        continue
                    movimentazioni.append({
                        'data_ora': row[0].strip(),
                        'operatore': row[1].strip() if row[1].strip() != '-' else '',
                        'tipo': row[2].strip(),
                        'valore': row[3].strip(),
                        'articolo': row[4].strip()
                    })
                except Exception as e:
                    continue
        result['movimentazioni'] = movimentazioni
        print(f"   🔄 Movimentazioni trovate: {len(movimentazioni)}")

        return result



    def update_spreadsheet(self):
        """Aggiorna il foglio Google Sheets con i dati ordinati."""
        print("\n📊 Aggiornamento Google Sheets...")

        # Prepara i dati dal database
        all_data = self.database['consumi_data']

        if not all_data:
            print("   Nessun dato da salvare")
            return

        # Ordina per data (più recenti prima)
        sorted_data = sorted(
            all_data,
            key=lambda x: datetime.strptime(x.get('data_report', '01/01/2000'), '%d/%m/%Y'),
            reverse=True
        )

        # Aggiorna tutti i fogli
        self._update_totali(sorted_data)
        self._update_prodotti(sorted_data)
        self._update_reparti(sorted_data)
        self._update_movimentazioni(sorted_data)

        print("✅ Google Sheets aggiornato completamente")

    def _update_totali(self, data: List[Dict]):
        """Aggiorna foglio Totali."""
        headers = [
            'Data Report', 'Periodo Dal', 'Periodo Al',
            'N. Incassi', 'Tot. Incassi €', 'N. Scontrini', 'Tot. Scontrini €'
        ]

        values = [headers]
        for record in data:
            row = [
                record.get('data_report', ''),
                record.get('periodo_dal', ''),
                record.get('periodo_al', ''),
                record.get('numero_incassi', ''),
                f"€{record.get('totale_incassi', 0):,.2f}".replace(',', '.'),
                record.get('numero_scontrini', ''),
                f"€{record.get('totale_scontrini', 0):,.2f}".replace(',', '.')
            ]
            values.append(row)

        self._write_to_sheet('Totali', values)

    def _update_prodotti(self, data: List[Dict]):
        """Aggiorna foglio Prodotti."""
        headers = ['Data Report', 'Prodotto', 'Quantità', 'Importo €', 'Qtà Omaggio', 'Importo Omaggio €']
        values = [headers]

        for record in data:
            data_report = record.get('data_report', '')
            for prodotto in record.get('prodotti', []):
                row = [
                    data_report,
                    prodotto.get('nome', ''),
                    prodotto.get('quantita', ''),
                    f"€{prodotto.get('importo', 0):,.2f}".replace(',', '.'),
                    prodotto.get('qta_omaggio', ''),
                    f"€{prodotto.get('importo_omaggio', 0):,.2f}".replace(',', '.')
                ]
                values.append(row)

        self._write_to_sheet('Prodotti', values)

    def _update_reparti(self, data: List[Dict]):
        """Aggiorna foglio Reparti."""
        headers = ['Data Report', 'Reparto', 'Importo €']
        values = [headers]

        for record in data:
            data_report = record.get('data_report', '')
            for reparto in record.get('reparti', []):
                row = [
                    data_report,
                    reparto.get('nome', ''),
                    f"€{reparto.get('importo', 0):,.2f}".replace(',', '.')
                ]
                values.append(row)

        self._write_to_sheet('Reparti', values)

    def _update_movimentazioni(self, data: List[Dict]):
        """Aggiorna foglio Movimentazioni."""
        headers = ['Data Report', 'Data/Ora', 'Operatore', 'Tipo', 'Articolo', 'Valore']
        values = [headers]

        for record in data:
            data_report = record.get('data_report', '')
            for mov in record.get('movimentazioni', []):
                row = [
                    data_report,
                    mov.get('data_ora', ''),
                    mov.get('operatore', ''),
                    mov.get('tipo', ''),
                    mov.get('articolo', ''),
                    mov.get('valore', '')
                ]
                values.append(row)

        self._write_to_sheet('Movimentazioni', values)

    def _write_to_sheet(self, sheet_name: str, values: List[List]):
        """Scrive i dati in un foglio specifico."""
        try:
            # Pulisci il foglio
            self.sheets_service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:Z'
            ).execute()

            # Scrivi i nuovi dati
            if values:
                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A1',
                    valueInputOption='USER_ENTERED',
                    body={'values': values}
                ).execute()

                print(f"   ✅ {sheet_name}: {len(values)-1} righe")

        except Exception as e:
            print(f"   ❌ Errore aggiornamento {sheet_name}: {e}")

    def process(self):
        """Processo principale."""
        print("\n🚀 SISTEMA CONSUMI SPIAGGIA - AVVIO")
        print("=" * 50)

        # 1. Autenticazione
        self.authenticate()

        # 2. Recupera nuove email
        new_emails = self.get_new_emails()

        if not new_emails:
            print("\n✅ Nessuna nuova email da processare")
            return

        # 3. Processa ogni nuova email
        print(f"\n📝 Elaborazione {len(new_emails)} nuove email...")
        processed = 0
        errors = 0

        for i, msg in enumerate(new_emails, 1):
            print(f"\n[{i}/{len(new_emails)}] Email {msg['id']}...")

            # Parse email
            parsed_data = self.parse_email(msg['id'])

            if parsed_data:
                data_report = parsed_data.get('data_report', '')

                # Verifica se esiste già un record per questa data
                existing_record_index = None
                for idx, record in enumerate(self.database['consumi_data']):
                    if record.get('data_report') == data_report:
                        existing_record_index = idx
                        break

                # Se è un forward e esiste già l'originale, salta
                is_forward = msg.get('_is_forward', False)
                if is_forward and existing_record_index is not None:
                    existing_record = self.database['consumi_data'][existing_record_index]
                    # Se il record esistente ha totali validi, salta il forward
                    if existing_record.get('totale_incassi') is not None and existing_record.get('totale_incassi') > 0:
                        print(f"   ⏭️  Forward saltato - esiste già originale con dati validi")
                        continue

                # Se questa è un'email originale e esiste un record danneggiato (forward), sostituiscilo
                if not is_forward and existing_record_index is not None:
                    existing_record = self.database['consumi_data'][existing_record_index]
                    # Se il record esistente non ha totali o sono zero, sostituiscilo
                    if (existing_record.get('totale_incassi') is None or
                        existing_record.get('totale_incassi') == 0 or
                        len(existing_record.get('prodotti', [])) == 0):

                        print(f"   🔄 Sostituendo record danneggiato del {data_report}")

                        # Rimuovi il record danneggiato
                        old_record = self.database['consumi_data'].pop(existing_record_index)

                        # Rimuovi anche dalla lista delle email processate
                        email_to_remove = None
                        for email_id, info in self.database['processed_emails'].items():
                            if info.get('data_report') == data_report:
                                email_to_remove = email_id
                                break
                        if email_to_remove:
                            del self.database['processed_emails'][email_to_remove]

                        # Aggiungi il nuovo record
                        self.database['consumi_data'].append(parsed_data)
                        self.database['processed_emails'][msg['id']] = {
                            'processed_at': datetime.now().isoformat(),
                            'data_report': data_report,
                            'hash': parsed_data['content_hash']
                        }
                        processed += 1
                        print(f"   ✅ Record del {data_report} sostituito con dati corretti")
                        continue

                # Verifica duplicati per hash del contenuto
                hash_exists = any(
                    d.get('content_hash') == parsed_data['content_hash']
                    for d in self.database['consumi_data']
                )

                if not hash_exists and existing_record_index is None:
                    self.database['consumi_data'].append(parsed_data)
                    self.database['processed_emails'][msg['id']] = {
                        'processed_at': datetime.now().isoformat(),
                        'data_report': data_report,
                        'hash': parsed_data['content_hash']
                    }
                    processed += 1
                    print(f"   ✅ Report del {data_report} estratto")
                else:
                    print(f"   ⏭️  Duplicato saltato (hash o data già esistente)")
            else:
                errors += 1
                print(f"   ❌ Errore nel parsing")

        # 4. Salva database
        self._save_database()

        # 5. Aggiorna Google Sheets
        if processed > 0:
            self.update_spreadsheet()

        # 6. Riepilogo
        print("\n" + "=" * 50)
        print("📊 RIEPILOGO ELABORAZIONE:")
        print(f"   • Nuove email processate: {processed}")
        print(f"   • Errori: {errors}")
        print(f"   • Totale record nel database: {len(self.database['consumi_data'])}")
        print(f"   • Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("\n✅ PROCESSO COMPLETATO")


def main():
    """Funzione principale."""
    sistema = SistemaConsumiOttimizzato()
    sistema.process()


if __name__ == "__main__":
    main()
