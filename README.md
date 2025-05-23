# DB-LogiX - Sistema Avanzato di Gestione Magazzino

DB-LogiX è un'applicazione web completa per la gestione del magazzino che si connette al database remoto della bilancia Dibal per monitorare l'inventario, tracciare i ticket e gestire i prodotti. Il sistema include funzionalità avanzate come la gestione clienti, lo scanner QR code, tracciabilità completa delle operazioni e gestione DDT.

## Descrizione del Progetto

Il progetto DB-LogiX è un sistema di gestione magazzino sviluppato in Python utilizzando il framework Flask. L'applicazione si interfaccia con un database MySQL remoto della bilancia Dibal e mantiene un database SQLite locale per le operazioni di autenticazione e tracciamento.

### Caratteristiche Principali

- **Gestione Inventario**: Monitoraggio in tempo reale dell'inventario
- **Catalogo Prodotti**: Gestione completa di prodotti con dettagli su prezzi, codici EAN, IVA
- **Gestione Ticket**: Visualizzazione e gestione dei ticket di vendita
- **Scanner QR Code**: Scansione rapida dei ticket mediante codici QR
- **Registro Scarichi**: Monitoraggio dettagliato degli articoli scaricati
- **Pannello Amministrativo**: Gestione utenti e statistiche avanzate
- **Gestione Clienti**: Database clienti completo con funzionalità CRUD
- **Generazione DDT**: Creazione e gestione dei documenti di trasporto
- **Tracciabilità**: Sistema completo di logging delle operazioni
- **Interfaccia Reattiva**: Design responsive per uso desktop e mobile

## Architettura del Sistema

Il sistema utilizza un'architettura client-server con:

- **Backend**: Python Flask per la gestione delle API e la logica applicativa
- **Database primario**: MySQL remoto (sulla bilancia Dibal)
- **Database secondario**: SQLite locale per autenticazione e logging
- **Frontend**: HTML, CSS, JavaScript con il supporto del framework Bootstrap

## Requisiti di Sistema

- Python 3.8+
- MySQL Server (remoto)
- Browser web moderno
- Connessione Internet (per accesso al database remoto)
- Webcam (per funzionalità scanner QR)

## Dipendenze Python

```
Flask==2.3.3
SQLAlchemy==2.0.23
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Migrate==4.0.5
PyMySQL==1.1.0
email-validator==2.1.0
python-dotenv==1.0.0
Jinja2==3.1.2
cryptography==41.0.5
```

## Struttura del Database

Il sistema DB-LogiX utilizza quattro tabelle principali per gestire l'operatività:

### 1. Table: users

La tabella `users` gestisce l'autenticazione e l'autorizzazione degli utenti del sistema.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(128) NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Descrizione dei campi**:
- `id`: Identificativo unico dell'utente (chiave primaria)
- `username`: Nome utente univoco per l'accesso al sistema
- `email`: Indirizzo email univoco dell'utente
- `password_hash`: Hash della password per la sicurezza
- `is_admin`: Flag che indica se l'utente ha privilegi amministrativi
- `created_at`: Data e ora di creazione dell'account

### 2. Table: scan_log

La tabella `scan_log` registra tutte le operazioni di scansione e tracciamento.

```sql
CREATE TABLE scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticket_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_code VARCHAR(50),
    product_code INTEGER,
    scan_date VARCHAR(20),
    scan_time VARCHAR(20),
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

**Descrizione dei campi**:
- `id`: Identificativo unico della registrazione (chiave primaria)
- `user_id`: ID dell'utente che ha effettuato l'operazione (chiave esterna)
- `ticket_id`: ID del ticket su cui è stata effettuata l'operazione
- `action`: Tipo di azione ('view', 'scan', 'scan_attempt', 'checkout')
- `timestamp`: Data e ora dell'operazione
- `raw_code`: Codice QR grezzo scannerizzato
- `product_code`: Codice del prodotto (se presente nel QR)
- `scan_date`: Data di scansione formattata
- `scan_time`: Ora di scansione formattata

### 3. Table: ddt_head

La tabella `ddt_head` contiene le intestazioni dei documenti di trasporto.

```sql
CREATE TABLE ddt_head (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    id_empresa INT NOT NULL,
    data_creazione DATETIME DEFAULT CURRENT_TIMESTAMP,
    totale_senza_iva DECIMAL(10,2) DEFAULT 0,
    totale_iva DECIMAL(10,2) DEFAULT 0,
    totale_importo DECIMAL(10,2) DEFAULT 0,
    INDEX idx_cliente (id_cliente),
    INDEX idx_empresa (id_empresa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

**Descrizione dei campi**:
- `id`: Identificativo unico del DDT (chiave primaria)
- `id_cliente`: ID del cliente destinatario del DDT
- `id_empresa`: ID dell'azienda emittente
- `data_creazione`: Data e ora di creazione del DDT
- `totale_senza_iva`: Importo totale senza IVA
- `totale_iva`: Importo totale dell'IVA
- `totale_importo`: Importo totale comprensivo di IVA
- Indici ottimizzati per ricerche veloci

### 4. Table: ddt_line

La tabella `ddt_line` contiene le linee dettagliate di ogni documento di trasporto.

```sql
CREATE TABLE ddt_line (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_ddt INT NOT NULL,
    id_empresa INT NOT NULL,
    id_tienda INT NOT NULL,
    id_balanza_maestra INT NOT NULL,
    id_balanza_esclava INT NOT NULL,
    tipo_venta TINYINT(1) NOT NULL,
    id_ticket BIGINT(20) NOT NULL,
    INDEX idx_ddt (id_ddt),
    INDEX idx_ticket (id_empresa, id_tienda, id_balanza_maestra, id_balanza_esclava, tipo_venta, id_ticket),
    FOREIGN KEY (id_ddt) REFERENCES ddt_head(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

**Descrizione dei campi**:
- `id`: Identificativo unico della linea DDT (chiave primaria)
- `id_ddt`: ID del DDT a cui appartiene questa linea (chiave esterna)
- `id_empresa`: ID dell'azienda
- `id_tienda`: ID del negozio
- `id_balanza_maestra`: ID della bilancia master
- `id_balanza_esclava`: ID della bilancia slave
- `tipo_venta`: Tipo di vendita
- `id_ticket`: ID del ticket associato
- Indici ottimizzati per ricerche veloci
- Vincolo di chiave esterna per garantire l'integrità referenziale

## Relazioni tra le Tabelle

- Un **utente** (`users`) può avere molti **log di scansione** (`scan_log`)
- Un **documento di trasporto** (`ddt_head`) può avere molte **linee** (`ddt_line`)
- Ogni **linea DDT** (`ddt_line`) è collegata a un **ticket** nel database remoto Dibal

## Processo di Generazione del DDT

Il sistema DB-LogiX implementa un processo strutturato per la generazione dei Documenti Di Trasporto (DDT), utilizzando diverse tabelle del database sia locale che remoto.

### Flusso del Processo di Generazione DDT

1. **Selezione dei Ticket**: L'utente seleziona uno o più ticket dalla pagina Scanner o dalla funzione di ricerca ticket
2. **Selezione del Cliente**: L'utente sceglie il cliente destinatario del DDT
3. **Generazione del DDT**: Il sistema crea il DDT, associando i ticket selezionati
4. **Tracciamento**: I ticket processati vengono marcati come "elaborati" (campo Enviado)
5. **Visualizzazione/Stampa**: Il DDT generato può essere visualizzato e esportato in formato PDF

### Tabelle Coinvolte

#### 1. Tabelle Principali DDT

- **dat_albaran_cabecera**: Contiene le intestazioni dei documenti di trasporto
  - `IdAlbaran`: Identificativo unico del DDT (parte della chiave primaria)
  - `NumAlbaran`: Numero progressivo del DDT
  - `IdEmpresa`, `IdTienda`, `IdBalanzaMaestra`, `IdBalanzaEsclava`, `TipoVenta`: Parti aggiuntive della chiave primaria
  - `IdCliente`: ID del cliente destinatario
  - `NombreCliente`: Nome del cliente
  - `DireccionCliente`, `PoblacionCliente`, `ProvinciaCliente`, `CPCliente`: Indirizzo cliente
  - `Fecha`: Data e ora di creazione del DDT
  - `ImporteTotalSinIVAConDtoL`: Importo totale senza IVA
  - `ImporteTotalDelIVAConDtoLConDtoTotal`: Importo totale dell'IVA
  - `ImporteTotal`: Importo totale comprensivo di IVA
  - `NumLineas`: Numero di linee nel DDT
  - `Usuario`: Utente che ha generato il DDT

- **dat_albaran_linea**: Contiene le linee dettagliate di ogni documento di trasporto
  - `IdLineaAlbaran`: Identificativo unico della linea
  - `IdAlbaran`: ID del DDT a cui appartiene questa linea
  - `IdEmpresa`, `IdTienda`, `IdBalanzaMaestra`, `IdBalanzaEsclava`, `TipoVenta`: Parti della chiave primaria
  - `IdTicket`: Riferimento al ticket di origine
  - `IdArticulo`: Codice del prodotto
  - `Descripcion`: Descrizione del prodotto
  - `Peso`: Quantità/peso del prodotto
  - `Medida2`: Unità di misura (es. kg, un)
  - `PrecioSinIVA`: Prezzo unitario senza IVA
  - `PorcentajeIVA`: Percentuale IVA applicata
  - `ImporteSinIVAConDtoL`: Importo senza IVA
  - `ImporteDelIVAConDtoL`: Importo dell'IVA

#### 2. Tabelle di Supporto (Remote DB)

- **dat_ticket_cabecera**: Contiene le intestazioni dei ticket di vendita
  - Chiave composta: `IdEmpresa`, `IdTienda`, `IdBalanzaMaestra`, `IdBalanzaEsclava`, `TipoVenta`, `IdTicket`
  - `Enviado`: Campo di stato che indica se il ticket è stato elaborato in un DDT (0=pendente, 4=in DDT)
  - `NumLineas`: Numero di linee del ticket
  - `Fecha`: Data e ora di emissione del ticket

- **dat_ticket_linea**: Contiene i dettagli di ogni linea del ticket
  - Collegata a `dat_ticket_cabecera` tramite chiave composta
  - `IdArticulo`: Riferimento al prodotto
  - `Descripcion`: Descrizione del prodotto
  - `Peso`: Quantità/peso del prodotto
  - `ImporteSinIVA`: Importo senza IVA
  - `ImporteIVA`: Importo IVA
  - `ImporteConIVA`: Importo totale

- **dat_articulo**: Anagrafica dei prodotti
  - `IdArticulo`: Codice prodotto
  - `Descripcion`: Nome/descrizione del prodotto
  - `PrecioSinIVA`: Prezzo unitario senza IVA
  - `PrecioConIVA`: Prezzo unitario con IVA
  - `IdIva`: Codice dell'aliquota IVA applicata

- **dat_cliente**: Anagrafica dei clienti
  - `IdCliente`, `IdEmpresa`: Chiave composta
  - `Nombre`: Nome/Ragione sociale del cliente
  - `Direccion`, `Poblacion`, `CodPostal`, `Provincia`: Indirizzo completo
  - `DNI`: Codice fiscale o partita IVA

- **dat_empresa**: Anagrafica dell'azienda emittente
  - `IdEmpresa`: ID azienda
  - `NombreEmpresa`: Nome dell'azienda
  - `CIF_VAT`: Partita IVA dell'azienda
  - `Direccion`, `Poblacion`, `CodPostal`, `Provincia`: Indirizzo completo

### Modelli di Implementazione

Nel codice Python, questi dati sono gestiti attraverso modelli SQLAlchemy:

- `AlbaranCabecera`: Modello per la tabella `dat_albaran_cabecera` (DDT header)
- `AlbaranLinea`: Modello per la tabella `dat_albaran_linea` (DDT lines)
- `TicketHeader`: Modello per la tabella `dat_ticket_cabecera`
- `TicketLine`: Modello per la tabella `dat_ticket_linea`
- `Product`: Modello per la tabella `dat_articulo`
- `Client`: Modello per la tabella `dat_cliente`
- `Company`: Modello per la tabella `dat_empresa`

### Calcolo dei Totali del DDT

Il sistema calcola automaticamente i totali per il DDT:

1. Per ogni ticket incluso nel DDT:
   - Recupera tutte le linee del ticket dalla tabella `dat_ticket_linea`
   - Per ogni linea, calcola subtotali e IVA in base ai dati del prodotto
   - Somma i totali di tutte le linee

2. Aggiorna i totali nella tabella `dat_albaran_cabecera`:
   - `ImporteTotalSinIVAConDtoL`: Somma di tutti gli importi senza IVA
   - `ImporteTotalDelIVAConDtoLConDtoTotal`: Somma di tutti gli importi IVA
   - `ImporteTotal`: Somma totale (imponibile + IVA)

### Esportazione del DDT

Il sistema offre la possibilità di esportare il DDT in formato PDF:

1. Recupera i dati del DDT dalla tabella `dat_albaran_cabecera`
2. Recupera i dati del cliente dalla tabella `dat_cliente`
3. Recupera i dati dell'azienda dalla tabella `dat_empresa`
4. Recupera tutte le linee del DDT dalla tabella `dat_albaran_linea` e i dettagli dei prodotti associati
5. Genera un documento PDF formattato con tutti i dati raccolti

## Installazione

### 1. Clona il repository

```bash
git clone https://github.com/tuo-username/dblogix.git
cd dblogix
```

### 2. Crea e attiva un ambiente virtuale

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

Modifica il file `config.py` inserendo i parametri di connessione:

```python
REMOTE_DB_CONFIG = {
    'host': '192.168.1.17',  # Indirizzo IP del server MySQL
    'user': 'user',          # Nome utente MySQL
    'password': 'dibal',     # Password MySQL
    'database': 'sys_datos', # Nome del database
    'port': 3306,            # Porta MySQL
}
```

### 5. Crea le tabelle nel database

Per creare le tabelle utenti e scan_log:
```bash
python main.py --init-db
```

Per creare le tabelle DDT:
```bash
python create_ddt_tables.py
```

### 6. Avvia l'applicazione

```bash
python main.py
```

L'applicazione sarà disponibile all'indirizzo: http://localhost:5000

Per modificare l'IP del server (ad esempio se il tuo indirizzo IP locale cambia), vai al file `config.py` e modifica i parametri nella sezione `REMOTE_DB_CONFIG`:

```python
REMOTE_DB_CONFIG = {
    'host': '192.168.1.22',  # Modifica questo indirizzo con il nuovo IP
    'user': 'user',
    'password': 'dibal',
    'database': 'sys_datos',
    'port': 3306,
}
```

Per avviare l'applicazione su un IP specifico e renderla accessibile sulla rete locale, puoi usare le variabili d'ambiente:

```bash
FLASK_HOST=0.0.0.0 FLASK_PORT=5000 python main.py
```

### 7. Percorso delle immagini dei prodotti

Le immagini dei prodotti vengono salvate nella condivisione di rete `\\192.168.1.26\DBLogiXUploads`. Il percorso è definito nel file `articles.py` nella funzione `upload_photo`:

```python
# Format the network path to the shared folder
network_path = f"\\\\192.168.1.26\\DBLogiXUploads\\{filename}"
```

Per modificare questo percorso, cerca questa riga nel file `articles.py` (circa linea 1401) e sostituisci l'indirizzo IP con quello della tua condivisione di rete.

## Utilizzo del Sistema

### Dashboard e Navigazione

La dashboard principale fornisce un riepilogo delle metriche chiave:
- Conteggio totale dei prodotti in inventario
- Ticket recenti (ultimi 5)
- Numero di ticket in attesa di elaborazione
- Scansioni recenti dell'utente

### Scansione QR Code

1. Accedere alla sezione "Scanner" dal menu principale
2. Inquadrare il codice QR del ticket da processare
3. Il sistema mostrerà i dettagli del ticket/prodotto scansionato
4. Procedere alla visualizzazione o al checkout

### Generazione DDT

1. Selezionare i ticket da includere nel DDT
2. Scegliere il cliente destinatario
3. Generare il DDT con il comando apposito
4. Visualizzare e/o stampare il documento generato

## Manutenzione

Il sistema include diverse utilità per la manutenzione:

- Script di backup del database
- Strumenti di sincronizzazione con il database remoto
- Log dettagliati per tracciare e risolvere problemi

## Sicurezza

Il sistema implementa diverse misure di sicurezza:
- Autenticazione utenti con password crittografate
- Protezione contro SQL injection
- Controllo degli accessi basato su ruoli
- Validazione degli input
- Protezione CSRF nei form

## Documentazione Aggiuntiva

Per ulteriori informazioni sui singoli moduli e sulle funzionalità specifiche, consultare i file sorgente nella directory del progetto.

Per assistenza tecnica, contattare il team di supporto all'indirizzo support@dblogix.com # DBLogiX
