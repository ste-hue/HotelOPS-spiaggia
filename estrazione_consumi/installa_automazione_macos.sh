#!/bin/bash

# Script per installare l'automazione su macOS usando launchd
# Alternativa a cron per macOS moderni

set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory e file
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_FILE="${SCRIPT_DIR}/com.panoramagroup.consumi.plist"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
INSTALLED_PLIST="${LAUNCH_AGENTS_DIR}/com.panoramagroup.consumi.plist"

echo -e "${BLUE}🍎 INSTALLAZIONE AUTOMAZIONE MACOS${NC}"
echo "===================================="
echo
echo "Questo script configurerà l'esecuzione automatica"
echo "del sistema consumi usando launchd (compatibile con macOS)"
echo

# Verifica che il plist esista
if [ ! -f "${PLIST_FILE}" ]; then
    echo -e "${RED}❌ File plist non trovato!${NC}"
    exit 1
fi

# Crea directory LaunchAgents se non esiste
mkdir -p "${LAUNCH_AGENTS_DIR}"

# Se esiste già un'installazione, rimuovila
if [ -f "${INSTALLED_PLIST}" ]; then
    echo "🔄 Rimozione installazione esistente..."
    launchctl unload "${INSTALLED_PLIST}" 2>/dev/null || true
    rm -f "${INSTALLED_PLIST}"
    echo -e "${GREEN}✅ Vecchia installazione rimossa${NC}"
fi

# Copia il plist nella directory LaunchAgents
echo "📋 Installazione nuova configurazione..."
cp "${PLIST_FILE}" "${INSTALLED_PLIST}"

# Carica il job
echo "🚀 Attivazione automazione..."
launchctl load "${INSTALLED_PLIST}"

# Verifica che sia caricato
if launchctl list | grep -q "com.panoramagroup.consumi"; then
    echo -e "${GREEN}✅ Automazione installata con successo!${NC}"
    echo
    echo "📊 Configurazione attiva:"
    echo "   • Esecuzione: ogni notte alle 2:00"
    echo "   • Script: ${SCRIPT_DIR}/sistema_consumi_ottimizzato.py"
    echo "   • Log stdout: ${SCRIPT_DIR}/launchd_stdout.log"
    echo "   • Log stderr: ${SCRIPT_DIR}/launchd_stderr.log"
    echo
    echo "🔧 Comandi utili:"
    echo "   • Stato: launchctl list | grep panoramagroup"
    echo "   • Disattiva: launchctl unload ~/Library/LaunchAgents/com.panoramagroup.consumi.plist"
    echo "   • Riattiva: launchctl load ~/Library/LaunchAgents/com.panoramagroup.consumi.plist"
    echo "   • Esegui ora: launchctl start com.panoramagroup.consumi"
    echo "   • Log: tail -f ${SCRIPT_DIR}/launchd_*.log"
    echo
    echo -e "${GREEN}🎉 FATTO! Il sistema si avvierà automaticamente ogni notte alle 2:00${NC}"
    echo

    # Test opzionale
    read -p "Vuoi eseguire un test immediato? (s/n): " test
    if [[ "$test" =~ ^[Ss]$ ]]; then
        echo
        echo "🧪 Esecuzione test..."
        launchctl start com.panoramagroup.consumi
        echo
        echo "✅ Test avviato. Controlla i log per i risultati:"
        echo "   tail -f ${SCRIPT_DIR}/launchd_*.log"
    fi
else
    echo -e "${RED}❌ Errore nell'installazione!${NC}"
    echo "Prova a controllare i log di sistema:"
    echo "  log show --predicate 'eventMessage contains \"com.panoramagroup\"' --last 5m"
    exit 1
fi
