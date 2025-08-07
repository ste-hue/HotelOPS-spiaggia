# 🤖 Opzioni di Automazione per Estrazione Consumi Spiaggia

## Confronto delle Opzioni

### 1. **Google Cloud Functions** ☁️
**Pro:**
- ✅ Integrazione nativa con Gmail e Google Sheets
- ✅ Trigger automatici su eventi (es. nuova email)
- ✅ Serverless (nessun server da gestire)
- ✅ 2 milioni di invocazioni gratis al mese
- ✅ Può essere triggerato da Cloud Scheduler

**Contro:**
- ❌ Richiede setup Google Cloud Platform
- ❌ Più complesso da configurare inizialmente
- ❌ Richiede conversione codice per ambiente cloud

**Costo:** Gratis per uso normale (< 2M invocazioni/mese)

**Setup richiesto:**
```python
# main.py per Cloud Function
import functions_framework
from estrai_consumi_spiaggia import ConsumiSpiaggiaExtractor

@functions_framework.http
def extract_consumi(request):
    extractor = ConsumiSpiaggiaExtractor()
    extractor.process_all_emails()
    return {'status': 'completed'}, 200
```

---

### 2. **n8n** 🔄
**Pro:**
- ✅ Interfaccia visuale drag-and-drop
- ✅ Facile da configurare senza codice
- ✅ Può inviare notifiche su errori
- ✅ Dashboard per monitoraggio
- ✅ Self-hosted o cloud

**Contro:**
- ❌ Richiede server sempre acceso o abbonamento cloud
- ❌ Overkill per un singolo task
- ❌ Richiede conversione in webhook/API

**Costo:** 
- Self-hosted: costo del server (~5€/mese)
- Cloud: da 20€/mese

**Workflow n8n:**
1. Trigger: Schedule (ogni giorno alle 9:00)
2. HTTP Request: chiama script Python via webhook
3. IF: controlla errori
4. Email/Slack: notifica risultati

---

### 3. **Cron Job** ⏰
**Pro:**
- ✅ Semplicissimo da configurare
- ✅ Nessuna dipendenza esterna
- ✅ Codice resta com'è
- ✅ Controllo totale
- ✅ Gratis se hai già un server

**Contro:**
- ❌ Richiede server/computer sempre acceso
- ❌ Nessun monitoring automatico
- ❌ Gestione manuale degli errori

**Costo:** Gratis (se hai già un server)

**Setup Cron:**
```bash
# Esegui ogni giorno alle 9:00
0 9 * * * cd /path/to/project && /usr/bin/python3 estrai_consumi_spiaggia.py >> /var/log/consumi_spiaggia.log 2>&1

# Oppure ogni 6 ore
0 */6 * * * cd /path/to/project && /usr/bin/python3 estrai_consumi_spiaggia.py
```

---

## 🎯 Raccomandazione

### Per iniziare subito: **Cron Job**
```bash
# 1. Apri crontab
crontab -e

# 2. Aggiungi la riga (esegue ogni giorno alle 8:30)
30 8 * * * cd ~/Desktop/Projects/Companies/INTUR/INTUR_development/HotelOPS/modules/spiaggia/estrazione_consumi && /usr/bin/python3 estrai_consumi_spiaggia.py >> ~/consumi_spiaggia.log 2>&1

# 3. Salva e esci
```

### Per soluzione professionale: **Google Cloud Functions + Cloud Scheduler**

1. **Prepara il codice:**
```bash
# Crea requirements.txt
echo "google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
python-dateutil
functions-framework" > requirements.txt
```

2. **Crea main.py:**
```python
import functions_framework
from estrai_consumi_spiaggia import ConsumiSpiaggiaExtractor

@functions_framework.http
def extract_consumi(request):
    """Cloud Function per estrarre consumi spiaggia."""
    try:
        extractor = ConsumiSpiaggiaExtractor()
        extractor.process_all_emails()
        return {'status': 'success'}, 200
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500
```

3. **Deploy:**
```bash
gcloud functions deploy extract-consumi-spiaggia \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file .env.yaml
```

4. **Schedula con Cloud Scheduler:**
```bash
gcloud scheduler jobs create http consumi-spiaggia-daily \
    --schedule="30 8 * * *" \
    --uri="https://REGION-PROJECT.cloudfunctions.net/extract-consumi-spiaggia" \
    --http-method=GET
```

---

## 📊 Monitoring & Notifiche

### Aggiungi notifiche email per errori:
```python
def send_error_notification(error_message):
    """Invia email in caso di errore."""
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(f"Errore estrazione consumi:\n\n{error_message}")
    msg['Subject'] = 'Errore Estrazione Consumi Spiaggia'
    msg['From'] = 'system@hotelops.it'
    msg['To'] = 'admin@hotelops.it'
    
    # Configura SMTP e invia...
```

### Log strutturati:
```python
import logging
logging.basicConfig(
    filename='consumi_spiaggia.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

## 🚀 Quick Start

**Opzione 1 - Cron Locale (Più Veloce):**
```bash
# Test manuale
python3 estrai_consumi_spiaggia.py

# Aggiungi a cron
crontab -e
# Aggiungi: 30 8 * * * cd /full/path && python3 estrai_consumi_spiaggia.py
```

**Opzione 2 - Cloud Function (Più Affidabile):**
1. Crea progetto Google Cloud
2. Abilita Gmail API e Sheets API
3. Deploy function con codice sopra
4. Configura Cloud Scheduler

**Opzione 3 - n8n (Più Flessibile):**
1. Installa n8n
2. Crea workflow con Schedule trigger
3. Aggiungi Execute Command node
4. Configura notifiche

---

## 💡 Suggerimento Finale

**Per INTUR/HotelOPS**, raccomando:
- **Breve termine**: Cron job su server esistente
- **Lungo termine**: Google Cloud Functions per affidabilità e scalabilità
- **Extra**: Aggiungi dashboard con statistiche giornaliere