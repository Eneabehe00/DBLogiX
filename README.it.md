# DBLogiX - Sistema di Gestione Magazzino

DBLogiX è un'applicazione web completa per la gestione del magazzino che si connette al database remoto della bilancia Dibal per monitorare l'inventario, tracciare i ticket e gestire i prodotti.

## Problemi di Compatibilità

**IMPORTANTE**: L'applicazione è stata testata con Python 3.8-3.11. Potrebbero verificarsi problemi di compatibilità con versioni più recenti (Python 3.12+).

## Requisiti

- Python 3.8-3.11 (consigliato)
- MySQL Server (remoto)
- Browser web moderno

## Installazione

### 1. Installazione di Python

Se non hai già Python installato, scarica e installa una versione compatibile (3.8-3.11) dal [sito ufficiale di Python](https://www.python.org/downloads/).

### 2. Configurazione dell'ambiente virtuale

Crea un ambiente virtuale per isolare le dipendenze dell'applicazione:

```bash
# Crea l'ambiente virtuale
python -m venv venv

# Attiva l'ambiente virtuale
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configurazione del database

Modifica il file `config.py` inserendo i parametri di connessione al database remoto della bilancia:

```python
REMOTE_DB_CONFIG = {
    'host': '192.168.1.17',  # Indirizzo IP del server MySQL
    'user': 'user',          # Nome utente MySQL
    'password': 'dibal',     # Password MySQL
    'database': 'sys_datos', # Nome del database
    'port': 3306,            # Porta MySQL
}
```

### 5. Esegui lo script di setup

Lo script di setup verifica che l'ambiente sia correttamente configurato e inizializza il database:

```bash
python setup.py
```

### 6. Avvia l'applicazione

```bash
python main.py
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5000

## Risoluzione dei Problemi

### Importazione Circolare

Se riscontri errori come `cannot import name 'db' from 'app'`, il problema è dovuto a un'importazione circolare. Questo è stato risolto nell'ultima versione, ma se persiste:

1. Assicurati di aver aggiornato tutti i file (app.py, main.py)
2. Assicurati che tutte le dipendenze siano installate
3. Riavvia l'ambiente virtuale

### Problemi di Connessione al Database

Se l'applicazione non riesce a connettersi al database:

1. Verifica che i parametri in `config.py` siano corretti
2. Assicurati che il server MySQL sia in esecuzione
3. Verifica che il firewall non blocchi la connessione alla porta 3306
4. Esegui `python setup.py` per verificare la connessione

### Problemi con Python 3.12+

Se stai utilizzando Python 3.12 o successivo e riscontri errori:

1. Passa a Python 3.11 se possibile
2. Se non puoi cambiare versione di Python, prova a utilizzare una versione più recente di SQLAlchemy (2.0.23 o superiore)

## Prima Configurazione

Al primo avvio:

1. Registra un account amministratore (il primo utente registrato diventa automaticamente admin)
2. Accedi con le credenziali appena create
3. Verifica la connessione al database remoto nella sezione Admin > Configurazione DB
4. Creazione utenti aggiuntivi se necessario dalla sezione Admin > Gestione Utenti

## Architettura del Progetto

```
dblogix/
├── app.py                # Applicazione Flask principale
├── main.py               # Punto di ingresso dell'applicazione
├── config.py             # Configurazione database e app
├── models.py             # Modelli database
├── forms.py              # Moduli WTForms
├── utils.py              # Funzioni di utilità
├── auth.py               # Blueprint autenticazione
├── warehouse.py          # Blueprint magazzino
├── admin.py              # Blueprint amministrativo
├── requirements.txt      # Dipendenze Python
├── setup.py              # Script di setup
├── static/               # File statici (CSS, JS, immagini)
├── templates/            # Template HTML Jinja2
└── logs/                 # File di log
```

## Log e Debug

I log dell'applicazione sono salvati nella directory `logs/` e possono essere utili per diagnosticare problemi:

- `logs/dblogix.log`: Log principale dell'applicazione

Per attivare la modalità debug, imposta la variabile d'ambiente `FLASK_DEBUG=True` prima di avviare l'applicazione:

```bash
# Windows
set FLASK_DEBUG=True
# macOS/Linux
export FLASK_DEBUG=True
``` 