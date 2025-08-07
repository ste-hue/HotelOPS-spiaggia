#!/bin/bash

# Setup Automazione Estrazione Consumi Spiaggia V2
# Versione stabile e funzionante con parsing HTML
# Autore: HotelOPS Development Team

echo "🚀 Setup Automazione Estrazione Consumi Spiaggia V2"
echo "==================================================="
echo "✨ Sistema completo per estrazione automatica dati:"
echo "   - Totali giornalieri"
echo "   - Dettaglio completo prodotti"
echo "   - Reparti con performance"
echo "   - Movimentazioni (cancellazioni/modifiche)"
echo ""

# Colori per output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verifica se siamo nella directory corretta
if [ ! -f "estrai_consumi_v2.py" ]; then
    echo -e "${RED}❌ Errore: File estrai_consumi_v2.py non trovato!${NC}"
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
python3 -c "import google.auth; import googleapiclient; import bs4" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Dipendenze mancanti! Installa con:${NC}"
    echo "   pip install -r requirements.txt"
    echo "   (BeautifulSoup4 è necessario per il parsing HTML)"
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

# Test esecuzione script
echo -e "\n${YELLOW}🧪 Test connessione e permessi...${NC}"
python3 -c "
from estrai_consumi_v2 import ConsumiExtractorV2
try:
    extractor = ConsumiExtractorV2()
    print('✅ Connessione e permessi OK')
except Exception as e:
    print(f'❌ Errore: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Errore nella connessione${NC}"
    exit 1
fi

# Configurazione Cron
echo -e "\n${BLUE}⏰ Configurazione Automazione${NC}"
echo "Il sistema processerà automaticamente TUTTE le email con label 'consumi Spiaggia'"
echo "e aggiornerà il database Google Sheets con tutti i dati estratti."
echo ""
echo "Quando vuoi eseguire l'estrazione automatica?"
echo "1) Ogni notte alle 02:00 (consigliato)"
echo "2) Ogni giorno alle 08:00"
echo "3) Ogni giorno alle 20:00"
echo "4) Due volte al giorno (08:00 e 20:00)"
echo "5) Ogni 6 ore"
echo "6) Personalizzato"
read -p "Scelta (1-6) [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        CRON_SCHEDULE="0 2 * * *"
        CRON_DESC="ogni notte alle 02:00"
        ;;
    2)
        CRON_SCHEDULE="0 8 * * *"
        CRON_DESC="ogni giorno alle 08:00"
        ;;
    3)
        CRON_SCHEDULE="0 20 * * *"
        CRON_DESC="ogni giorno alle 20:00"
        ;;
    4)
        CRON_SCHEDULE="0 8,20 * * *"
        CRON_DESC="due volte al giorno (08:00 e 20:00)"
        ;;
    5)
        CRON_SCHEDULE="0 */6 * * *"
        CRON_DESC="ogni 6 ore"
        ;;
    6)
        read -p "Inserisci schedule cron personalizzato: " CRON_SCHEDULE
        CRON_DESC="personalizzato: $CRON_SCHEDULE"
        ;;
    *)
        CRON_SCHEDULE="0 2 * * *"
        CRON_DESC="ogni notte alle 02:00"
        ;;
esac

# Log file
LOG_FILE="$HOME/logs/consumi_spiaggia_v2.log"
LOG_DIR=$(dirname "$LOG_FILE")

# Crea directory logs se non esiste
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
    echo -e "${GREEN}✅ Creata directory logs: $LOG_DIR${NC}"
fi

# Costruisci comando cron
CRON_CMD="cd $SCRIPT_DIR && $PYTHON_PATH estrai_consumi_v2.py >> $LOG_FILE 2>&1"
CRON_ENTRY="$CRON_SCHEDULE $CRON_CMD"

echo -e "\n${YELLOW}📝 Entry cron da aggiungere:${NC}"
echo -e "${GREEN}$CRON_ENTRY${NC}"
echo -e "\nQuesto eseguirà l'estrazione ${YELLOW}$CRON_DESC${NC}"
echo -e "I log saranno salvati in: ${YELLOW}$LOG_FILE${NC}"

# Mostra cosa verrà estratto
echo -e "\n${BLUE}📊 Dati che verranno estratti automaticamente:${NC}"
echo "   ✓ Totali giornalieri completi"
echo "   ✓ Tutti i prodotti venduti con quantità e prezzi"
echo "   ✓ Performance per reparto"
echo "   ✓ Tutte le movimentazioni (cancellazioni, modifiche)"
echo ""
echo "   Il database Google Sheets verrà aggiornato con 4 fogli:"
echo "   • Totali - Dashboard principale"
echo "   • Prodotti - Dettaglio vendite"
echo "   • Reparti - Analisi per categoria"
echo "   • Movimentazioni - Log modifiche ordini"

# Chiedi conferma
echo ""
read -p "Vuoi configurare questa automazione? (s/n) [s]: " confirm
confirm=${confirm:-s}

if [[ $confirm =~ ^[Ss]$ ]]; then
    # Backup crontab attuale
    crontab -l > /tmp/crontab.backup.v2 2>/dev/null

    # Rimuovi eventuali entry precedenti per estrai_consumi_v2.py
    (crontab -l 2>/dev/null | grep -v "estrai_consumi_v2.py"; echo "$CRON_ENTRY") | crontab -

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ Automazione configurata con successo!${NC}"
        echo -e "   L'estrazione avverrà automaticamente $CRON_DESC"

        # Crea script di monitoraggio
        MONITOR_SCRIPT="$SCRIPT_DIR/monitor_v2.sh"
        cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Monitoraggio Estrazione Consumi Spiaggia V2

LOG_FILE="$HOME/logs/consumi_spiaggia_v2.log"
echo "📊 Monitoraggio Estrazione Consumi V2"
echo "====================================="
echo "Log file: $LOG_FILE"
echo ""

# Mostra ultima esecuzione
echo "🕐 Ultima esecuzione:"
grep "Estrazione Consumi Spiaggia V2" "$LOG_FILE" 2>/dev/null | tail -1

echo ""
echo "📈 Statistiche ultima esecuzione:"
tail -50 "$LOG_FILE" 2>/dev/null | grep -E "Email processate|Prodotti:|Reparti:|Movimentazioni:" | tail -10

echo ""
echo "📅 Date processate di recente:"
grep "Date più recenti" -A 5 "$LOG_FILE" 2>/dev/null | tail -6

echo ""
echo "❌ Ultimi errori (se presenti):"
grep -i "error\|errore" "$LOG_FILE" 2>/dev/null | tail -5

echo ""
echo "🔄 Per vedere i log in tempo reale, premi Invio..."
read
tail -f "$LOG_FILE"
EOF

        chmod +x "$MONITOR_SCRIPT"

        echo -e "\n${YELLOW}📋 Comandi utili:${NC}"
        echo "   - Test manuale: cd $SCRIPT_DIR && python3 estrai_consumi_v2.py"
        echo "   - Monitoraggio: $MONITOR_SCRIPT"
        echo "   - Vedi cron: crontab -l"
        echo "   - Log completi: tail -f $LOG_FILE"

        echo -e "\n${BLUE}🔗 Link al Google Sheet:${NC}"
        echo "   https://docs.google.com/spreadsheets/d/1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA"

        # Chiedi se vuole eseguire subito una prima estrazione
        echo ""
        read -p "Vuoi eseguire subito una prima estrazione? (s/n) [s]: " run_now
        run_now=${run_now:-s}

        if [[ $run_now =~ ^[Ss]$ ]]; then
            echo -e "\n${YELLOW}🚀 Esecuzione prima estrazione...${NC}"
            cd "$SCRIPT_DIR" && python3 estrai_consumi_v2.py
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

# Crea documentazione finale
DOC_FILE="$SCRIPT_DIR/SISTEMA_FUNZIONANTE.md"
cat > "$DOC_FILE" << 'EOF'
# 🎉 Sistema di Estrazione Consumi Spiaggia V2

## ✅ Sistema Completamente Funzionante

### 🚀 Cosa fa questo sistema:
Estrae automaticamente TUTTI i dati dalle email HTML dei report della spiaggia:

1. **Totali** - Incassi, scontrini, pagamenti, ordini per tipo
2. **Prodotti** - Lista completa di tutti i prodotti venduti con:
   - Nome prodotto
   - Reparto di appartenenza
   - Quantità vendute
   - Numero ordini
   - Totale incassato
3. **Reparti** - Performance per categoria con totali
4. **Movimentazioni** - Log di tutte le cancellazioni e modifiche

### 📊 Database Google Sheets
Il sistema aggiorna automaticamente 4 fogli:
- `Totali` - Dashboard con tutti i KPI giornalieri
- `Prodotti` - Dettaglio di ogni singolo prodotto venduto
- `Reparti` - Analisi per categoria merceologica
- `Movimentazioni` - Tracciamento modifiche ordini

### 🔄 Automazione
- Esecuzione automatica programmata
- Nessun intervento manuale richiesto
- Accumula dati storici automaticamente
- Processa TUTTE le email con label "consumi Spiaggia"

### 🛠️ Manutenzione
- **Test manuale**: `python3 estrai_consumi_v2.py`
- **Monitoraggio**: `./monitor_v2.sh`
- **Log**: `~/logs/consumi_spiaggia_v2.log`
- **Cron**: `crontab -l`

### 📈 Benefici
- Dati sempre aggiornati
- Storico completo disponibile
- Analisi dettagliate possibili
- Zero effort giornaliero

### 🆘 Supporto
In caso di problemi:
1. Controlla i log con `./monitor_v2.sh`
2. Verifica la connessione internet
3. Controlla che le email abbiano la label corretta
4. Verifica i permessi del service account

---
Sistema sviluppato da HotelOPS Development Team
EOF

echo -e "\n${GREEN}✅ Setup completato con successo!${NC}"
echo -e "\n${YELLOW}📋 Riepilogo:${NC}"
echo "- Script: estrai_consumi_v2.py"
echo "- Automazione: $CRON_DESC"
echo "- Log: $LOG_FILE"
echo "- Monitor: $MONITOR_SCRIPT"
echo "- Documentazione: $DOC_FILE"
echo -e "\n${GREEN}🎉 Il sistema è ora completamente automatizzato!${NC}"
echo -e "${BLUE}Non dovrai più fare nulla manualmente!${NC}"
