#!/bin/bash

# Script per configurare il cron job per l'estrazione automatica dei consumi
# Esegue ogni giorno e processa solo le nuove email

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
RUN_SCRIPT="${SCRIPT_DIR}/run_estrazione.sh"

echo -e "${BLUE}🔧 CONFIGURAZIONE CRON JOB - ESTRAZIONE CONSUMI SPIAGGIA${NC}"
echo "=================================================="
echo

# Verifica che lo script di esecuzione esista
if [ ! -f "${RUN_SCRIPT}" ]; then
    echo -e "${RED}❌ ERRORE: Script run_estrazione.sh non trovato!${NC}"
    echo "   Percorso cercato: ${RUN_SCRIPT}"
    exit 1
fi

# Mostra le opzioni disponibili
echo "📅 Quando vuoi eseguire l'estrazione automatica?"
echo
echo "1) Ogni notte alle 2:00 (consigliato)"
echo "2) Ogni mattina alle 8:00"
echo "3) Ogni sera alle 20:00"
echo "4) Ogni ora"
echo "5) Personalizzato"
echo

read -p "Scegli un'opzione (1-5): " choice

case $choice in
    1)
        CRON_TIME="0 2 * * *"
        DESCRIPTION="ogni notte alle 2:00"
        ;;
    2)
        CRON_TIME="0 8 * * *"
        DESCRIPTION="ogni mattina alle 8:00"
        ;;
    3)
        CRON_TIME="0 20 * * *"
        DESCRIPTION="ogni sera alle 20:00"
        ;;
    4)
        CRON_TIME="0 * * * *"
        DESCRIPTION="ogni ora"
        ;;
    5)
        echo
        echo "Inserisci il cron time personalizzato"
        echo "Formato: MIN ORA GIORNO MESE GIORNO_SETTIMANA"
        echo "Esempio: 30 14 * * * (ogni giorno alle 14:30)"
        read -p "Cron time: " CRON_TIME
        DESCRIPTION="personalizzato: ${CRON_TIME}"
        ;;
    *)
        echo -e "${RED}Opzione non valida${NC}"
        exit 1
        ;;
esac

# Crea la riga del crontab
CRON_LINE="CRON=1 ${CRON_TIME} ${RUN_SCRIPT} >> ${SCRIPT_DIR}/logs/cron_output.log 2>&1"

echo
echo -e "${YELLOW}📋 Configurazione scelta:${NC}"
echo "   Esecuzione: ${DESCRIPTION}"
echo "   Comando: ${CRON_LINE}"
echo

# Chiedi conferma
read -p "Vuoi procedere con questa configurazione? (s/n): " confirm

if [[ ! "$confirm" =~ ^[Ss]$ ]]; then
    echo -e "${RED}Operazione annullata${NC}"
    exit 0
fi

# Backup del crontab attuale
echo
echo "📦 Backup del crontab attuale..."
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true

# Verifica se esiste già una configurazione per questo script
if crontab -l 2>/dev/null | grep -q "${RUN_SCRIPT}"; then
    echo -e "${YELLOW}⚠️  Trovata configurazione esistente:${NC}"
    crontab -l | grep "${RUN_SCRIPT}"
    echo
    read -p "Vuoi sostituirla? (s/n): " replace

    if [[ "$replace" =~ ^[Ss]$ ]]; then
        # Rimuovi la vecchia configurazione
        crontab -l | grep -v "${RUN_SCRIPT}" | crontab -
        echo "✅ Vecchia configurazione rimossa"
    else
        echo -e "${RED}Operazione annullata${NC}"
        exit 0
    fi
fi

# Aggiungi la nuova configurazione
echo
echo "➕ Aggiunta nuova configurazione al crontab..."
(crontab -l 2>/dev/null; echo "${CRON_LINE}") | crontab -

# Verifica che sia stata aggiunta
if crontab -l | grep -q "${RUN_SCRIPT}"; then
    echo -e "${GREEN}✅ Cron job configurato con successo!${NC}"
    echo
    echo "📊 Riepilogo configurazione:"
    echo "   - Esecuzione: ${DESCRIPTION}"
    echo "   - Script: ${RUN_SCRIPT}"
    echo "   - Log: ${SCRIPT_DIR}/logs/"
    echo
    echo "🔍 Comandi utili:"
    echo "   - Visualizza crontab: crontab -l"
    echo "   - Modifica crontab: crontab -e"
    echo "   - Rimuovi questo job: crontab -l | grep -v '${RUN_SCRIPT}' | crontab -"
    echo "   - Controlla i log: tail -f ${SCRIPT_DIR}/logs/cron_output.log"
    echo
    echo -e "${GREEN}🎉 Sistema pronto! L'estrazione avverrà automaticamente ${DESCRIPTION}${NC}"
else
    echo -e "${RED}❌ ERRORE: Impossibile configurare il cron job${NC}"
    exit 1
fi

# Test opzionale
echo
read -p "Vuoi eseguire un test immediato? (s/n): " test

if [[ "$test" =~ ^[Ss]$ ]]; then
    echo
    echo "🚀 Esecuzione test..."
    echo
    "${RUN_SCRIPT}"
    echo
    echo "✅ Test completato. Controlla i risultati sopra."
fi

echo
echo "📌 Note importanti:"
echo "   1. Il sistema processerà SOLO le email non ancora elaborate"
echo "   2. I duplicati vengono automaticamente evitati"
echo "   3. I log vengono conservati per 30 giorni"
echo "   4. In caso di errori, controlla ${SCRIPT_DIR}/logs/"
echo
