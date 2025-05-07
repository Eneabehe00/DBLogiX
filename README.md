# DBLogiX - Sistema di Gestione Magazzino

DBLogiX è un'applicazione web completa per la gestione del magazzino che si connette al database remoto della bilancia Dibal per monitorare l'inventario, tracciare i ticket e gestire i prodotti.

## Caratteristiche

- **Gestione Inventario**: Visualizza e gestisci l'inventario in tempo reale
- **Catalogo Prodotti**: Catalogo completo con dettagli come prezzo, codice EAN, famiglia
- **Gestione Ticket**: Visualizza e gestisci i ticket di vendita con possibilità di checkout
- **Scanner QR Code**: Scansiona codici QR per processare i ticket rapidamente
- **Registro Scarichi**: Monitoraggio dettagliato degli articoli scaricati
- **Pannello Amministrativo**: Gestione utenti e statistiche avanzate

## Requisiti

- Python 3.8+
- MySQL Server (remoto)
- Browser web moderno

## Installazione

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/dblogix.git
cd dblogix
```

### 2. Crea un ambiente virtuale e attivalo

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 4. Configura la connessione al database

Modifica il file `config.py` inserendo i parametri di connessione al database remoto:

```python
REMOTE_DB_CONFIG = {
    'host': '192.168.1.17',  # Indirizzo IP del server MySQL
    'user': 'user',          # Nome utente MySQL
    'password': 'dibal',     # Password MySQL
    'database': 'sys_datos', # Nome del database
    'port': 3306,            # Porta MySQL
}
```

### 5. Inizializza il database locale

```bash
flask db init
flask db migrate -m "Creazione tabelle iniziali"
flask db upgrade
```

### 6. Avvia l'applicazione

```bash
python main.py
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5000

## Prima Configurazione

Al primo avvio:

1. Registra un account amministratore (il primo utente registrato diventa automaticamente admin)
2. Accedi con le credenziali appena create
3. Verifica la connessione al database remoto nella sezione Admin > Configurazione DB
4. Creazione utenti aggiuntivi se necessario dalla sezione Admin > Gestione Utenti

## Utilizzo

### Visualizzazione Inventario e Prodotti
- Accedi alla sezione "Prodotti" per visualizzare il catalogo completo
- Utilizza i filtri per famiglia e sottofamiglia per restringere la ricerca
- Clicca su un prodotto per visualizzarne i dettagli

### Gestione Ticket
- Accedi alla sezione "Ticket" per visualizzare tutti i ticket
- Filtra i ticket per stato (pendente/processato)
- Clicca su un ticket per visualizzarne i dettagli e le linee associate

### Utilizzo Scanner QR
1. Accedi alla sezione "Scanner"
2. Concedi i permessi per la fotocamera quando richiesto
3. Inquadra il codice QR di un ticket (formato `T[numero_ticket]` o `T[numero_ticket]-P[id_prodotto]`)
4. Il sistema mostrerà i dettagli del ticket scansionato
5. Puoi procedere alla visualizzazione del ticket o al checkout

### Amministrazione
- **Dashboard**: Visualizza statistiche e metriche del sistema
- **Gestione Utenti**: Crea, modifica o elimina account utente
- **Log Attività**: Monitora le operazioni di scansione e checkout
- **Configurazione DB**: Modifica i parametri di connessione al database remoto

## Struttura del Progetto

```
dblogix/
├── app.py                # Configurazione Flask
├── main.py               # Punto di ingresso dell'applicazione
├── config.py             # Configurazione database e app
├── models.py             # Modelli database
├── forms.py              # Moduli WTForms
├── utils.py              # Funzioni di utilità
├── auth.py               # Blueprint autenticazione
├── warehouse.py          # Blueprint magazzino
├── admin.py              # Blueprint amministrativo
├── requirements.txt      # Dipendenze Python
├── static/               # File statici (CSS, JS, immagini)
├── templates/            # Template HTML Jinja2
└── migrations/           # Migrazioni database
```

## Contribuire

Per contribuire al progetto:

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/nome-feature`)
3. Commit le tue modifiche (`git commit -m 'Aggiunta nuova feature'`)
4. Push sul branch (`git push origin feature/nome-feature`)
5. Apri una Pull Request

## Risoluzione Problemi

### Problemi di Connessione al Database
- Verifica che l'indirizzo IP del server MySQL sia corretto
- Assicurati che le credenziali di accesso siano valide
- Controlla che il firewall non blocchi la connessione alla porta MySQL

### Errori nell'Applicazione
- Controlla i file di log nella directory `logs/`
- Se l'applicazione non si avvia, verifica che tutte le dipendenze siano installate

## Licenza

Questo progetto è rilasciato con licenza MIT. Vedi il file `LICENSE` per i dettagli. # DBLogiX
