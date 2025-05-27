# 🚀 DBLogiX - Sistema Completo di Build e Distribuzione

## ✨ Panoramica

Questo sistema ti permette di compilare DBLogiX in un'applicazione Windows standalone con:

- 🔐 **Codice Python completamente crittografato** (non accessibile ai clienti)
- 🛠️ **Servizio Windows automatico** (si avvia con il sistema)
- 🌐 **HTTPS obbligatorio** (necessario per lo scanner barcode)
- 🔥 **Firewall configurato automaticamente**
- 💾 **Installer Windows professionale**
- 📦 **Pacchetto portable** per distribuzione manuale

## 🎯 Avvio Rapido

### Windows (Raccomandato)

Fai doppio clic su:
```
quick_build.bat
```

### Comando diretto

```bash
python build_and_package.py
```

## 📋 File Creati per il Build

| File | Descrizione |
|------|-------------|
| `dblogix.spec` | Configurazione PyInstaller con crittografia |
| `main_service.py` | Entry point ottimizzato per servizio Windows |
| `dblogix_service.py` | Gestione completa servizio Windows |
| `dblogix_installer.iss` | Script InnoSetup per installer Windows |
| `build_and_package.py` | Script automatico completo |
| `quick_build.bat` | Script Windows per build rapido |
| `BUILD_INSTRUCTIONS.md` | Istruzioni dettagliate complete |

## 🔧 Requisiti

### Software
- **Python 3.8+** con pip
- **PyInstaller 6.3.0+**
- **InnoSetup 6** (per installer Windows)

### Installazione Automatica
Il script `quick_build.bat` installa automaticamente:
- Tutte le dipendenze Python
- PyInstaller
- Controlla i prerequisiti

## 📁 Output del Build

Dopo il build avrai:

```
📦 DBLogiX_Build_Output/
├── 📂 dist/DBLogiX/                    # ✅ App compilata e pronta
│   ├── 🔐 DBLogiX.exe                 # Eseguibile crittografato  
│   ├── 🛠️ dblogix_service.py          # Gestore servizio
│   ├── 📄 config.py                   # Configurazione
│   ├── 🔐 _internal/                  # Librerie crittografate
│   └── 📋 INSTALL.md                  # Istruzioni installazione
├── 📂 installer_output/                # ✅ Installer Windows
│   └── 💾 DBLogiX_Setup_1.0.0.exe    # Installer automatico
└── 📂 release_package/                 # ✅ Pacchetto portable
    └── 📦 DBLogiX_Portable_[data].zip # Archivio completo
```

## 🎯 Distribuzione ai Clienti

### Opzione 1: Installer Automatico (Raccomandato)
Distribuisci solo:
```
💾 DBLogiX_Setup_1.0.0.exe
```

L'installer configura automaticamente tutto:
- ✅ Servizio Windows
- ✅ Firewall  
- ✅ Certificati SSL
- ✅ Avvio automatico

### Opzione 2: Pacchetto Portable
Distribuisci:
```
📦 DBLogiX_Portable_[data].zip
```

Il cliente deve estrarre e eseguire manualmente i comandi di installazione.

## 🔐 Sicurezza Garantita

### Protezione del Codice
- ✅ **Crittografia PyInstaller**: Codice Python non leggibile
- ✅ **Bytecode protetto**: File .pyc incorporati e crittografati  
- ✅ **Dipendenze nascoste**: Tutto incluso nel binario
- ✅ **No file .py**: Nessun file sorgente distribuito

### Verifica Protezione
```bash
# I file .py NON sono presenti nell'output finale
# Solo l'eseguibile .exe e file di configurazione
```

## 🌐 Accesso Post-Installazione

Una volta installato, l'applicazione è accessibile via:

**🌐 URL:** https://localhost:5000

**⚠️ IMPORTANTE:** Funziona SOLO in HTTPS (richiesto per scanner barcode)

## 🛠️ Gestione Servizio

### Nel PC del Cliente

```cmd
# Stato servizio
python dblogix_service.py status

# Avvia servizio  
python dblogix_service.py start

# Ferma servizio
python dblogix_service.py stop

# Riavvia servizio
python dblogix_service.py restart
```

## 📊 Monitoraggio

### Log Disponibili
```
📁 logs/
├── 📄 dblogix_service.log    # Log servizio Windows
└── 📄 dblogix.log           # Log applicazione Flask
```

### Controllo Stato
```cmd
# Verifica servizio attivo
sc query DBLogiX

# Verifica porta HTTPS
netstat -an | findstr :5000

# Test connessione
curl -k https://localhost:5000
```

## 🔄 Processo di Aggiornamento

1. **Build nuova versione**:
   ```bash
   python build_and_package.py
   ```

2. **Distribuisci nuovo installer** o pacchetto

3. **Nel PC cliente**:
   - Ferma servizio: `python dblogix_service.py stop`
   - Sostituisci file (mantieni `config.py`)
   - Riavvia servizio: `python dblogix_service.py start`

## 🆘 Supporto

### Debug Problemi
```cmd
# Log in tempo reale
tail -f logs\dblogix_service.log

# Test manuale applicazione
python main_service.py

# Verifica certificati SSL
dir cert.pem key.pem

# Rigenera certificati se necessario
python generate_certs.py
```

### Problemi Comuni

| Problema | Soluzione |
|----------|-----------|
| Servizio non si avvia | Controlla `logs\dblogix_service.log` |
| Errore HTTPS | Rigenera certificati: `python generate_certs.py` |
| Connessione rifiutata | Configura firewall: `python dblogix_service.py firewall` |
| Errore database | Verifica `config.py` |

## 📚 Documentazione Completa

Per dettagli completi, consulta:
- 📖 `BUILD_INSTRUCTIONS.md` - Istruzioni dettagliate
- 📋 `dist/DBLogiX/INSTALL.md` - Guida installazione cliente

## ✅ Checklist Pre-Distribuzione

- [ ] Build completato senza errori
- [ ] Installer testato su PC pulito
- [ ] Servizio si avvia automaticamente
- [ ] HTTPS accessibile su porta 5000
- [ ] Scanner barcode funziona in HTTPS
- [ ] Database connectivity OK
- [ ] Log generati correttamente
- [ ] Firewall configurato
- [ ] Certificati SSL generati

---

🎉 **Congratulazioni!** Hai ora un sistema completo per distribuire DBLogiX ai tuoi clienti con codice Python protetto e configurazione automatica!

**DBLogiX** © 2024 