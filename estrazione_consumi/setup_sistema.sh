#!/bin/bash

# Setup automatico del sistema di estrazione consumi
# Configura tutto il necessario e imposta il cron job

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="${SCRIPT_DIR}/sistema_consumi_ottimizzato.py"

echo -e "${BLUE}🚀 SETUP SISTEMA CONSUMI SPIAGGIA${NC}"
echo "=================================="
echo

# 1. Verifica Python
echo "📌 Verifica requisiti..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 non trovato!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python3 disponibile${NC}"

# 2. Installa dipendenze
echo
echo "📦 Installazione dipendenze Python..."
pip3 install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client beautifulsoup4 --quiet
echo -e "${GREEN}✅ Dipendenze installate${NC}"

# 3. Verifica file service account
echo
echo "🔍 Ricerca file service account..."
SERVICE_ACCOUNT_FOUND=false
for path in \
    "${SCRIPT_DIR}/HotelOps Suite.json" \
    "${HOME}/HotelOps Suite.json" \
    "${HOME}/Documents/HotelOps Suite.json" \
    "${HOME}/Desktop/HotelOps Suite.json"; do
    if [ -f "$path" ]; then
        echo -e "${GREEN}✅ Service account trovato: $path${NC}"
        SERVICE_ACCOUNT_FOUND=true
        break
    fi
done

if [ "$SERVICE_ACCOUNT_FOUND" = false ]; then
    echo -e "${RED}❌ File 'HotelOps Suite.json' non trovato!${NC}"
    echo "   Posiziona il file in una di queste directory:"
    echo "   - ${SCRIPT_DIR}/"
    echo "   - ${HOME}/"
    echo "   - ${HOME}/Documents/"
    echo "   - ${HOME}/Desktop/"
    exit 1
fi

# 4. Rendi eseguibile lo script Python
chmod +x "${PYTHON_SCRIPT}"

# 5. Test del sistema
echo
echo "🧪 Test del sistema..."
echo -e "${YELLOW}Eseguo un test per verificare che tutto funzioni...${NC}"
echo

if python3 "${PYTHON_SCRIPT}"; then
    echo
    echo -e "${GREEN}✅ Test completato con successo!${NC}"
else
    echo
    echo -e "${RED}❌ Test fallito! Verifica gli errori sopra.${NC}"
    exit 1
fi

# 6. Configurazione cron job
echo
echo -e "${BLUE}⏰ CONFIGURAZIONE AUTOMAZIONE${NC}"
echo "=============================="
echo
echo "Quando vuoi eseguire l'estrazione automatica?"
echo
echo "1) Ogni notte alle 2:00 (consigliato)"
echo "2) Ogni mattina alle 7:00"
echo "3) Ogni sera alle 19:00"
echo "4) Due volte al giorno (7:00 e 19:00)"
echo "5) Ogni ora"
echo "6) Non configurare ora"
echo

read -p "Scegli un'opzione (1-6): " choice

case $choice in
    1)
        CRON_TIME="0 2 * * *"
        DESCRIPTION="ogni notte alle 2:00"
        ;;
    2)
        CRON_TIME="0 7 * * *"
        DESCRIPTION="ogni mattina alle 7:00"
        ;;
    3)
        CRON_TIME="0 19 * * *"
        DESCRIPTION="ogni sera alle 19:00"
        ;;
    4)
        CRON_TIME="0 7,19 * * *"
        DESCRIPTION="due volte al giorno (7:00 e 19:00)"
        ;;
    5)
        CRON_TIME="0 * * * *"
        DESCRIPTION="ogni ora"
        ;;
    6)
        echo
        echo "⏭️  Configurazione cron saltata"
        echo
        echo -e "${GREEN}✅ Setup completato!${NC}"
        echo
        echo "Per eseguire manualmente:"
        echo "  python3 '${PYTHON_SCRIPT}'"
        echo
        echo "Per configurare il cron in seguito, esegui:"
        echo "  crontab -e"
        echo "  e aggiungi questa riga:"
        echo "  0 2 * * * cd '${SCRIPT_DIR}' && python3 sistema_consumi_ottimizzato.py"
        exit 0
        ;;
    *)
        echo -e "${RED}Opzione non valida${NC}"
        exit 1
        ;;
esac

# Crea entry crontab
CRON_ENTRY="${CRON_TIME} cd '${SCRIPT_DIR}' && python3 sistema_consumi_ottimizzato.py >> '${SCRIPT_DIR}/cron.log' 2>&1"

echo
echo -e "${YELLOW}Configurazione scelta: ${DESCRIPTION}${NC}"
echo "Comando cron: ${CRON_ENTRY}"
echo

read -p "Confermi? (s/n): " confirm
if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
    echo "Operazione annullata"
    exit 0
fi

# Rimuovi eventuali entry esistenti
crontab -l 2>/dev/null | grep -v "sistema_consumi_ottimizzato.py" | crontab - 2>/dev/null || true

# Aggiungi nuova entry
(crontab -l 2>/dev/null; echo "${CRON_ENTRY}") | crontab -

echo
echo -e "${GREEN}✅ Cron job configurato!${NC}"

# 7. Riepilogo finale
echo
echo -e "${GREEN}🎉 SETUP COMPLETATO CON SUCCESSO!${NC}"
echo
echo "📊 Riepilogo configurazione:"
echo "   • Script: ${PYTHON_SCRIPT}"
echo "   • Database locale: ${SCRIPT_DIR}/database_consumi.json"
echo "   • Esecuzione automatica: ${DESCRIPTION}"
echo "   • Log cron: ${SCRIPT_DIR}/cron.log"
echo "   • Google Sheet: https://docs.google.com/spreadsheets/d/1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"
echo
echo "📌 Comandi utili:"
echo "   • Esecuzione manuale: python3 '${PYTHON_SCRIPT}'"
echo "   • Visualizza cron: crontab -l"
echo "   • Log in tempo reale: tail -f '${SCRIPT_DIR}/cron.log'"
echo "   • Disattiva cron: crontab -l | grep -v sistema_consumi_ottimizzato.py | crontab -"
echo
echo "Il sistema processerà automaticamente solo le NUOVE email,"
echo "evitando duplicati e mantenendo un database pulito e ordinato."
echo
