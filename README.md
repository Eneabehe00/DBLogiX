# DBLogiX - Sistema Avanzato di Gestione Magazzino

DBLogiX è un'applicazione web completa per la gestione del magazzino che si connette al database remoto della bilancia Dibal per monitorare l'inventario, tracciare i ticket e gestire i prodotti. Il sistema include funzionalità avanzate come la gestione clienti, lo scanner QR code e la tracciabilità completa delle operazioni.

## Caratteristiche

- **Gestione Inventario**: Visualizza e gestisci l'inventario in tempo reale
- **Catalogo Prodotti**: Catalogo completo con dettagli come prezzo, codice EAN, famiglia, IVA e sottofamiglia
- **Gestione Ticket**: Visualizza e gestisci i ticket di vendita con possibilità di checkout
- **Scanner QR Code**: Scansiona codici QR per processare i ticket rapidamente
- **Registro Scarichi**: Monitoraggio dettagliato degli articoli scaricati
- **Pannello Amministrativo**: Gestione utenti e statistiche avanzate
- **Gestione Clienti**: Database clienti completo con funzionalità CRUD
- **Filtri e Ricerca Avanzata**: Ricerca prodotti e ticket per vari criteri
- **Supporto Multi-Database**: Connessione a database MySQL remoto e SQLite locale
- **Tracciabilità Scadenze**: Monitoraggio prodotti in scadenza
- **Log Dettagliati**: Sistema completo di logging delle operazioni
- **Interfaccia Reattiva**: Design responsive per uso mobile e desktop

## Requisiti

- Python 3.8+
- MySQL Server (remoto)
- Browser web moderno
- Connessione Internet (per accesso al database remoto)
- Webcam (per funzionalità scanner QR)

## Dipendenze Python

- Flask 2.3.3
- SQLAlchemy 2.0.23
- Flask-SQLAlchemy 3.1.1
- Flask-Login 0.6.3
- Flask-WTF 1.2.1
- Flask-Migrate 4.0.5
- PyMySQL 1.1.0
- email-validator 2.1.0
- python-dotenv 1.0.0
- Jinja2 3.1.2
- cryptography 41.0.5

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

Il sistema supporta anche l'utilizzo di variabili d'ambiente per configurare la connessione:

```bash
export DB_HOST=192.168.1.17
export DB_USER=user
export DB_PASSWORD=dibal
export DB_NAME=sys_datos
export DB_PORT=3306
export SECRET_KEY=your-secret-key
```

### 5. Inizializza il database locale

```bash
flask db init
flask db migrate -m "Creazione tabelle iniziali"
flask db upgrade
```

### 6. Avvia l'applicazione

**Modalità di sviluppo:**
```bash
py main.py
```

**Modalità produzione (con WSGI):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5000

## Prima Configurazione

Al primo avvio:

1. Registra un account amministratore (il primo utente registrato diventa automaticamente admin)
2. Accedi con le credenziali appena create
3. Verifica la connessione al database remoto nella sezione Admin > Configurazione DB
4. Creazione utenti aggiuntivi se necessario dalla sezione Admin > Gestione Utenti
5. Configura i parametri di sistema nella sezione Admin > Impostazioni

## Modelli e Database

DBLogiX utilizza il database remoto:

### Database Remoto (MySQL)

Contiene i modelli relativi al sistema della bilancia Dibal:

- **Client (dat_cliente)**: Informazioni sui clienti
- **Product (dat_articulo)**: Catalogo prodotti
- **TicketHeader (dat_ticket_cabecera)**: Intestazioni dei ticket di vendita
- **TicketLine (dat_ticket_linea)**: Linee dei ticket con dettagli sui prodotti

Contiene i modelli relativi alla gestione utenti e tracciamento:

- **User**: Account utente con autenticazione
- **ScanLog**: Registro delle operazioni di scansione QR

## Utilizzo

### Dashboard e Panoramica

La dashboard principale mostra:
- Conteggio totale dei prodotti in inventario
- Ticket recenti (ultimi 5)
- Numero di ticket in attesa di elaborazione
- Scansioni recenti dell'utente corrente
- Statistiche riassuntive

### Gestione Prodotti

- **Catalogo Prodotti**: Accedi dalla voce di menu "Prodotti"
- **Filtri**: Filtra per famiglia, sottofamiglia o utilizza la ricerca testuale
- **Dettagli Prodotto**: Clicca su un prodotto per vedere informazioni dettagliate e storico utilizzo

### Gestione Ticket

- **Lista Ticket**: Visualizza tutti i ticket dalla sezione "Ticket"
- **Filtri**: Filtra per stato (pendente/processato/in scadenza)
- **Dettagli Ticket**: Clicca su un ticket per vedere tutte le linee e i prodotti associati
- **Checkout**: Segna un ticket come processato dalla pagina di dettaglio

### Gestione Clienti

- **Lista Clienti**: Visualizza tutti i clienti dalla sezione "Clienti"
- **Ricerca**: Cerca clienti per nome, ID o altri parametri
- **Nuovo Cliente**: Aggiungi nuovi clienti con il form dedicato
- **Modifica/Elimina**: Gestisci i dettagli dei clienti esistenti

### Utilizzo Scanner QR

1. Accedi alla sezione "Scanner" dal menu principale
2. Concedi i permessi per la fotocamera quando richiesto
3. Inquadra il codice QR di un ticket (supportati i formati):
   - `T[numero_ticket]` - Scansione ticket completo
   - `T[numero_ticket]-P[id_prodotto]` - Scansione prodotto specifico in un ticket
   - `T[numero_ticket]-D[data]-H[ora]` - Formato avanzato con timestamp
4. Il sistema mostrerà i dettagli del ticket/prodotto scansionato
5. Puoi procedere alla visualizzazione del ticket o al checkout diretto

### Scansione Manuale

Se il codice QR non è leggibile, è possibile utilizzare la funzione di scansione manuale:
1. Vai alla sezione "Scanner"
2. Clicca su "Inserimento Manuale"
3. Inserisci il numero del ticket e opzionalmente l'ID del prodotto
4. Clicca su "Procedi" per elaborare il ticket

### Amministrazione

- **Dashboard Admin**: Visualizza statistiche e metriche del sistema
- **Gestione Utenti**: Crea, modifica o elimina account utente
- **Log Attività**: Monitora le operazioni di scansione e checkout
- **Configurazione DB**: Modifica i parametri di connessione al database remoto
- **Backup e Ripristino**: Funzionalità di backup dei dati locali
- **Impostazioni Sistema**: Configura parametri globali dell'applicazione

## Aggiornamento Database

Il sistema include diverse utilità per aggiornare il database:

### Aggiornamento MySQL

```bash
python update_mysql_db.py
```

Questo script sincronizza il database locale con il server MySQL remoto.

### Aggiornamento SQLite

```bash
python update_db_sqlite.py
```

Per installazioni che utilizzano SQLite come database locale.

### Aggiornamento Generico

```bash
python update_db.py
```

Routine di aggiornamento generica che seleziona automaticamente il tipo di database.

## Struttura del Progetto

```
dblogix/
├── app.py                # Configurazione principale Flask
├── main.py               # Punto di ingresso dell'applicazione
├── config.py             # Configurazione database e app
├── models.py             # Modelli database (SQLAlchemy)
├── forms.py              # Moduli WTForms per l'interfaccia
├── utils.py              # Funzioni di utilità
├── auth.py               # Blueprint autenticazione
├── warehouse.py          # Blueprint gestione magazzino
├── admin.py              # Blueprint amministrazione
├── update_db.py          # Script aggiornamento database
├── update_mysql_db.py    # Script specifico per MySQL
├── update_db_sqlite.py   # Script specifico per SQLite
├── setup.py              # Setup dell'applicazione
├── requirements.txt      # Dipendenze Python
├── static/               # File statici (CSS, JS, immagini)
│   ├── css/              # Fogli di stile
│   ├── js/               # Script JavaScript
│   └── images/           # Immagini e icone
├── templates/            # Template HTML Jinja2
│   ├── auth/             # Template autenticazione
│   ├── admin/            # Template amministrazione
│   ├── warehouse/        # Template magazzino
│   ├── errors/           # Template pagine di errore
│   └── base.html         # Template base
└── logs/                 # Directory log applicazione
```

## Funzionalità Avanzate

### Filtro Prodotti in Scadenza

Il sistema identifica automaticamente i prodotti con una data di scadenza prossima (entro 7 giorni) e li evidenzia nella vista ticket. Questa funzionalità è accessibile tramite il filtro "In Scadenza" nella lista ticket.

### Gestione Errori e Logging

Il sistema include un robusto meccanismo di logging che registra:
- Errori di applicazione
- Tentativi di accesso
- Operazioni di scansione
- Operazioni di checkout
- Modifiche al database

I log sono disponibili nella directory `logs/` e configurabili per rotazione.

### API Interna

Per operazioni avanzate, il sistema espone endpoint API interni:
- `/api/checkout` - Checkout programmato di ticket
- `/process_qr` - Elaborazione codici QR
- `/checkout` - Checkout manuale

### Configurazione Avanzata

Il file `config.py` supporta configurazioni avanzate:
- Connessioni a database multipli
- Configurazione di logging
- Configurazione di sicurezza
- Timeout sessione
- Cache di sistema

## Risoluzione Problemi

### Problemi di Connessione al Database
- Verifica che l'indirizzo IP del server MySQL sia corretto
- Assicurati che le credenziali di accesso siano valide
- Controlla che il firewall non blocchi la connessione alla porta MySQL
- Verifica se il database remoto Dibal è online e accessibile
- Controlla i parametri di connessione nel file `config.py`

### Errori di Autenticazione
- Verifica le credenziali utente
- Controlla se l'account è stato disabilitato da un amministratore
- Riprova dopo aver cancellato i cookie del browser

### Errori Scanner QR
- Assicurati che la fotocamera sia abilitata e funzionante
- Verifica che il browser abbia i permessi di accesso alla fotocamera
- Prova a migliorare l'illuminazione del codice QR
- Utilizza l'opzione di inserimento manuale come alternativa

### Errori nell'Applicazione
- Controlla i file di log nella directory `logs/`
- Riavvia l'applicazione se si verificano errori persistenti
- Verifica che tutte le dipendenze siano installate correttamente

### Errori Comuni
- **Errore 500**: Problema sul server, controlla i log
- **Errore 404**: Pagina non trovata, verifica l'URL
- **Errore di Database**: Verifica la connessione al database
- **Timeout**: Controlla la connessione di rete e lo stato del server

## Manutenzione

### Backup Database

```bash
flask db-backup
```

### Pulizia Log

```bash
python -m utils.cleanup_logs --days 30
```

Elimina i log più vecchi di 30 giorni.

### Aggiornamento Sistema

```bash
git pull
pip install -r requirements.txt
flask db upgrade
```

## Sviluppo

### Shell Interattiva

```bash
flask shell
```

Offre accesso a un ambiente Python con i modelli già importati per test rapidi:

```python
# Esempio di query
tickets = TicketHeader.query.filter_by(Enviado=0).all()
print(f"Ticket pendenti: {len(tickets)}")
```

### Debug Mode

```bash
export FLASK_DEBUG=1
python main.py
```

### Test

Il sistema include una suite di test automatizzati:

```bash
pytest tests/
```

## Contribuire

Per contribuire al progetto:

1. Fork il repository
2. Crea un branch per la tua feature (`git checkout -b feature/nome-feature`)
3. Commit le tue modifiche (`git commit -m 'Aggiunta nuova feature'`)
4. Push sul branch (`git push origin feature/nome-feature`)
5. Apri una Pull Request

## Sicurezza

DBLogiX implementa diverse misure di sicurezza:
- Password hash sicuro con Werkzeug
- Protezione CSRF su tutti i form
- Gestione sessioni sicura
- Logging di accesso
- Timeout di sessione configurabile
- Autenticazione obbligatoria per tutte le route sensibili

## Tecnologie Utilizzate

- **Backend**: Flask, SQLAlchemy, WTForms
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Database**: MySQL, SQLite
- **Autenticazione**: Flask-Login
- **Migrazioni**: Flask-Migrate (Alembic)
- **Connettore DB**: PyMySQL
- **Validazione**: email-validator, wtforms.validators
- **Configurazione**: python-dotenv

## Licenza

Questo progetto è rilasciato con licenza MIT. Vedi il file `LICENSE` per i dettagli.

## Contatti e Supporto

Per assistenza e supporto, contatta il team di sviluppo all'indirizzo email [support@dblogix.com](mailto:support@dblogix.com).
