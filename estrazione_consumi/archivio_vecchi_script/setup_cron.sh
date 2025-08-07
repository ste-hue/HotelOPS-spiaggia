#!/bin/bash

# Script di setup per automazione cron - Estrazione Consumi Spiaggia
# Autore: HotelOPS
# Data: 2025

echo "🚀 Setup Automazione Estrazione Consumi Spiaggia"
echo "================================================"

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verifica se siamo nella directory corretta
if [ ! -f "estrai_consumi_spiaggia.py" ]; then
    echo -e "${RED}❌ Errore: File estrai_consumi_spiaggia.py non trovato!${NC}"
    echo "   Assicurati di eseguire questo script dalla directory estrazione_consumi/"
    exit 1
fi

# Ottieni il percorso completo della directory corrente
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH=$(which python3)

echo -e "${GREEN}✅ Directory script:${NC} $SCRIPT_DIR"
echo -e "${GREEN}✅ Python path:${NC} $PYTHON_PATH"

# Verifica dipendenze Python
echo -e "\n${YELLOW}📦 Verifica dipendenze Python...${NC}"
python3 -c "import google.auth; import googleapiclient" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Dipendenze mancanti! Installa con:${NC}"
    echo "   pip install -r requirements.txt"
    exit 1
else
    echo -e "${GREEN}✅ Dipendenze Python OK${NC}"
fi

# Verifica credenziali
if [ ! -f "credentials.json" ]; then
    echo -e "${RED}❌ File credentials.json non trovato!${NC}"
    echo "   Scarica le credenziali da Google Cloud Console"
    exit 1
fi

# Test esecuzione script
echo -e "\n${YELLOW}🧪 Test esecuzione script...${NC}"
python3 estrai_consumi_spiaggia.py --test 2>/dev/null
if [ $? -eq 0 ] || [ $? -eq 2 ]; then
    echo -e "${GREEN}✅ Script funzionante${NC}"
else
    echo -e "${RED}❌ Errore nell'esecuzione dello script${NC}"
    exit 1
fi

# Creazione entry cron
echo -e "\n${YELLOW}⏰ Configurazione Cron${NC}"
echo "Quando vuoi eseguire l'estrazione? (default: ogni giorno alle 8:30)"
echo "1) Ogni giorno alle 8:30"
echo "2) Ogni giorno alle 9:00"
echo "3) Ogni 6 ore"
echo "4) Ogni ora"
echo "5) Personalizzato"
read -p "Scelta (1-5) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        CRON_SCHEDULE="30 8 * * *"
        CRON_DESC="ogni giorno alle 8:30"
        ;;
    2)
        CRON_SCHEDULE="0 9 * * *"
        CRON_DESC="ogni giorno alle 9:00"
        ;;
    3)
        CRON_SCHEDULE="0 */6 * * *"
        CRON_DESC="ogni 6 ore"
        ;;
    4)
        CRON_SCHEDULE="0 * * * *"
        CRON_DESC="ogni ora"
        ;;
    5)
        read -p "Inserisci schedule cron personalizzato: " CRON_SCHEDULE
        CRON_DESC="personalizzato: $CRON_SCHEDULE"
        ;;
    *)
        CRON_SCHEDULE="30 8 * * *"
        CRON_DESC="ogni giorno alle 8:30"
        ;;
esac

# Log file
LOG_FILE="$HOME/logs/consumi_spiaggia.log"
LOG_DIR=$(dirname "$LOG_FILE")

# Crea directory logs se non esiste
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✅ Creata directory logs: $LOG_DIR${NC}"
fi

# Costruisci comando cron
CRON_CMD="cd $SCRIPT_DIR && $PYTHON_PATH estrai_consumi_spiaggia.py >> $LOG_FILE 2>&1"
CRON_ENTRY="$CRON_SCHEDULE $CRON_CMD"

echo -e "\n${YELLOW}📝 Entry cron da aggiungere:${NC}"
echo -e "${GREEN}$CRON_ENTRY${NC}"
echo -e "\nQuesto eseguirà l'estrazione ${YELLOW}$CRON_DESC${NC}"
echo -e "I log saranno salvati in: ${YELLOW}$LOG_FILE${NC}"

# Chiedi conferma
read -p $'\n'"Vuoi aggiungere questa entry al crontab? (s/n) [s]: " confirm
confirm=${confirm:-s}

if [[ $confirm =~ ^[Ss]$ ]]; then
    # Backup crontab attuale
    crontab -l > /tmp/crontab.backup 2>/dev/null

    # Aggiungi nuova entry
    (crontab -l 2>/dev/null | grep -v "estrai_consumi_spiaggia.py"; echo "$CRON_ENTRY") | crontab -

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ Cron configurato con successo!${NC}"
        echo -e "   L'estrazione avverrà automaticamente $CRON_DESC"
        echo -e "\n${YELLOW}📋 Comandi utili:${NC}"
        echo "   - Visualizza cron: crontab -l"
        echo "   - Modifica cron: crontab -e"
        echo "   - Vedi ultimi log: tail -f $LOG_FILE"
        echo "   - Test manuale: cd $SCRIPT_DIR && python3 estrai_consumi_spiaggia.py"
    else
        echo -e "${RED}❌ Errore nella configurazione del cron${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}⚠️  Cron non configurato${NC}"
    echo "Per configurarlo manualmente, esegui:"
    echo "crontab -e"
    echo "e aggiungi la riga:"
    echo "$CRON_ENTRY"
fi

# Crea script di monitoraggio
MONITOR_SCRIPT="$SCRIPT_DIR/monitor_consumi.sh"
cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Script di monitoraggio per estrazione consumi

LOG_FILE="$HOME/logs/consumi_spiaggia.log"
echo "📊 Monitoraggio Estrazione Consumi Spiaggia"
echo "==========================================="
echo "Log file: $LOG_FILE"
echo ""

# Mostra ultime 5 esecuzioni
echo "🕐 Ultime 5 esecuzioni:"
grep "Estrazione completa" "$LOG_FILE" 2>/dev/null | tail -5

echo ""
echo "📧 Email processate oggi:"
grep "$(date +%Y-%m-%d)" "$LOG_FILE" 2>/dev/null | grep "Email processate"

echo ""
echo "❌ Ultimi errori:"
grep -i "error\|errore" "$LOG_FILE" 2>/dev/null | tail -5

echo ""
echo "📈 Statistiche:"
echo "- Totale esecuzioni: $(grep -c "Estrazione completa" "$LOG_FILE" 2>/dev/null)"
echo "- Errori totali: $(grep -ic "error\|errore" "$LOG_FILE" 2>/dev/null)"

echo ""
echo "Premi Ctrl+C per uscire, o attendi per vedere log in tempo reale..."
echo ""
tail -f "$LOG_FILE"
EOF

chmod +x "$MONITOR_SCRIPT"

echo -e "\n${GREEN}✅ Setup completato!${NC}"
echo -e "\n${YELLOW}📋 Riepilogo:${NC}"
echo "- Automazione: $CRON_DESC"
echo "- Log file: $LOG_FILE"
echo "- Monitor: $MONITOR_SCRIPT"
echo -e "\n${GREEN}🎉 Il sistema è ora completamente automatizzato!${NC}"
