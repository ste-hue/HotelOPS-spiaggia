# Sistema Estrazione Consumi Spiaggia

Sistema completamente automatizzato per l'estrazione dei dati di consumo dalla spiaggia Panorama Beach tramite email e aggiornamento automatico di Google Sheets.

## ✅ Stato del Sistema

**IL SISTEMA È COMPLETAMENTE OPERATIVO E AUTOMATICO**

- 🤖 **Automazione attiva**: Ogni notte alle 2:00
- 📧 **Email processate**: Solo nuove email (nessun duplicato)
- 📊 **Google Sheet**: Aggiornato automaticamente
- 🔒 **Accesso pubblico**: Chiunque con il link può visualizzare

## 🚀 Cosa Fa il Sistema

1. **Ogni notte alle 2:00** si attiva automaticamente
2. **Controlla** la casella email `magazzino@panoramagroup.it`
3. **Trova** le email con label "consumi Spiaggia"
4. **Processa** solo le nuove email (evita duplicati)
5. **Estrae** tutti i dati dal report HTML
6. **Aggiorna** il Google Sheet con i nuovi dati

## 📊 Dati Estratti e Organizzati

### Foglio "Totali"
- Data report
- Periodo (dal/al con timestamp completo)
- Numero incassi e totale in €
- Numero scontrini e totale in €

### Foglio "Prodotti" 
- 192+ prodotti con dettagli completi
- Quantità vendute
- Importi
- Reparto di appartenenza

### Foglio "Reparti"
- Performance per categoria
- Totali aggregati per reparto

### Foglio "Movimentazioni"
- Log di tutte le cancellazioni/modifiche
- Data/ora, operatore, tipo operazione
- Articolo e valore modificato

## 🔗 Google Sheet

**Link pubblico (sola lettura):**
https://docs.google.com/spreadsheets/d/1QVjRqUUmKUIBQ5F2EXaytEVCGqrK6zcjRsxddSDv1jA

- **Accesso**: Chiunque con il link può visualizzare
- **Aggiornamento**: Automatico ogni notte
- **Ordinamento**: Per data (più recenti prima)

## 🛠️ Componenti del Sistema

### File Principali
- `sistema_consumi_ottimizzato.py` - Script principale
- `database_consumi.json` - Database locale (previene duplicati)
- `com.panoramagroup.consumi.plist` - Configurazione automazione macOS

### Automazione
- **Scheduler**: launchd (macOS nativo)
- **Orario**: Ogni notte alle 2:00
- **Log**: `launchd_stdout.log` e `launchd_stderr.log`

## 📌 Comandi Utili

### Verifica stato automazione
```bash
launchctl list | grep panoramagroup
```

### Esecuzione manuale (se necessario)
```bash
python3 sistema_consumi_ottimizzato.py
```

### Visualizza log in tempo reale
```bash
tail -f launchd_*.log
```

### Reset completo sistema
```bash
./reset_sistema.sh
```

## 🔧 Manutenzione

Il sistema è progettato per essere **completamente autonomo**. Non richiede interventi manuali.

### Cosa succede automaticamente:
- ✅ Processa solo nuove email
- ✅ Evita duplicati
- ✅ Gestisce errori temporanei
- ✅ Mantiene database locale di backup
- ✅ Aggiorna Google Sheet incrementalmente

### Monitoraggio:
- I log mostrano l'attività giornaliera
- Il database locale tiene traccia di tutto
- Google Sheet mostra sempre i dati più recenti

## 🎯 Risultato Finale

Ogni mattina troverai nel Google Sheet:
- **Dati aggiornati** del giorno precedente
- **Storico completo** di tutti i consumi
- **Nessun duplicato** o dato mancante
- **Ordinamento automatico** per data

**Non è richiesta alcuna azione manuale. Il sistema funziona autonomamente 24/7.**

## 📞 Supporto

Per assistenza tecnica:
- Email: stefano@panoramagroup.it
- Sistema: HotelOps Suite

---

*Sistema sviluppato e configurato il 16/07/2025 - Completamente operativo e automatico*