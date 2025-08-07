#!/bin/bash

# Setup Automazione Completa - Estrazione TUTTI i Dati Consumi Spiaggia
# Versione: 2.0
# Autore: HotelOPS Development Team

echo "🚀 Setup Automazione COMPLETA Estrazione Consumi Spiaggia"
echo "=========================================================="
echo "✨ Questo setup configura l'estrazione di TUTTI i dati:"
echo "   - Totali"
echo "   - Prodotti dettagliati"
echo "   - Reparti"
echo "   - Movimentazioni"
echo "   - Addetti"
echo "   - Ambienti"
echo ""

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verifica se siamo nella directory corretta
if [ ! -f "estrai_consumi_completo.py" ]; then
    echo -e "${RED}❌ Errore: File estrai_consumi_completo.py non trovato!${NC}"
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

# Verifica service account
if [ ! -f "HotelOps Suite.json" ]; then
    echo -e "${RED}❌ File HotelOps Suite.json non trovato!${NC}"
    echo "   Il file del service account è necessario per l'autenticazione"
    exit 1
fi

# Test esecuzione script completo
echo -e "\n${YELLOW}🧪 Test esecuzione script completo...${NC}"
echo "   Premi Ctrl+C per interrompere il test se necessario"
echo ""

# Esegui un test limitato
python3 -c "
from estrai_consumi_completo import ConsumiSpiaggiaCompletExtractor
try:
    extractor = ConsumiSpiaggiaCompletExtractor()
    print('✅ Inizializzazione OK')
except Exception as e:
    print(f'❌ Errore: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Errore nell'inizializzazione dello script${NC}"
    exit 1
fi

# Creazione entry cron
echo -e "\n${BLUE}📊 Configurazione Automazione Completa${NC}"
echo -e "${YELLOW}⏰ Quando vuoi eseguire l'estrazione COMPLETA?${NC}"
echo ""
echo "Raccomandazione: L'estrazione completa richiede più tempo,"
echo "quindi è consigliabile eseguirla in orari di basso traffico."
echo ""
echo "1) Ogni notte alle 02:00 (consigliato)"
echo "2) Ogni giorno alle 06:00"
echo "3) Ogni giorno alle 23:00"
echo "4) Due volte al giorno (02:00 e 14:00)"
echo "5) Personalizzato"
read -p "Scelta (1-5) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        CRON_SCHEDULE="0 2 * * *"
        CRON_DESC="ogni notte alle 02:00"
        ;;
    2)
        CRON_SCHEDULE="0 6 * * *"
        CRON_DESC="ogni giorno alle 06:00"
        ;;
    3)
        CRON_SCHEDULE="0 23 * * *"
        CRON_DESC="ogni giorno alle 23:00"
        ;;
    4)
        CRON_SCHEDULE="0 2,14 * * *"
        CRON_DESC="due volte al giorno (02:00 e 14:00)"
        ;;
    5)
        read -p "Inserisci schedule cron personalizzato: " CRON_SCHEDULE
        CRON_DESC="personalizzato: $CRON_SCHEDULE"
        ;;
    *)
        CRON_SCHEDULE="0 2 * * *"
        CRON_DESC="ogni notte alle 02:00"
        ;;
esac

# Log file
LOG_FILE="$HOME/logs/consumi_spiaggia_completo.log"
LOG_DIR=$(dirname "$LOG_FILE")

# Crea directory logs se non esiste
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✅ Creata directory logs: $LOG_DIR${NC}"
fi

# Costruisci comando cron
CRON_CMD="cd $SCRIPT_DIR && $PYTHON_PATH estrai_consumi_completo.py >> $LOG_FILE 2>&1"
CRON_ENTRY="$CRON_SCHEDULE $CRON_CMD"

echo -e "\n${YELLOW}📝 Entry cron da aggiungere:${NC}"
echo -e "${GREEN}$CRON_ENTRY${NC}"
echo -e "\nQuesto eseguirà l'estrazione COMPLETA ${YELLOW}$CRON_DESC${NC}"
echo -e "I log saranno salvati in: ${YELLOW}$LOG_FILE${NC}"

# Mostra cosa verrà estratto
echo -e "\n${BLUE}📋 Dati che verranno estratti automaticamente:${NC}"
echo "   ✓ Totali giornalieri (incassi, scontrini, pagamenti, ecc.)"
echo "   ✓ Dettaglio completo di TUTTI i prodotti venduti"
echo "   ✓ Reparti con quantità e totali"
echo "   ✓ Movimentazioni (cancellazioni, modifiche)"
echo "   ✓ Performance degli addetti"
echo "   ✓ Statistiche per ambiente"
echo ""
echo "   📊 Il database Google Sheets avrà 6 fogli separati"
echo "      per una consultazione facile e completa!"

# Chiedi conferma
echo ""
read -p "Vuoi configurare questa automazione completa? (s/n) [s]: " confirm
confirm=${confirm:-s}

if [[ $confirm =~ ^[Ss]$ ]]; then
    # Backup crontab attuale
    crontab -l > /tmp/crontab.backup.completo 2>/dev/null

    # Rimuovi eventuali entry precedenti per estrai_consumi_completo.py
    (crontab -l 2>/dev/null | grep -v "estrai_consumi_completo.py"; echo "$CRON_ENTRY") | crontab -

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ Automazione completa configurata con successo!${NC}"
        echo -e "   L'estrazione COMPLETA avverrà automaticamente $CRON_DESC"

        # Crea script di monitoraggio specifico per versione completa
        MONITOR_SCRIPT="$SCRIPT_DIR/monitor_completo.sh"
        cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Monitoraggio Estrazione Completa Consumi Spiaggia

LOG_FILE="$HOME/logs/consumi_spiaggia_completo.log"
echo "📊 Monitoraggio Estrazione COMPLETA Consumi Spiaggia"
echo "===================================================="
echo "Log file: $LOG_FILE"
echo ""

# Mostra ultima esecuzione
echo "🕐 Ultima esecuzione:"
grep "Estrazione COMPLETA" "$LOG_FILE" 2>/dev/null | tail -1

echo ""
echo "📈 Statistiche ultima esecuzione:"
tail -50 "$LOG_FILE" 2>/dev/null | grep -E "Foglio|righe|record" | tail -10

echo ""
echo "❌ Ultimi errori (se presenti):"
grep -i "error\|errore" "$LOG_FILE" 2>/dev/null | tail -5

echo ""
echo "📅 Date processate di recente:"
grep "Date più recenti" -A 5 "$LOG_FILE" 2>/dev/null | tail -6

echo ""
echo "Premi Ctrl+C per uscire, o attendi per vedere log in tempo reale..."
echo ""
tail -f "$LOG_FILE"
EOF

        chmod +x "$MONITOR_SCRIPT"

        echo -e "\n${YELLOW}📋 Comandi utili:${NC}"
        echo "   - Test manuale: cd $SCRIPT_DIR && python3 estrai_consumi_completo.py"
        echo "   - Monitoraggio: $MONITOR_SCRIPT"
        echo "   - Vedi cron: crontab -l"
        echo "   - Log completi: tail -f $LOG_FILE"

        echo -e "\n${BLUE}🔗 Link al Google Sheet:${NC}"
        echo "   https://docs.google.com/spreadsheets/d/1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"

        # Chiedi se vuole eseguire subito una prima estrazione
        echo ""
        read -p "Vuoi eseguire subito una prima estrazione completa? (s/n) [n]: " run_now
        run_now=${run_now:-n}

        if [[ $run_now =~ ^[Ss]$ ]]; then
            echo -e "\n${YELLOW}🚀 Esecuzione prima estrazione completa...${NC}"
            cd "$SCRIPT_DIR" && python3 estrai_consumi_completo.py
        fi

    else
        echo -e "${RED}❌ Errore nella configurazione del cron${NC}"
        exit 1
    fi
else
    echo -e "\n${YELLOW}⚠️  Automazione non configurata${NC}"
    echo "Per configurarla manualmente, esegui:"
    echo "crontab -e"
    echo "e aggiungi la riga:"
    echo "$CRON_ENTRY"
fi

# Crea README per la versione completa
README_COMPLETO="$SCRIPT_DIR/README_COMPLETO.md"
cat > "$README_COMPLETO" << 'EOF'
# 📊 Sistema Completo Estrazione Consumi Spiaggia

## 🎯 Cosa fa questo sistema

Estrae AUTOMATICAMENTE **TUTTI** i dati dalle email dei report della spiaggia:

### 📈 Dati Estratti:
1. **Totali** - Incassi, scontrini, pagamenti, ordini
2. **Prodotti** - Lista completa con quantità e prezzi
3. **Reparti** - Performance per categoria
4. **Movimentazioni** - Cancellazioni e modifiche
5. **Addetti** - Performance del personale
6. **Ambienti** - Statistiche per area

### 🔄 Automazione
- Esecuzione automatica ogni notte
- Nessun intervento manuale richiesto
- Accumula dati storici automaticamente

### 📱 Google Sheet
Il database è organizzato in 6 fogli:
- `Totali` - Dashboard principale
- `Prodotti` - Dettaglio vendite
- `Reparti` - Analisi categorie
- `Movimentazioni` - Log modifiche
- `Addetti` - Performance staff
- `Ambienti` - Analisi aree

### 🛠️ Manutenzione
- Monitor: `./monitor_completo.sh`
- Test: `python3 estrai_consumi_completo.py`
- Log: `~/logs/consumi_spiaggia_completo.log`

### 🚨 In caso di problemi
1. Controlla i log
2. Verifica connessione internet
3. Controlla permessi Google API

EOF

echo -e "\n${GREEN}✅ Setup completato!${NC}"
echo -e "\n${YELLOW}📋 Riepilogo Sistema Completo:${NC}"
echo "- Script: estrai_consumi_completo.py"
echo "- Automazione: $CRON_DESC"
echo "- Log: $LOG_FILE"
echo "- Monitor: $MONITOR_SCRIPT"
echo "- README: $README_COMPLETO"
echo -e "\n${GREEN}🎉 Il sistema di estrazione COMPLETA è ora operativo!${NC}"
echo -e "${BLUE}📊 Tutti i dati saranno estratti automaticamente ogni giorno!${NC}"
