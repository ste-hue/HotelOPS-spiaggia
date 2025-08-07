#!/usr/bin/env python3
"""
Test di parsing per debug estrazione prodotti e reparti
"""

import re

# Esempio di testo reale dalla email
test_text = """RepartiRepartoFamigliaUnità di misuraMagazzinoQuantitàOrdiniTotaleAPERITIVI E VINIpz01714€ 159,00BIBITE E BIRREpz09974€ 261,50BURGER E PATATINEpz084€ 81,00CAFFETTERIA - COLAZIONEpz02316€ 44,50GELATIpz03935€ 113,00INSALATEpz122€ 22,00PANINI/BRUSCHETTEpz099€ 111,00PIZZA E FRITTIpz075€ 20,00SNACKpz01210€ 19,00SPIAGGIApz01514€ 525,00SPIAGGIA ALLOGGIATIpz01110€ 223,00SUCCHI DI FRUTTApz021€ 5,00Totali:244,00194€ 1584,00ProdottiProdottoRepartoFamigliaUnità di misuraMagazzinoQuantitàOrdiniTotaleAPEROL SPRITZAPERITIVI E VINIpz054€ 45,00LEMON SPRITZAPERITIVI E VINIpz065€ 54,00VINO BIANCO - BICCHIERE APERITIVI E VINIpz343€ 20,00VINO BIANCO - BOTTIGLIAAPERITIVI E VINIpz022€ 40,00ACQUA FRIZZANTE SVEVA 50 CLBIBITE E BIRREpz0129€ 18,00ACQUA LILIA 50 CLBIBITE E BIRREpz04126€ 61,50BIRRA  PORETTI ALLA SPINA BIBITE E BIRREpz043€ 22,00BIRRA CORONA 33 CLBIBITE E BIRREpz043€ 22,00"""

def parse_currency(value):
    """Converte stringhe di valuta in float."""
    if not value or value == '-':
        return 0.0
    value = value.replace('€', '').replace(',', '.').strip()
    try:
        return float(value)
    except:
        return 0.0

def test_parse_reparti():
    """Test parsing sezione Reparti."""
    print("🧪 Test Parsing Reparti")
    print("=" * 50)

    # Trova la sezione Reparti
    reparti_start = test_text.find('RepartiReparto')
    reparti_end = test_text.find('ProdottiProdotto')

    if reparti_start == -1:
        print("❌ Sezione Reparti non trovata")
        return

    reparti_text = test_text[reparti_start:reparti_end] if reparti_end != -1 else test_text[reparti_start:]
    print(f"📝 Testo estratto (primi 200 caratteri):\n{reparti_text[:200]}...\n")

    # Lista dei reparti conosciuti
    reparti_noti = [
        'APERITIVI E VINI',
        'BIBITE E BIRRE',
        'BURGER E PATATINE',
        'CAFFETTERIA - COLAZIONE',
        'GELATI',
        'INSALATE',
        'PANINI/BRUSCHETTE',
        'PIZZA E FRITTI',
        'SNACK',
        'SPIAGGIA ALLOGGIATI',
        'SPIAGGIA',
        'SUCCHI DI FRUTTA'
    ]

    reparti = []

    # Metodo 1: Splitting per €
    print("📊 Metodo 1: Split per €")
    lines = reparti_text.split('€')

    for i, line in enumerate(lines[:-1]):  # Escludi l'ultima parte
        # L'importo è all'inizio della linea successiva
        import_match = re.search(r'^\s*([\d,]+)', lines[i+1])
        if not import_match:
            continue

        importo = import_match.group(1)

        # Trova pz e i numeri prima
        data_match = re.search(r'pz(\d+)([\d,]+)(\d+)$', line)
        if data_match:
            magazzino = int(data_match.group(1))
            quantita = float(data_match.group(2).replace(',', '.'))
            ordini = int(data_match.group(3))

            # Il resto è il nome del reparto
            resto = line[:data_match.start()]

            # Trova quale reparto è
            reparto_trovato = None
            for reparto in reparti_noti:
                if reparto in resto:
                    reparto_trovato = reparto
                    break

            if reparto_trovato:
                rep = {
                    'reparto': reparto_trovato,
                    'magazzino': magazzino,
                    'quantita': quantita,
                    'ordini': ordini,
                    'totale': parse_currency(importo)
                }
                reparti.append(rep)
                print(f"✅ Trovato: {reparto_trovato} - €{parse_currency(importo)}")

    print(f"\n📈 Totale reparti trovati: {len(reparti)}")
    return reparti

def test_parse_prodotti():
    """Test parsing sezione Prodotti."""
    print("\n\n🧪 Test Parsing Prodotti")
    print("=" * 50)

    # Trova la sezione Prodotti
    prodotti_start = test_text.find('ProdottiProdotto')

    if prodotti_start == -1:
        print("❌ Sezione Prodotti non trovata")
        return

    prodotti_text = test_text[prodotti_start:]
    print(f"📝 Testo estratto (primi 300 caratteri):\n{prodotti_text[:300]}...\n")

    prodotti = []

    # Lista dei reparti per identificazione
    reparti_noti = [
        'APERITIVI E VINI',
        'BIBITE E BIRRE',
        'BURGER E PATATINE',
        'CAFFETTERIA - COLAZIONE',
        'GELATI',
        'INSALATE',
        'PANINI/BRUSCHETTE',
        'PIZZA E FRITTI',
        'SNACK',
        'SPIAGGIA ALLOGGIATI',
        'SPIAGGIA',
        'SUCCHI DI FRUTTA'
    ]

    # Metodo: Split per €
    print("📊 Metodo: Split per €")
    lines = prodotti_text.split('€')

    for i, line in enumerate(lines[:-1]):
        # L'importo è all'inizio della linea successiva
        import_match = re.search(r'^\s*([\d,]+)', lines[i+1])
        if not import_match:
            continue

        importo = import_match.group(1)

        # Trova pz e i numeri prima
        data_match = re.search(r'pz(\d+)(\d+)(\d+)$', line)
        if data_match:
            magazzino = int(data_match.group(1))
            quantita = int(data_match.group(2))
            ordini = int(data_match.group(3))

            # Il resto contiene nome prodotto e reparto
            resto = line[:data_match.start()]

            # Trova quale reparto è presente
            nome_prodotto = resto
            reparto_trovato = ''

            for reparto in reparti_noti:
                if reparto in resto:
                    # Estrai il nome del prodotto rimuovendo il reparto
                    nome_prodotto = resto.replace(reparto, '').strip()
                    reparto_trovato = reparto
                    break

            # Pulisci il nome del prodotto
            nome_prodotto = nome_prodotto.strip()

            if nome_prodotto and len(nome_prodotto) < 100:  # Filtro di sicurezza
                prod = {
                    'prodotto': nome_prodotto,
                    'reparto': reparto_trovato,
                    'magazzino': magazzino,
                    'quantita': quantita,
                    'ordini': ordini,
                    'totale': parse_currency(importo)
                }
                prodotti.append(prod)
                print(f"✅ {nome_prodotto[:30]:<30} | {reparto_trovato[:20]:<20} | €{parse_currency(importo):>8.2f}")

    print(f"\n📈 Totale prodotti trovati: {len(prodotti)}")
    return prodotti

def test_parsing_alternativo():
    """Test con regex più specifiche."""
    print("\n\n🧪 Test Parsing Alternativo con Regex")
    print("=" * 50)

    # Test per prodotti con pattern più specifico
    # Esempio: APEROL SPRITZAPERITIVI E VINIpz054€ 45,00

    # Prima identifichiamo tutti i possibili pattern di reparto
    reparti_pattern = r'(APERITIVI E VINI|BIBITE E BIRRE|BURGER E PATATINE|CAFFETTERIA - COLAZIONE|GELATI|INSALATE|PANINI/BRUSCHETTE|PIZZA E FRITTI|SNACK|SPIAGGIA ALLOGGIATI|SPIAGGIA|SUCCHI DI FRUTTA)'

    # Pattern per prodotti
    # Cattura: nome_prodotto + reparto + pz + magazzino + quantita + ordini + € + importo
    pattern = rf'([A-Z0-9\s\-\./\']+?)({reparti_pattern})pz(\d+)(\d+)(\d+)€\s*([\d,]+)'

    print("📊 Cercando prodotti con pattern regex...")

    matches = re.finditer(pattern, test_text)
    prodotti = []

    for match in matches:
        prod = {
            'prodotto': match.group(1).strip(),
            'reparto': match.group(2).strip(),
            'magazzino': int(match.group(3)),
            'quantita': int(match.group(4)),
            'ordini': int(match.group(5)),
            'totale': parse_currency(match.group(6))
        }
        prodotti.append(prod)
        print(f"✅ {prod['prodotto'][:30]:<30} | {prod['reparto'][:20]:<20} | €{prod['totale']:>8.2f}")

    print(f"\n📈 Totale prodotti trovati con regex: {len(prodotti)}")

if __name__ == "__main__":
    # Test parsing reparti
    reparti = test_parse_reparti()

    # Test parsing prodotti
    prodotti = test_parse_prodotti()

    # Test metodo alternativo
    test_parsing_alternativo()

    print("\n\n📊 Riepilogo Finale:")
    print(f"   - Reparti trovati: {len(reparti) if reparti else 0}")
    print(f"   - Prodotti trovati: {len(prodotti) if prodotti else 0}")
