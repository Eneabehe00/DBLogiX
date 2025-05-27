# DBLogiX - Istruzioni per Build e Distribuzione

## Overview

Questo documento descrive come compilare DBLogiX in un'applicazione Windows standalone con codice Python crittografato, servizio Windows automatico, e supporto HTTPS.

## Caratteristiche della Build

- ✅ **Codice Python crittografato** tramite PyInstaller
- ✅ **Servizio Windows** automatico con avvio del sistema
- ✅ **HTTPS obbligatorio** con certificati SSL auto-generati
- ✅ **Firewall configurato** automaticamente
- ✅ **Installer Windows** professionale con InnoSetup
- ✅ **Protezione completa** del codice sorgente

## Prerequisiti

### Software Richiesto

1. **Python 3.8+** (testato con Python 3.8-3.11)
   - Scarica da: https://python.org/downloads/
   - ⚠️ Assicurati che sia aggiunto al PATH

2. **PyInstaller 6.3.0+**
   ```bash
   pip install pyinstaller>=6.3.0
   ```

3. **InnoSetup 6**
   - Scarica da: https://jrsoftware.org/isdl.php
   - Installa nella directory predefinita

4. **Dipendenze Python**
   ```bash
   pip install -r requirements.txt
   ```

### File Necessari

Assicurati che questi file esistano nella directory principale:

```
📂 DBLogiX/
├── 📄 main_service.py      # Entry point per il servizio
├── 📄 app.py               # Applicazione Flask principale
├── 📄 models.py            # Modelli database
├── 📄 config.py            # Configurazione
├── 📄 dblogix.spec         # Configurazione PyInstaller
├── 📄 dblogix_installer.iss # Script InnoSetup
├── 📄 dblogix_service.py   # Gestione servizio Windows
├── 📄 generate_certs.py    # Generazione certificati SSL
├── 📄 build_and_package.py # Script automatico di build
├── 📁 templates/           # Template HTML
├── 📁 static/              # File statici
└── 📄 requirements.txt     # Dipendenze Python
```

## Metodi di Build

### Metodo 1: Build Automatico (Raccomandato)

```bash
python build_and_package.py
```

Questo script:
1. Verifica tutti i prerequisiti
2. Pulisce build precedenti
3. Compila con PyInstaller (codice crittografato)
4. Crea l'installer Windows
5. Genera pacchetto portable
6. Fornisce report completo

### Metodo 2: Build Manuale

#### Passo 1: Compila con PyInstaller
```bash
# Pulisci build precedenti
rm -rf build/ dist/ __pycache__/

# Compila l'applicazione
pyinstaller --clean --noconfirm dblogix.spec
```

#### Passo 2: Prepara la distribuzione
```bash
# Copia file aggiuntivi
cp dblogix_service.py dist/DBLogiX/
cp README.md dist/DBLogiX/
cp requirements.txt dist/DBLogiX/

# Crea directory necessarie
mkdir -p dist/DBLogiX/logs
mkdir -p dist/DBLogiX/UPLOADS
mkdir -p dist/DBLogiX/Fatture
```

#### Passo 3: Crea installer (opzionale)
```bash
# Usando InnoSetup Compiler
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" dblogix_installer.iss
```

## Struttura Output

Dopo il build avrai:

```
📂 dist/DBLogiX/              # Applicazione compilata
├── 📄 DBLogiX.exe           # Eseguibile principale (crittografato)
├── 📄 dblogix_service.py    # Gestore servizio Windows
├── 📄 config.py             # Configurazione
├── 📄 generate_certs.py     # Generatore certificati
├── 📁 templates/            # Template HTML
├── 📁 static/               # File statici
├── 📁 logs/                 # Directory log
├── 📁 _internal/            # Librerie Python (crittografate)
└── 📄 INSTALL.md           # Istruzioni installazione

📂 installer_output/          # Installer Windows
└── 📄 DBLogiX_Setup_1.0.0.exe

📂 release_package/           # Pacchetto portable
└── 📄 DBLogiX_Portable_YYYYMMDD_HHMMSS.zip
```

## Installazione sul PC Cliente

### Metodo 1: Installer Automatico

1. Esegui `DBLogiX_Setup_1.0.0.exe` come **Amministratore**
2. Segui la procedura guidata
3. L'installer configurerà automaticamente:
   - Servizio Windows
   - Firewall Windows
   - Certificati SSL
   - Avvio automatico

### Metodo 2: Installazione Manuale

1. **Estrai i file** nella directory di installazione:
   ```
   C:\Program Files\DBLogiX\
   ```

2. **Apri prompt come Amministratore** e naviga nella directory:
   ```cmd
   cd "C:\Program Files\DBLogiX"
   ```

3. **Installa il servizio:**
   ```cmd
   python dblogix_service.py install
   ```

4. **Configura il firewall:**
   ```cmd
   python dblogix_service.py firewall
   ```

5. **Avvia il servizio:**
   ```cmd
   python dblogix_service.py start
   ```

## Gestione Servizio

### Comandi Disponibili

```cmd
# Controlla stato
python dblogix_service.py status

# Avvia servizio
python dblogix_service.py start

# Ferma servizio
python dblogix_service.py stop

# Riavvia servizio
python dblogix_service.py restart

# Disinstalla servizio
python dblogix_service.py uninstall
```

### Accesso all'Applicazione

Una volta installato e avviato:

🌐 **URL:** https://localhost:5000

⚠️ **IMPORTANTE:** L'applicazione funziona SOLO in HTTPS per garantire il corretto funzionamento dello scanner barcode.

## Configurazione

### Database

Modifica `config.py` per configurare la connessione al database:

```python
REMOTE_DB_CONFIG = {
    'host': '192.168.1.22',     # IP del database
    'user': 'user',             # Username
    'password': 'password',     # Password
    'database': 'sys_datos',    # Nome database
    'port': 3306,               # Porta MySQL
}
```

### Certificati SSL

I certificati SSL vengono generati automaticamente al primo avvio. Per rigenerarli:

```cmd
python generate_certs.py
```

### Log

I log dell'applicazione sono disponibili in:

```
📁 logs/
├── 📄 dblogix_service.log   # Log del servizio
└── 📄 dblogix.log          # Log dell'applicazione Flask
```

## Sicurezza

### Protezione del Codice

- **Crittografia PyInstaller:** Il codice Python è crittografato e non leggibile
- **Bytecode protetto:** I file .pyc sono incorporati e crittografati
- **Import nascosti:** Le dipendenze sono incluse nel binario

### Accesso HTTPS

- **Certificati auto-firmati:** Generati automaticamente
- **TLS 1.2+:** Protocollo sicuro obbligatorio
- **Redirect automatico:** HTTP reindirizzato a HTTPS

### Firewall

Il servizio configura automaticamente:
- Regola in ingresso per porta 5000 TCP
- Descrizione "DBLogiX Database Management System HTTPS"
- Permessi solo per connessioni locali/rete locale

## Troubleshooting

### Problemi Comuni

#### 1. Servizio non si avvia
```cmd
# Controlla i log
type logs\dblogix_service.log

# Verifica Python
python --version

# Testa manualmente
python main_service.py
```

#### 2. Errore certificati SSL
```cmd
# Rigenera certificati
python generate_certs.py

# Verifica file
dir cert.pem key.pem
```

#### 3. Errore database
```cmd
# Verifica connessione
python test_db_connection.py

# Controlla config
type config.py
```

#### 4. Firewall blocca connessioni
```cmd
# Riconfigura firewall
python dblogix_service.py firewall

# Verifica regole
netsh advfirewall firewall show rule name="DBLogiX HTTPS"
```

### Log di Debug

Per abilitare debug dettagliato, modifica il file `config.py`:

```python
import os
os.environ['FLASK_DEBUG'] = 'True'
```

## Aggiornamenti

### Processo di Aggiornamento

1. **Ferma il servizio:**
   ```cmd
   python dblogix_service.py stop
   ```

2. **Backup configurazione:**
   ```cmd
   copy config.py config.py.backup
   ```

3. **Sostituisci i file** con la nuova versione

4. **Ripristina configurazione:**
   ```cmd
   copy config.py.backup config.py
   ```

5. **Riavvia servizio:**
   ```cmd
   python dblogix_service.py start
   ```

## Supporto

### Informazioni Sistema

```cmd
# Versione applicazione
python -c "import json; print(json.load(open('build_info.json')))"

# Stato sistema
python dblogix_service.py status

# Log recenti
tail -f logs\dblogix_service.log
```

### Disinstallazione Completa

```cmd
# Ferma e disinstalla servizio
python dblogix_service.py stop
python dblogix_service.py uninstall

# Rimuovi regole firewall
netsh advfirewall firewall delete rule name="DBLogiX HTTPS"

# Elimina directory installazione
rmdir /s "C:\Program Files\DBLogiX"
```

---

**DBLogiX** © 2024 - Sistema di gestione database e scanner barcode 