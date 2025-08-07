#!/usr/bin/env python3
"""
Script di test per il parsing delle email di consumo.
Utile per verificare e affinare i pattern di estrazione.
"""

import re
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import json

# Esempio di contenuto email (da sostituire con esempi reali)
SAMPLE_EMAIL_HTML = """
<html>
<body>
<h2>Report Consumo Spiaggia</h2>
<table border="1">
    <tr>
        <td><b>Data:</b></td>
        <td>15/07/2025</td>
    </tr>
    <tr>
        <td><b>Ora:</b></td>
        <td>18:39:21</td>
    </tr>
    <tr>
        <td><b>Totale Consumo:</b></td>
        <td>€ 1.234,56</td>
    </tr>
    <tr>
        <td><b>Ombrelloni:</b></td>
        <td>45</td>
    </tr>
    <tr>
        <td><b>Lettini:</b></td>
        <td>90</td>
    </tr>
    <tr>
        <td><b>Incasso Bar:</b></td>
        <td>€ 456,78</td>
    </tr>
    <tr>
        <td><b>Incasso Ristorante:</b></td>
        <td>€ 678,90</td>
    </tr>
    <tr>
        <td><b>Incasso Spiaggia:</b></td>
        <td>€ 98,88</td>
    </tr>
    <tr>
        <td><b>Presenze:</b></td>
        <td>150</td>
    </tr>
    <tr>
        <td><b>Ticket Medio:</b></td>
        <td>€ 8,23</td>
    </tr>
</table>
</body>
</html>
"""

SAMPLE_EMAIL_TEXT = """
Report Panorama Beach 15/07/2025 18:39:21

Riepilogo Giornaliero:
Data: 15/07/2025
Ora: 18:39:21

CONSUMI:
Totale Consumo: € 1.234,56
Ombrelloni: 45
Lettini: 90

INCASSI:
Incasso Totale: € 1.234,56
- Bar: € 456,78
- Ristorante: € 678,90
- Spiaggia: € 98,88

STATISTICHE:
Presenze: 150
Ticket Medio: € 8,23
"""


class EmailParser:
    """Parser per estrarre dati dalle email di consumo."""

    def __init__(self):
        """Inizializza il parser con i pattern di estrazione."""
        self.patterns = {
            'data': r'Data[:\s]+(\d{2}/\d{2}/\d{4})',
            'ora': r'Ora[:\s]+(\d{2}:\d{2}:\d{2})',
            'totale_consumo': r'Totale\s*Consumo[:\s]+€?\s*([\d.,]+)',
            'numero_ombrelloni': r'Ombrelloni[:\s]+(\d+)',
            'numero_lettini': r'Lettini[:\s]+(\d+)',
            'incasso_totale': r'Incasso\s*Totale[:\s]+€?\s*([\d.,]+)',
            'incasso_bar': r'Bar[:\s]+€?\s*([\d.,]+)',
            'incasso_ristorante': r'Ristorante[:\s]+€?\s*([\d.,]+)',
            'incasso_spiaggia': r'Spiaggia[:\s]+€?\s*([\d.,]+)',
            'presenze': r'Presenze[:\s]+(\d+)',
            'ticket_medio': r'Ticket\s*Medio[:\s]+€?\s*([\d.,]+)'
        }

    def parse_html(self, html_content: str) -> Dict[str, Any]:
        """
        Parsa contenuto HTML per estrarre dati.

        Args:
            html_content: Contenuto HTML dell'email

        Returns:
            Dizionario con i dati estratti
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        data = {}

        # Cerca nelle tabelle
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)

                    # Mappa le chiavi ai nostri campi
                    if 'Data' in key and 'data' not in data:
                        data['data'] = value
                    elif 'Ora' in key:
                        data['ora'] = value
                    elif 'Totale Consumo' in key:
                        data['totale_consumo'] = self._extract_number(value)
                    elif 'Ombrelloni' in key:
                        data['numero_ombrelloni'] = self._extract_number(value)
                    elif 'Lettini' in key:
                        data['numero_lettini'] = self._extract_number(value)
                    elif 'Incasso Bar' in key:
                        data['incasso_bar'] = self._extract_number(value)
                    elif 'Incasso Ristorante' in key:
                        data['incasso_ristorante'] = self._extract_number(value)
                    elif 'Incasso Spiaggia' in key:
                        data['incasso_spiaggia'] = self._extract_number(value)
                    elif 'Presenze' in key:
                        data['presenze'] = self._extract_number(value)
                    elif 'Ticket Medio' in key:
                        data['ticket_medio'] = self._extract_number(value)

        # Se non troviamo dati nelle tabelle, proviamo con il testo
        if not data:
            text_content = soup.get_text()
            data = self.parse_text(text_content)

        return data

    def parse_text(self, text_content: str) -> Dict[str, Any]:
        """
        Parsa contenuto testuale per estrarre dati.

        Args:
            text_content: Contenuto testuale dell'email

        Returns:
            Dizionario con i dati estratti
        """
        data = {}

        for key, pattern in self.patterns.items():
            match = re.search(pattern, text_content, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1)
                if key in ['totale_consumo', 'incasso_totale', 'incasso_bar',
                          'incasso_ristorante', 'incasso_spiaggia', 'ticket_medio']:
                    value = self._normalize_currency(value)
                elif key in ['numero_ombrelloni', 'numero_lettini', 'presenze']:
                    value = int(value)
                data[key] = value

        return data

    def _extract_number(self, value: str) -> str:
        """Estrae il numero da una stringa con simboli di valuta."""
        # Rimuovi il simbolo dell'euro e gli spazi
        value = value.replace('€', '').strip()
        return value

    def _normalize_currency(self, value: str) -> float:
        """Normalizza i valori di valuta in float."""
        # Rimuovi spazi e converti virgola in punto
        value = value.replace(' ', '').replace('.', '').replace(',', '.')
        try:
            return float(value)
        except ValueError:
            return 0.0

    def parse(self, content: str, content_type: str = 'auto') -> Dict[str, Any]:
        """
        Parsa il contenuto dell'email.

        Args:
            content: Contenuto dell'email
            content_type: Tipo di contenuto ('html', 'text', 'auto')

        Returns:
            Dizionario con i dati estratti
        """
        if content_type == 'auto':
            # Determina automaticamente il tipo
            if '<html' in content.lower() or '<table' in content.lower():
                content_type = 'html'
            else:
                content_type = 'text'

        if content_type == 'html':
            return self.parse_html(content)
        else:
            return self.parse_text(content)


def test_parser():
    """Testa il parser con esempi di email."""
    parser = EmailParser()

    print("=== Test Parser Email Consumi ===\n")

    # Test con HTML
    print("1. Test parsing HTML:")
    print("-" * 50)
    result_html = parser.parse(SAMPLE_EMAIL_HTML, 'html')
    print(json.dumps(result_html, indent=2, ensure_ascii=False))

    print("\n2. Test parsing testo:")
    print("-" * 50)
    result_text = parser.parse(SAMPLE_EMAIL_TEXT, 'text')
    print(json.dumps(result_text, indent=2, ensure_ascii=False))

    print("\n3. Test auto-detect HTML:")
    print("-" * 50)
    result_auto = parser.parse(SAMPLE_EMAIL_HTML, 'auto')
    print(f"Tipo rilevato: HTML")
    print(json.dumps(result_auto, indent=2, ensure_ascii=False))

    print("\n4. Validazione dati estratti:")
    print("-" * 50)

    # Verifica che i campi principali siano stati estratti
    required_fields = ['data', 'totale_consumo', 'numero_ombrelloni', 'numero_lettini']

    for field in required_fields:
        if field in result_html:
            print(f"✓ Campo '{field}' estratto correttamente: {result_html[field]}")
        else:
            print(f"✗ Campo '{field}' non trovato!")

    print("\n=== Fine Test ===")


def test_with_custom_email():
    """
    Testa il parser con un'email personalizzata.
    Inserisci qui il contenuto HTML o testo di un'email reale per testare.
    """
    # Inserisci qui il contenuto dell'email da testare
    custom_email = """
    <!-- Incolla qui il contenuto HTML dell'email -->
    """

    if custom_email.strip() and not custom_email.strip().startswith('<!--'):
        parser = EmailParser()
        result = parser.parse(custom_email)

        print("\n=== Test con Email Personalizzata ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n⚠ Inserisci il contenuto dell'email nella funzione test_with_custom_email()")


if __name__ == '__main__':
    # Esegui i test standard
    test_parser()

    # Testa con email personalizzata (se fornita)
    test_with_custom_email()
