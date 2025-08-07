#!/bin/bash

# Script per reset completo del sistema di estrazione consumi
# Rimuove duplicati e permette di ripartire da zero

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${RED}⚠️  RESET SISTEMA CONSUMI SPIAGGIA${NC}"
echo "===================================="
echo
echo "Questo script rimuoverà:"
echo "  • Il database locale (database_consumi.json)"
echo "  • I log di esecuzione"
echo "  • Le configurazioni cron"
echo
echo -e "${YELLOW}ATTENZIONE: I dati su Google Sheets NON verranno toccati${NC}"
echo

read -p "Sei sicuro di voler procedere? (digita 'RESET' per confermare): " confirm

if [ "$confirm" != "RESET" ]; then
    echo
    echo "Operazione annullata"
    exit 0
fi

echo
echo "🔧 Inizio reset..."

# 1. Rimuovi database locale
if [ -f "${SCRIPT_DIR}/database_consumi.json" ]; then
    echo "  • Rimozione database locale..."
    rm -f "${SCRIPT_DIR}/database_consumi.json"
    echo -e "${GREEN}    ✓ Database rimosso${NC}"
else
    echo "  • Database non presente"
fi

# 2. Rimuovi log
if [ -f "${SCRIPT_DIR}/cron.log" ]; then
    echo "  • Rimozione log cron..."
    rm -f "${SCRIPT_DIR}/cron.log"
    echo -e "${GREEN}    ✓ Log rimosso${NC}"
fi

if [ -d "${SCRIPT_DIR}/logs" ]; then
    echo "  • Rimozione directory logs..."
    rm -rf "${SCRIPT_DIR}/logs"
    echo -e "${GREEN}    ✓ Directory logs rimossa${NC}"
fi

# 3. Rimuovi vecchi file di hash (se esistono)
if [ -f "${SCRIPT_DIR}/processed_emails.json" ]; then
    echo "  • Rimozione file hash obsoleto..."
    rm -f "${SCRIPT_DIR}/processed_emails.json"
    echo -e "${GREEN}    ✓ File hash rimosso${NC}"
fi

if [ -f "$HOME/Documents/processed_emails.json" ]; then
    echo "  • Rimozione file hash in Documents..."
    rm -f "$HOME/Documents/processed_emails.json"
    echo -e "${GREEN}    ✓ File hash rimosso${NC}"
fi

# 4. Rimuovi configurazioni cron
echo "  • Rimozione configurazioni cron..."
CRON_REMOVED=false

# Rimuovi entry per sistema_consumi_ottimizzato.py
if crontab -l 2>/dev/null | grep -q "sistema_consumi_ottimizzato.py"; then
    crontab -l | grep -v "sistema_consumi_ottimizzato.py" | crontab - 2>/dev/null || true
    CRON_REMOVED=true
fi

# Rimuovi entry per altri script di estrazione
if crontab -l 2>/dev/null | grep -q "estrai_consumi"; then
    crontab -l | grep -v "estrai_consumi" | crontab - 2>/dev/null || true
    CRON_REMOVED=true
fi

if [ "$CRON_REMOVED" = true ]; then
    echo -e "${GREEN}    ✓ Configurazioni cron rimosse${NC}"
else
    echo "    • Nessuna configurazione cron trovata"
fi

# 5. Pulisci file temporanei
echo "  • Pulizia file temporanei..."
find "${SCRIPT_DIR}" -name "*.pyc" -delete 2>/dev/null || true
find "${SCRIPT_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${SCRIPT_DIR}" -name ".DS_Store" -delete 2>/dev/null || true
echo -e "${GREEN}    ✓ File temporanei rimossi${NC}"

echo
echo -e "${GREEN}✅ RESET COMPLETATO!${NC}"
echo
echo "Il sistema è stato resettato. Per riconfigurare:"
echo
echo "  1. Esegui: ${BLUE}./setup_sistema.sh${NC}"
echo "     Questo riconfigurerà tutto e processerà TUTTE le email"
echo
echo "  2. Oppure esegui manualmente: ${BLUE}python3 sistema_consumi_ottimizzato.py${NC}"
echo "     Per processare le email senza configurare il cron"
echo
echo -e "${YELLOW}Nota: I dati su Google Sheets sono rimasti intatti.${NC}"
echo "      Se vuoi anche pulire il foglio Google, dovrai farlo manualmente."
echo
