#!/bin/bash

# Script wrapper per eseguire l'estrazione consumi dalla directory corretta
# Questo script gestisce i percorsi e l'ambiente per l'esecuzione automatica

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directory di base dove si trovano credentials.json e token.pickle
WORK_DIR="/Users/stefanodellapietra/Documents"

# Directory dello script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# File di log
LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/cron_$(date +%Y%m%d_%H%M%S).log"

# Funzione per logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Header del log
echo "========================================" > "${LOG_FILE}"
log "INIZIO ESTRAZIONE CONSUMI SPIAGGIA"
log "Script directory: ${SCRIPT_DIR}"
log "Working directory: ${WORK_DIR}"
echo "========================================" >> "${LOG_FILE}"

# Verifica che esistano i file necessari
if [ ! -f "${WORK_DIR}/credentials.json" ]; then
    log "❌ ERRORE: File credentials.json non trovato in ${WORK_DIR}"
    exit 1
fi

# Cambia alla directory di lavoro
cd "${WORK_DIR}" || {
    log "❌ ERRORE: Impossibile accedere alla directory ${WORK_DIR}"
    exit 1
}

# Attiva l'ambiente virtuale se esiste
VENV_PATH="/Users/stefanodellapietra/.virtualenvs/hotelops_env"
if [ -d "${VENV_PATH}" ]; then
    log "Attivazione ambiente virtuale..."
    source "${VENV_PATH}/bin/activate"
else
    log "⚠️  Ambiente virtuale non trovato, uso Python di sistema"
fi

# Verifica che Python sia disponibile
if ! command -v python3 &> /dev/null; then
    log "❌ ERRORE: Python3 non trovato"
    exit 1
fi

# Mostra versione Python
PYTHON_VERSION=$(python3 --version)
log "Python: ${PYTHON_VERSION}"

# Esegui lo script di estrazione
log "Avvio estrazione dati..."
echo "----------------------------------------" >> "${LOG_FILE}"

# Esegui lo script e cattura output
python3 "${SCRIPT_DIR}/estrai_consumi_spiaggia.py" 2>&1 | tee -a "${LOG_FILE}"

# Cattura exit code
EXIT_CODE=${PIPESTATUS[0]}

echo "----------------------------------------" >> "${LOG_FILE}"

if [ ${EXIT_CODE} -eq 0 ]; then
    log "✅ Estrazione completata con successo"

    # Conta le nuove email processate dal log
    NEW_EMAILS=$(grep -c "✅ Dati estratti" "${LOG_FILE}" || echo "0")
    DUPLICATES=$(grep -c "⏭️  Email già processata" "${LOG_FILE}" || echo "0")

    log "📊 Riepilogo:"
    log "   - Nuove email processate: ${NEW_EMAILS}"
    log "   - Duplicati evitati: ${DUPLICATES}"
else
    log "❌ ERRORE: Estrazione fallita (exit code: ${EXIT_CODE})"

    # Invia notifica di errore (opzionale)
    # echo "Errore nell'estrazione consumi. Controlla ${LOG_FILE}" | mail -s "ERRORE: Estrazione Consumi" admin@example.com
fi

log "FINE ESTRAZIONE"
echo "========================================" >> "${LOG_FILE}"

# Mantieni solo gli ultimi 30 log
log "Pulizia vecchi log..."
find "${LOG_DIR}" -name "cron_*.log" -type f -mtime +30 -delete

# Se eseguito da cron e c'è stato un errore, stampa l'ultimo log per email
if [ -n "${CRON}" ] && [ ${EXIT_CODE} -ne 0 ]; then
    echo "Errore nell'estrazione. Ultimi 50 righe del log:"
    tail -50 "${LOG_FILE}"
fi

exit ${EXIT_CODE}
