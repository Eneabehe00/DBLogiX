<!-- markdownlint-disable -->
# 🏭 DBLogiX - Sistema di Gestione Magazzino e Tracciabilità

![Version](https://img.shields.io/badge/version-4.7.0-blue.svg)
![Build System](https://img.shields.io/badge/build%20.net%20config-modular-brightgreen.svg)
![Inno Setup](https://img.shields.io/badge/installer-inno%20setup-orange.svg)
![Windows Service](https://img.shields.io/badge/service-windows-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)
![Flask](https://img.shields.io/badge/flask-2.3.3-red.svg)
![MySQL](https://img.shields.io/badge/mysql-8.0%2B-orange.svg)
![License](https://img.shields.io/badge/license-Proprietary-yellow.svg)

## 📋 Indice

- [Panoramica del Progetto](#-panoramica-del-progetto)
- [Architettura del Sistema](#️-architettura-del-sistema)
- [Tecnologie Utilizzate](#-tecnologie-utilizzate)
- [Struttura del Database](#-struttura-del-database)
- [Moduli e Funzionalità](#-moduli-e-funzionalità)
- [Installazione e Configurazione](#-installazione-e-configurazione)
- [API e Endpoint](#-api-e-endpoint)
- [Frontend e UI](#-frontend-e-ui)
- [Sicurezza e Autenticazione](#-sicurezza-e-autenticazione)
- [Logging e Monitoraggio](#-logging-e-monitoraggio)
- [Deployment](#-deployment)
- [Testing](#-testing)
- [Contributi](#-contributi)

## 🎯 Panoramica del Progetto

**DBLogiX** è una webapp completa per la gestione del magazzino, tracciabilità dei prodotti, e gestione dei documenti di trasporto (DDT) e fatturazione elettronica. Il sistema è progettato per integrarsi con bilance industriali e sistemi POS per la tracciabilità completa dei prodotti dal ricevimento alla vendita.

### 🎯 Obiettivi Principali
- **Tracciabilità Completa**: Dal ricevimento prodotti fino alla vendita finale
- **Gestione Magazzino**: Controllo stock, movimentazioni, scadenze
- **Automazione Processi**: Generazione automatica DDT e fatture
- **Task Management**: Sistema di gestione task per operatori
- **Integrazione Hardware**: Supporto per bilance e scanner QR/Barcode

### 🏢 Casi d'Uso
- Gestione magazzino per aziende alimentari
- Tracciabilità prodotti con QR Code
- Generazione automatica documenti fiscali
- Controllo qualità e scadenze prodotti
- Gestione clienti e fornitori

## 🏗️ Architettura del Sistema

### Struttura MVC Flask

```mermaid
graph TB
    A[Frontend - Jinja2 Templates] --> B[Flask Routes - Blueprint]
    B --> C[Business Logic - Modules]
    C --> D[Database Models - SQLAlchemy]
    D --> E[MySQL Database]
    
    F[Static Assets] --> A
    G[Authentication] --> B
    H[API Endpoints] --> B
    I[Services] --> C
    J[Configuration] --> C
```

### 🗂️ Struttura Directory

```
DBLogiX/
├── 📁 app/                     # Core applicazione Flask
│   ├── __init__.py
│   ├── auth.py                 # Autenticazione utenti
│   ├── config.py              # Configurazioni sistema
│   ├── config_manager.py      # Gestione configurazioni esterne
│   ├── forms.py               # Form WTF
│   ├── models.py              # Modelli database SQLAlchemy
│   └── logs/                  # Log applicazione core
├── 📁 modules/                # Moduli funzionali
│   ├── admin.py               # Pannello amministrazione
│   ├── articles.py            # Gestione articoli
│   ├── chat.py                # Sistema chat interno
│   ├── clients.py             # Gestione clienti
│   ├── ddt.py                 # Documenti di trasporto
│   ├── fattura_pa.py          # Fatturazione elettronica PA
│   ├── ingredients.py         # Gestione ingredienti e food cost
│   ├── listini.py             # Gestione listini prezzi
│   ├── sections.py            # Gestione sezioni magazzino
│   ├── tasks.py               # Sistema gestione task
│   └── warehouse.py           # Gestione magazzino
├── 📁 services/               # Servizi di supporto
│   ├── chat.py                # Sistema chat interno
│   └── utils.py               # Utility functions
├── 📁 templates/              # Template Jinja2
│   ├── base.html              # Template base
│   ├── 📁 admin/              # Template amministrazione
│   ├── 📁 articles/           # Template articoli
│   ├── 📁 auth/               # Template autenticazione
│   ├── 📁 clients/            # Template clienti
│   ├── 📁 ddt/                # Template DDT
│   ├── 📁 fattura_pa/         # Template fatturazione
│   ├── 📁 sections/           # Template sezioni
│   ├── 📁 tasks/              # Template task
│   └── 📁 warehouse/          # Template magazzino
├── 📁 static/                 # Asset statici
│   ├── 📁 css/                # Fogli di stile (15 file specializzati)
│   ├── 📁 js/                 # JavaScript
│   ├── 📁 uploads/            # File caricati
│   └── favicon.ico            # Icona applicazione
├── 📁 migrations/             # Migrazioni database
├── 📁 logs/                   # File di log
├── 📁 scripts/                # Script utility
│   └── dblogix_installer.iss  # Script Inno Setup installer
├── 📁 build_system/           # Sistema di build modulare
│   ├── main_builder.py        # Entry point principale build
│   ├── inno_setup.py          # Generazione installer
│   ├── python_embedded.py     # Download Python embedded
│   ├── launcher_service.py    # Servizio Windows launcher
│   ├── ssl_certificates.py    # Gestione certificati SSL
│   ├── update_and_deploy.py   # Sistema aggiornamento
│   ├── windows_service.py     # Creazione servizio Windows
│   ├── file_operations.py     # Operazioni su file
│   └── app_entry.py           # Entry point Flask per build
├── 📁 build/                  # Directory build temporanea
├── 📁 UPLOADS/                # Directory upload separata
├── 📁 Install DB e Kiosk/     # Script installazione database
│   ├── Install_DBLogiX.bat    # Script installazione Windows
│   ├── Install_DBLogiX_Complete.sql  # Schema database completo
│   └── Kiosk - DBlogiX.bat    # Script modalità kiosk
├── 📁 Backup/                 # Backup sistema
├── main.py                    # Entry point principale applicazione
├── app.py                     # Configurazione Flask alternativa
├── build.py                   # Script build semplificato
├── DBLogix.exe.config         # Configurazione .NET per exe
└── RAG CURSOR.txt             # Documentazione AI/RAG
```

## 🛠️ Tecnologie Utilizzate

### Backend
| Tecnologia | Versione | Utilizzo |
|------------|----------|----------|
| **Python** | 3.8+ | Linguaggio principale |
| **Flask** | 2.3.3 | Framework web |
| **SQLAlchemy** | 2.0.23 | ORM Database |
| **Flask-Login** | 0.6.3 | Gestione sessioni |
| **Flask-WTF** | 1.2.1 | Form validation |
| **PyMySQL** | 1.1.0 | Driver MySQL |
| **Werkzeug** | 2.3.7 | WSGI toolkit |

### Frontend
| Tecnologia | Utilizzo |
|------------|----------|
| **HTML5** | Markup semantic |
| **CSS3** | Styling responsivo (15 fogli specializzati) |
| **JavaScript ES6** | Interattività |
| **Bootstrap 5** | Framework CSS |
| **Jinja2** | Template engine |
| **FontAwesome** | Icone |

### Fogli di Stile Specializzati
| File CSS | Funzione | Moduli |
|----------|----------|---------|
| `base.css` | Stili base globali | Core |
| `tasks.css` | Sistema task management | Tasks |
| `ddt.css` | Documenti di trasporto | DDT |
| `ddt_preview.css` | Anteprime DDT | DDT |
| `shared-components.css` | Componenti riutilizzabili | Core |
| `fattura_pa.css` | Fatturazione elettronica | FatturaPA |
| `articles.css` | Gestione articoli | Articles |
| `warehouse.css` | Interfaccia magazzino | Warehouse |
| `clients.css` | Gestione clienti | Clients |
| `fornitori.css` | Gestione fornitori | Ingredients |
| `ingredients.css` | Sistema ingredienti | Ingredients |
| `sections.css` | Sezioni magazzino | Sections |
| `chat.css` | Sistema chat | Chat |
| `notifications.css` | Sistema notifiche | Core |
| `home.css` | Dashboard principale | Core |
| `admin.css` | Pannello amministrazione | Admin |
| `style.css` | Stili generici | Core |
| `auth.css` | Autenticazione | Auth |
| `errors.css` | Pagine errore | Core |

### Database
| Componente | Dettaglio |
|------------|-----------|
| **MySQL** | 8.0+ |
| **Charset** | UTF-8 |
| **Engine** | InnoDB |
| **Connessioni** | Pool connection |

### Librerie Specializzate
| Libreria | Versione | Funzione |
|----------|----------|----------|
| **ReportLab** | 4.4.0 | Generazione PDF |
| **QRCode** | 8.2 | Generazione QR Code |
| **Flask-CORS** | 4.0.0 | Cross-Origin Resource Sharing |
| **PyWin32** | 306 | Servizi Windows nativi |
| **Python-dotenv** | 1.0.0 | Gestione variabili ambiente |
| **Pandas** | 2.1.3 | Manipolazione dati Excel |
| **OpenPyXL** | 3.1.2 | Lettura/scrittura Excel |

### Runtime e Distribuzione
| Componente | Versione | Utilizzo |
|------------|----------|----------|
| **Python Embedded** | 3.11.9 | Runtime distribuzione |
| **Inno Setup** | - | Generazione installer Windows |
| **.NET Config** | - | Configurazione runtime eseguibile |

## 🗄️ Struttura del Database

### Tabelle Principali

#### 🏢 Gestione Azienda
```sql
-- Tabella aziende
dat_empresa (
    IdEmpresa INT PRIMARY KEY,
    NombreEmpresa VARCHAR(100),
    CIF_VAT VARCHAR(50),
    Direccion VARCHAR(200),
    Telefono1 VARCHAR(20),
    -- ... altri campi aziendali
)
```

#### 👥 Gestione Clienti
```sql
-- Tabella clienti
dat_cliente (
    IdCliente INT PRIMARY KEY,
    IdEmpresa INT,
    Nombre VARCHAR(100),
    Direccion VARCHAR(200),
    CodPostal VARCHAR(10),
    Poblacion VARCHAR(100),
    DNI VARCHAR(20),
    Email VARCHAR(100),
    Telefono1 VARCHAR(20),
    -- ... altri campi cliente
)
```

#### 📦 Gestione Prodotti
```sql
-- Tabella articoli/prodotti
dat_articulo (
    IdArticulo INT PRIMARY KEY,
    Descripcion VARCHAR(100),
    PrecioConIVA DECIMAL(13,3),
    EANScanner VARCHAR(50),
    IdFamilia INT,
    IdSubFamilia INT,
    IdIva INT,
    StockActual FLOAT,
    -- ... altri campi prodotto
)
```

#### 🎫 Sistema Ticketing
```sql
-- Testata ticket
dat_ticket_cabecera (
    IdTicket INT PRIMARY KEY,
    IdEmpresa INT DEFAULT 1,
    NumTicket INT,
    Fecha DATETIME,
    CodigoBarras VARCHAR(50),
    NumLineas INT,
    Enviado INT DEFAULT 0  -- Status: 0=Giacenza, 1=Processato, 4=Scaduto
)

-- Righe ticket
dat_ticket_linea (
    IdLineaTicket INT,
    IdTicket BIGINT,
    IdArticulo INT,
    Descripcion VARCHAR(100),
    Peso DECIMAL(15,3),
    FechaCaducidad DATETIME,
    comportamiento INT DEFAULT 0  -- 0=unità, 1=kg
    -- Chiave composta primaria
)
```

#### 📋 Sistema Task
```sql
-- Task management
tasks (
    id_task INT PRIMARY KEY,
    task_number VARCHAR(20) UNIQUE,
    title VARCHAR(200),
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_by INT,
    assigned_to INT,
    deadline DATETIME,
    priority VARCHAR(10) DEFAULT 'medium',
    total_tickets INT DEFAULT 0,
    completed_tickets INT DEFAULT 0
)

-- Associazione task-ticket
task_tickets (
    id INT PRIMARY KEY,
    task_id INT,
    ticket_id INT,
    status VARCHAR(20) DEFAULT 'pending',
    total_items INT DEFAULT 0,
    scanned_items INT DEFAULT 0
)
```

#### 📄 Documenti di Trasporto (DDT)
```sql
-- Testata DDT/Albarán
dat_albaran_cabecera (
    IdAlbaran BIGINT PRIMARY KEY,
    NumAlbaran BIGINT,
    IdEmpresa INT,
    IdCliente INT,
    NombreCliente VARCHAR(50),
    Fecha DATETIME,
    ImporteTotal FLOAT(15,3),
    NumLineas SMALLINT,
    Enviado BOOLEAN DEFAULT 0
)

-- Righe DDT/Albarán
dat_albaran_linea (
    IdLineaAlbaran INT,
    IdAlbaran BIGINT,
    IdArticulo INT,
    Descripcion VARCHAR(100),
    Peso FLOAT(15,3),
    Precio FLOAT(15,3),
    Importe FLOAT(15,3)
    -- Chiave composta primaria
)
```

#### 👤 Gestione Utenti
```sql
-- Utenti sistema
users (
    id INT PRIMARY KEY,
    username VARCHAR(64) UNIQUE,
    email VARCHAR(120) UNIQUE,
    password_hash VARCHAR(128),
    is_admin BOOLEAN DEFAULT FALSE,
    screen_task BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME
)

-- Log scansioni
scan_log (
    id INT PRIMARY KEY,
    user_id INT,
    ticket_id INT,
    action VARCHAR(20),  -- 'view', 'scan', 'checkout'
    timestamp DATETIME,
    raw_code VARCHAR(50),
    product_code INT,
    scan_date VARCHAR(20),
    scan_time VARCHAR(20)
)
```

### Relazioni Database

```mermaid
erDiagram
    dat_empresa ||--o{ dat_cliente : "has"
    dat_cliente ||--o{ dat_albaran_cabecera : "orders"
    dat_articulo ||--o{ dat_ticket_linea : "contains"
    dat_ticket_cabecera ||--o{ dat_ticket_linea : "has"
    dat_albaran_cabecera ||--o{ dat_albaran_linea : "contains"
    users ||--o{ tasks : "creates"
    users ||--o{ tasks : "assigned_to"
    tasks ||--o{ task_tickets : "contains"
    dat_ticket_cabecera ||--o{ task_tickets : "assigned_to"
```

## 🧩 Moduli e Funzionalità

### 1. 🏠 Modulo Admin (`modules/admin.py`)
**Funzionalità**: Pannello di controllo amministrativo completo

#### Features:
- **Dashboard Statistiche**: Visualizzazione metriche sistema
- **Gestione Utenti**: CRUD utenti, ruoli, permessi
- **Configurazione Sistema**: Impostazioni globali
- **Gestione Database**: Configurazione connessione DB
- **Log Monitoring**: Visualizzazione log di sistema
- **Backup/Restore**: Gestione backup automatici

#### Endpoint Principali:
```python
/admin/                        # Dashboard principale
/admin/users                   # Gestione utenti
/admin/config                  # Configurazione sistema
/admin/stats                   # Statistiche avanzate
/admin/db_config              # Configurazione database
/admin/logs                   # Visualizzazione log
```

### 2. 📦 Modulo Warehouse (`modules/warehouse.py`)
**Funzionalità**: Gestione completa magazzino e tracciabilità

#### Features:
- **Scanner QR/Barcode**: Scansione prodotti con validazione
- **Gestione Ticket**: Visualizzazione e processamento ordini
- **Tracciabilità**: Storico movimentazioni prodotti
- **Controllo Scadenze**: Alert prodotti in scadenza
- **Checkout Automatico**: Processamento ordini con QR

#### Componenti UI:
```javascript
// Scanner Interface
scanner.html - Interfaccia scansione QR/Barcode
tickets.html - Lista ticket magazzino
ticket_detail.html - Dettaglio singolo ticket
generate_ddt_step.html - Generazione DDT da ticket
```

#### Workflow Scansione:
```mermaid
sequenceDiagram
    participant U as Utente
    participant S as Scanner
    participant DB as Database
    participant W as Warehouse
    
    U->>S: Scansione QR Code
    S->>DB: Verifica codice prodotto
    DB-->>S: Dati prodotto
    S->>W: Aggiorna quantità
    W->>DB: Salva movimentazione
    DB-->>U: Conferma operazione
```

### 3. 📝 Modulo Tasks (`modules/tasks.py`)
**Funzionalità**: Sistema gestione task e workflow

#### Features:
- **Creazione Task**: Assegnazione compiti a operatori
- **Workflow Management**: Stati task (pending, in_progress, completed)
- **Progress Tracking**: Monitoraggio avanzamento
- **Notifiche Real-time**: Alert completamento task
- **Reporting**: Report produttività e performance

#### Stati Task:
| Stato | Descrizione |
|-------|-------------|
| `pending` | Task creato, in attesa assegnazione |
| `assigned` | Task assegnato a operatore |
| `in_progress` | Task in esecuzione |
| `completed` | Task completato |

#### Dashboard Task:
```javascript
// Admin Dashboard
admin_dashboard.html - Panoramica task admin
user_dashboard.html - Dashboard operatore
task_screen.html - Schermo dedicato task
create_task.html - Creazione nuovo task
edit_task.html - Modifica task esistente
```

### 4. 📄 Modulo DDT (`modules/ddt.py`)
**Funzionalità**: Gestione Documenti di Trasporto

#### Features:
- **Generazione DDT**: Creazione automatica da ticket
- **Selezione Clienti**: Interfaccia scelta destinatario
- **Preview Documenti**: Anteprima prima stampa
- **Esportazione PDF**: Generazione documento finale
- **Storico DDT**: Archivio documenti generati

#### Workflow DDT:
```mermaid
flowchart TD
    A[Selezione Ticket] --> B[Scelta Cliente]
    B --> C[Generazione Testata DDT]
    C --> D[Calcolo Totali]
    D --> E[Preview Documento]
    E --> F[Conferma e Salvataggio]
    F --> G[Generazione PDF]
```

### 5. 💰 Modulo Fattura PA (`modules/fattura_pa.py`)
**Funzionalità**: Fatturazione Elettronica Pubblica Amministrazione

#### Features:
- **Generazione XML**: Formato standard FatturaPA
- **Validazione Dati**: Controllo conformità PA
- **Gestione CIG/CUP**: Codici identificativi gara
- **Firma Digitale**: Supporto firma qualificata
- **Invio SDI**: Integrazione Sistema Interscambio

### 6. 👥 Modulo Clients (`modules/clients.py`)
**Funzionalità**: Gestione clienti e fornitori

#### Features:
- **Anagrafica Completa**: Dati fiscali e commerciali
- **Classificazione Clienti**: Categorizzazione per tipo
- **Storico Ordini**: Visualizzazione acquisti precedenti
- **Gestione Crediti**: Controllo saldo clienti
- **Esportazione Dati**: Export per sistemi esterni

### 7. 🏷️ Modulo Articles (`modules/articles.py`)
**Funzionalità**: Gestione articoli e prodotti

#### Features:
- **Catalogo Prodotti**: Database completo articoli
- **Gestione Prezzi**: Listini e scontistiche
- **Controllo Stock**: Monitoraggio giacenze
- **Codici EAN**: Gestione barcode/QR code
- **Categorizzazione**: Organizzazione per famiglie/sezioni

### 8. 🏬 Modulo Sections (`modules/sections.py`)
**Funzionalità**: Gestione sezioni magazzino

#### Features:
- **Organizzazione Spazi**: Mapping aree magazzino
- **Assegnazione Prodotti**: Posizionamento articoli
- **Visualizzazione Grafica**: Mappe interattive sezioni
- **Ottimizzazione Layout**: Suggerimenti posizionamento

### 9. 🍎 Modulo Ingredients (`modules/ingredients.py`)
**Funzionalità**: Gestione ingredienti e food cost

#### Features:
- **Catalogo Ingredienti**: Database completo ingredienti
- **Gestione Fornitori**: Anagrafica fornitori ingredienti
- **Associazione Articoli**: Collegamento ingredienti-prodotti
- **Food Cost Calculation**: Calcolo automatico costi ricette
- **Gestione Scorte**: Controllo giacenze ingredienti
- **Report Analitici**: Analisi marginalità e redditività

### 10. 💰 Modulo Listini (`modules/listini.py`)
**Funzionalità**: Gestione listini prezzi e scontistiche

#### Features:
- **Listini Dinamici**: Prezzi differenziati per cliente/tipo
- **Scontistiche Configurabili**: Regole prezzi personalizzate
- **Gestione Promozioni**: Offerte temporanee e stagionali
- **Integrazione Clienti**: Listini specifici per categorie
- **Report Vendite**: Analisi prezzi e marginalità

### 11. 💬 Servizio Chat (`services/chat.py`)
**Funzionalità**: Sistema comunicazione interno

#### Features:
- **Chat Real-time**: Messaggistica istantanea
- **Stanze Multiple**: Canali tematici
- **Notifiche**: Alert nuovi messaggi
- **Cronologia**: Storico conversazioni
- **Integrazione Task**: Chat collegata a task specifici

## ⚙️ Installazione e Configurazione

### Prerequisiti Sistema
```bash
# Sistema Operativo
Windows 10/11 o Linux Ubuntu 18.04+

# Python
Python 3.8 - 3.11 (testato)

# Database
MySQL 8.0+ o MariaDB 10.5+

# Hardware Raccomandato
RAM: 4GB+ (8GB+ consigliati)
CPU: 2+ cores
Disco: 10GB+ spazio libero
```

### Installazione

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/DBLogiX.git
cd DBLogiX
```

#### 2. Ambiente Virtuale
```bash
# Creazione virtual environment
python -m venv venv

# Attivazione
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

#### 3. Dipendenze
```bash
# Installazione requirements
pip install -r requirements.txt

# Verifica installazione
pip list
```

#### 4. Configurazione Database
```python
# app/config.py
REMOTE_DB_CONFIG = {
    'host': '192.168.1.32',           # IP server MySQL
    'user': 'dblogix_user',           # Username database
    'password': 'secure_password',    # Password database
    'database': 'sys_datos',          # Nome database
    'port': 3306,                     # Porta MySQL
    'charset': 'utf8',                # Charset
}
```

#### 5. Variabili Ambiente
```bash
# .env file
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
DB_HOST=192.168.1.32
DB_USER=dblogix_user
DB_PASSWORD=secure_password
DB_NAME=sys_datos
```

#### 6. Inizializzazione Database
```bash
# Creazione tabelle
python main.py

# O utilizzo Flask-Migrate
flask db upgrade
```

#### 7. Primo Avvio
```bash
# Avvio applicazione
python main.py

# Oppure modalità development
flask run --debug
```

### Configurazione Avanzata

#### Config Manager Esterno
Il sistema supporta configurazioni esterne tramite `config_manager.py`:

```python
# Configurazioni supportate
- Database connection
- Company settings  
- System parameters
- Chat configuration
- Client management
- DDT settings
- Invoice settings
```

#### Backup Automatico
```python
# Configurazione backup in config.py
BACKUP_CONFIG = {
    'enabled': True,
    'interval_hours': 24,
    'retention_days': 30,
    'backup_path': './Backup/'
}
```

## 🌐 API e Endpoint

### Autenticazione
```python
POST /auth/login          # Login utente
POST /auth/logout         # Logout utente
GET  /auth/register       # Registrazione (admin only)
```

### Warehouse Management
```python
GET  /warehouse/                    # Dashboard magazzino
GET  /warehouse/scanner            # Interfaccia scanner
POST /warehouse/scan               # Processamento scansione
GET  /warehouse/tickets            # Lista ticket
GET  /warehouse/ticket/<id>        # Dettaglio ticket
POST /warehouse/checkout           # Checkout prodotti
```

### Task Management  
```python
GET  /tasks/                       # Dashboard task
POST /tasks/create                 # Creazione task
GET  /tasks/view/<id>             # Visualizzazione task
PUT  /tasks/edit/<id>             # Modifica task
POST /tasks/assign                # Assegnazione task
GET  /tasks/notifications         # Notifiche task
```

### DDT Management
```python
GET  /ddt/                        # Lista DDT
POST /ddt/generate                # Generazione DDT
GET  /ddt/preview/<id>           # Anteprima DDT
GET  /ddt/detail/<id>            # Dettaglio DDT
POST /ddt/select_client          # Selezione cliente
POST /ddt/select_tickets         # Selezione ticket
```

### Client Management
```python
GET  /clients/                    # Lista clienti
POST /clients/create              # Creazione cliente
GET  /clients/edit/<id>          # Modifica cliente
DELETE /clients/delete/<id>      # Eliminazione cliente
GET  /clients/search             # Ricerca clienti
```

### Articles Management
```python
GET  /articles/                   # Catalogo articoli
POST /articles/create             # Creazione articolo
PUT  /articles/edit/<id>         # Modifica articolo
DELETE /articles/delete/<id>     # Eliminazione articolo
GET  /articles/search            # Ricerca articoli
POST /articles/import            # Importazione massiva
```

### Listini Management
```python
GET  /listini/                    # Lista listini prezzi
POST /listini/new                 # Creazione listino
GET  /listini/<id>               # Visualizzazione listino
PUT  /listini/<id>/edit          # Modifica listino
DELETE /listini/<id>/delete      # Eliminazione listino
POST /listini/<id>/aggiungi_articoli  # Aggiunta articoli al listino
POST /listini/<id>/rimuovi_articolo   # Rimozione articolo dal listino
POST /listini/<id>/modifica_prezzo    # Modifica prezzo articolo
POST /listini/<id>/copia         # Duplicazione listino
GET  /listini/<id>/api/articoli_disponibili  # Articoli disponibili per listino
GET  /listini/<id>/api/search_clients       # Ricerca clienti per assegnazione
POST /listini/<id>/assign_client    # Assegnazione listino a cliente
POST /listini/<id>/remove_client    # Rimozione listino da cliente
GET  /listini/api/prezzi_per_cliente/<id>    # Prezzi per cliente specifico
```

### Ingredients Management
```python
GET  /ingredients/                   # Dashboard ingredienti
GET  /ingredients/ingredienti        # Lista ingredienti
POST /ingredients/ingredienti/new    # Creazione ingrediente
GET  /ingredients/ingredienti/<id>   # Visualizzazione ingrediente
PUT  /ingredients/ingredienti/<id>/edit  # Modifica ingrediente
DELETE /ingredients/ingredienti/<id>/delete  # Eliminazione ingrediente
GET  /ingredients/fornitori          # Lista fornitori
POST /ingredients/fornitori/new      # Creazione fornitore
GET  /ingredients/fornitori/<id>     # Visualizzazione fornitore
PUT  /ingredients/fornitori/<id>/edit   # Modifica fornitore
DELETE /ingredients/fornitori/<id>/delete  # Eliminazione fornitore
GET  /ingredients/food_cost          # Dashboard food cost
GET  /ingredients/api/search         # Ricerca ingredienti/fornitori
```

### Admin Panel
```python
GET  /admin/                      # Dashboard admin
GET  /admin/users                 # Gestione utenti
POST /admin/users/create          # Creazione utente
GET  /admin/config               # Configurazioni sistema
POST /admin/config/update        # Aggiornamento config
GET  /admin/stats                # Statistiche sistema
GET  /admin/logs                 # Visualizzazione log
```

### Utility API
```python
GET  /api/scan_network           # Scansione rete per dispositivi
POST /api/set_db_ip             # Impostazione IP database
POST /api/test_db_connection    # Test connessione database
GET  /uploads/<filename>        # Accesso file caricati
```

### WebSocket Endpoints
```javascript
// Chat real-time
/chat/messages                   // Messaggi chat
/chat/notifications             // Notifiche istantanee

// Task notifications
/tasks/status_updates           // Aggiornamenti stato task
/tasks/progress_updates         // Aggiornamenti progresso
```

## 🎨 Frontend e UI

### Framework e Librerie
```html
<!-- CSS Framework -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">

<!-- JavaScript Libraries -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
```

### Struttura CSS
```css
/* File CSS principali */
static/css/
├── base.css              /* Stili base globali */
├── admin.css             /* Pannello amministrazione */
├── warehouse.css         /* Interfaccia magazzino */
├── tasks.css             /* Sistema task */
├── ddt.css               /* Documenti trasporto */
├── articles.css          /* Gestione articoli */
├── clients.css           /* Gestione clienti */
├── chat.css              /* Sistema chat */
└── shared-components.css /* Componenti riutilizzabili */
```

### JavaScript Modulare
```javascript
// File JavaScript principali
static/js/
├── main.js                    // Funzioni globali
├── shared-components.js       // Componenti condivisi
├── tasks.js                   // Logica task management
├── notifications.js           // Sistema notifiche
├── chat.js                    // Chat real-time
├── sidebar.js                 // Navigazione sidebar
├── responsive.js              // Responsive design
└── admin/                     // Script amministrazione
    ├── dashboard.js
    ├── users.js
    └── config.js
```

### Template Jinja2
```html
<!-- Template base -->
templates/base.html
├── Header navigation
├── Sidebar menu
├── Flash messages
├── Main content area
└── Footer

<!-- Template specializzati -->
templates/
├── warehouse/
│   ├── index.html           <!-- Dashboard magazzino -->
│   ├── scanner.html         <!-- Interfaccia scanner -->
│   └── tickets.html         <!-- Lista ticket -->
├── tasks/
│   ├── admin_dashboard.html <!-- Dashboard admin task -->
│   ├── user_dashboard.html  <!-- Dashboard utente -->
│   └── task_screen.html     <!-- Schermo dedicato task -->
└── admin/
    ├── dashboard/
    └── configurazioni/
```

### Responsive Design
```css
/* Breakpoints responsivi */
@media (max-width: 576px) { /* Mobile */ }
@media (max-width: 768px) { /* Tablet */ }
@media (max-width: 992px) { /* Desktop small */ }
@media (max-width: 1200px) { /* Desktop large */ }
```

### Componenti UI Personalizzati

#### Scanner Interface
```html
<!-- Scanner QR/Barcode -->
<div class="scanner-container">
    <video id="scanner-video"></video>
    <div class="scanner-overlay">
        <div class="scanner-frame"></div>
        <div class="scanner-info">
            <p>Inquadra il QR Code del prodotto</p>
        </div>
    </div>
</div>
```

#### Task Cards
```html
<!-- Card task con progress bar -->
<div class="task-card">
    <div class="task-header">
        <h5 class="task-title">{{ task.title }}</h5>
        <span class="task-priority badge">{{ task.priority }}</span>
    </div>
    <div class="task-progress">
        <div class="progress">
            <div class="progress-bar" style="width: {{ task.progress_percentage }}%"></div>
        </div>
        <small>{{ task.completed_tickets }}/{{ task.total_tickets }} completati</small>
    </div>
</div>
```

#### Notification System
```javascript
// Sistema notifiche toast
function showNotification(message, type = 'info', duration = 5000) {
    const toast = `
        <div class="toast align-items-center text-white bg-${type}" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    document.getElementById('toast-container').insertAdjacentHTML('beforeend', toast);
}
```

## 🔐 Sicurezza e Autenticazione

### Sistema Autenticazione
```python
# Flask-Login integration
from flask_login import LoginManager, login_required, current_user

# User authentication
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
```

### Livelli Autorizzazione
| Ruolo | Permessi |
|-------|----------|
| **Admin** | Accesso completo sistema, gestione utenti, configurazioni |
| **Manager** | Gestione task, visualizzazione report, creazione DDT |
| **Operator** | Scansione prodotti, completamento task assegnati |
| **Viewer** | Solo visualizzazione dati, report read-only |

### Protezione CSRF
```python
# CSRF Protection
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)

# Form protection
class TicketForm(FlaskForm):
    csrf_token = HiddenField()
    # ... altri campi
```

### Password Security
```python
# Password hashing con Werkzeug
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, password):
    self.password_hash = generate_password_hash(password)

def check_password(self, password):
    return check_password_hash(self.password_hash, password)
```

### Session Management
```python
# Configurazione sessioni
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### API Security
```python
# Rate limiting per API
from flask_limiter import Limiter

@app.route('/api/scan', methods=['POST'])
@login_required
@limiter.limit("100 per minute")
def api_scan():
    # API endpoint con limitazione rate
```

## 📊 Logging e Monitoraggio

### Sistema Logging
```python
# Configurazione logging
import logging
from logging.handlers import RotatingFileHandler

# Log files
logs/
├── dblogix.log          # Log applicazione principale
├── error.log            # Log errori sistema
├── scan.log             # Log scansioni prodotti
├── task.log             # Log operazioni task
└── security.log         # Log eventi sicurezza
```

### Livelli Log
```python
# Configurazione log levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/dblogix.log', maxBytes=10240, backupCount=5),
        logging.StreamHandler()
    ]
)
```

### Monitoraggio Prestazioni
```python
# Metriche sistema
- Tempo risposta API endpoints
- Numero scansioni per ora/giorno
- Task completati per operatore
- Errori database connection
- Utilizzo memoria e CPU
```

### Dashboard Monitoring
```html
<!-- Pannello monitoraggio admin -->
/admin/stats
├── Statistiche scansioni
├── Performance database
├── Utilizzo sistema
├── Log errori recenti
└── Metriche utenti attivi
```

## 🚀 Deployment

### Sistema di Build Modulare

Il progetto utilizza un sistema di build modulare avanzato per la distribuzione:

#### 1. Build System Overview
```bash
# Build completo (dalla root)
python build.py

# Il sistema esegue automaticamente:
# 1. Download Python 3.11.9 embedded
# 2. Creazione directory build
# 3. Copia file applicazione
# 4. Generazione servizio Windows
# 5. Creazione installer Inno Setup
# 6. Configurazione SSL/TLS
# 7. Setup firewall rules
```

#### 2. Configurazione .NET
Il sistema supporta configurazioni avanzate tramite `DBLogix.exe.config`:

```xml
<!-- Configurazioni Database -->
<add key="DB_HOST" value="192.168.1.150" />
<add key="DB_USER" value="user" />
<!-- Configurazioni Azienda -->
<add key="COMPANY_NAME" value="Test Company SRL" />
<!-- Configurazioni Sistema -->
<add key="BACKUP_FREQUENCY_HOURS" value="24" />
<!-- SSL/Network -->
<add key="USE_SSL" value="True" />
<add key="NETWORK_SCAN_TIMEOUT" value="5" />
```

### Deployment Windows

#### 1. Servizio Windows Automatico
Il build system genera automaticamente il servizio Windows:

#### 2. Installer Inno Setup
L'installer viene generato automaticamente con:

```ini
[Setup]
AppName=DBLogiX
AppVersion=4.7.0
PrivilegesRequired=admin
ArchitecturesAllowed=x64

[Tasks]
Name: "installservice"; Description: "Install Windows Service"
Name: "firewallrules"; Description: "Create firewall rules"

[Run]
# Regole firewall automatiche per porta 5000
# Installazione e avvio servizio Windows
# Apertura dell'app al termine installazione
```

#### 3. Installazione Database
Il sistema include script di installazione completi:

```bash
# Script Windows batch
Install_DBLogiX.bat

# Schema database completo
Install_DBLogiX_Complete.sql

# Modalità kiosk
Kiosk - DBlogiX.bat
```

#### 4. Sistema di Aggiornamento Automatico
Il progetto include un sistema di update e deploy avanzato:

```python
# build_system/update_and_deploy.py
# Funzionalità:
# - Backup versione corrente
# - Download nuova versione
# - Aggiornamento servizio Windows
# - Verifica integrità
# - Rollback automatico in caso di errori
```

#### 5. Modalità Kiosk
Sistema dedicato per funzionamento in modalità kiosk:

```batch
# Avvio automatico in modalità kiosk
Kiosk - DBlogiX.bat
# - Avvio automatico all'accensione
# - Interfaccia semplificata
# - Blocco funzioni amministrative
```

### Deployment Linux

#### 1. Systemd Service
```ini
# /etc/systemd/system/dblogix.service
[Unit]
Description=DBLogiX Warehouse Management
After=network.target

[Service]
Type=simple
User=dblogix
WorkingDirectory=/opt/dblogix
ExecStart=/opt/dblogix/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 2. Nginx Proxy
```nginx
# /etc/nginx/sites-available/dblogix
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "main.py"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  dblogix:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DB_HOST=mysql
    depends_on:
      - mysql
      
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=sys_datos
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

### Configurazione Produzione

#### Gunicorn WSGI
```python
# gunicorn_config.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
keepalive = 2
timeout = 30
```

#### Avvio Produzione
```bash
# Con Gunicorn
gunicorn --config gunicorn_config.py main:app

# Con uWSGI
uwsgi --http :5000 --wsgi-file main.py --callable app --processes 4
```

## 🧪 Testing

### Framework Testing
```python
# Librerie testing
pytest==7.4.0
pytest-flask==1.3.0
pytest-cov==4.1.0
factory-boy==3.3.0
```

### Struttura Test
```
tests/
├── conftest.py              # Configurazione pytest
├── test_models.py           # Test modelli database
├── test_auth.py             # Test autenticazione
├── test_warehouse.py        # Test funzionalità magazzino
├── test_tasks.py            # Test sistema task
├── test_ddt.py              # Test generazione DDT
├── test_api.py              # Test API endpoints
└── fixtures/                # Dati test
    ├── users.json
    ├── products.json
    └── tickets.json
```

### Test Esempi
```python
# test_warehouse.py
import pytest
from app.models import TicketHeader, Product

class TestWarehouse:
    def test_ticket_creation(self, client, auth_user):
        """Test creazione ticket magazzino"""
        response = client.post('/warehouse/create_ticket', data={
            'product_id': 1,
            'quantity': 10,
            'expiry_date': '2024-12-31'
        })
        assert response.status_code == 201
        
    def test_qr_scan(self, client, sample_ticket):
        """Test scansione QR code"""
        qr_data = f"P{sample_ticket.product_id}D{sample_ticket.date}T{sample_ticket.time}"
        response = client.post('/warehouse/scan', json={'qr_code': qr_data})
        assert response.json['status'] == 'success'
```

### Coverage Report
```bash
# Esecuzione test con coverage
pytest --cov=app --cov-report=html

# Report generato in htmlcov/index.html
# Target coverage: 85%+
```

## 🤝 Contributi

### Guidelines Sviluppo

#### Code Style
```python
# Utilizzare Black per formatting
black --line-length 88 *.py

# Utilizzare isort per import ordering
isort --profile black *.py

# Utilizzare flake8 per linting
flake8 --max-line-length 88 --extend-ignore E203,W503
```

#### Commit Messages
```bash
# Formato commit standardizzato
type(scope): description

# Esempi:
feat(warehouse): add QR code batch scanning
fix(ddt): resolve PDF generation encoding issue
docs(readme): update installation instructions
refactor(models): optimize database queries
```

#### Branch Strategy
```
main                    # Branch produzione
├── develop            # Branch sviluppo
├── feature/xxx        # Nuove funzionalità
├── hotfix/xxx         # Fix critici
└── release/xxx        # Preparazione rilasci
```

### Development Workflow

#### 1. Setup Environment
```bash
# Fork repository
git clone https://github.com/your-username/DBLogiX.git
cd DBLogiX

# Setup development environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 2. Feature Development
```bash
# Crea feature branch
git checkout -b feature/new-scanner-interface

# Sviluppo e test
python -m pytest tests/

# Commit changes
git add .
git commit -m "feat(scanner): add new batch scanning interface"

# Push and create PR
git push origin feature/new-scanner-interface
```

#### 3. Code Review
- Revisione codice automatica con GitHub Actions
- Test coverage minimo 80%
- Documentazione aggiornata
- Approvazione mantenitori

---

## 📦 Build System e Distribuzione

### Architettura Build System

Il progetto utilizza un sistema di build modulare avanzato per la distribuzione enterprise:

```mermaid
flowchart TD
    A[build.py] --> B[Build System Modular]
    B --> C[Python Embedded 3.11.9]
    B --> D[File Operations]
    B --> E[SSL Certificates]
    B --> F[Windows Service]
    B --> G[Inno Setup Installer]
    
    G --> H[DBLogiX_Setup.exe]
    H --> I[Service Installation]
    H --> J[Firewall Rules]
    H --> K[Desktop Shortcuts]
    H --> L[Auto-Start Web App]
```

### Moduli Build System

| Modulo | Funzione | Features |
|--------|----------|----------|
| `main_builder.py` | Orchestrazione build | Python version check, directory setup |
| `python_embedded.py` | Runtime embedding | Download Python 3.11.9, configurazione path |
| `inno_setup.py` | Installer generation | Script ISS, icone, shortcuts |
| `launcher_service.py` | Servizio Windows | Auto-start, gestione processi |
| `ssl_certificates.py` | Sicurezza HTTPS | Certificati self-signed, configurazione TLS |
| `update_and_deploy.py` | Sistema update | Backup, rollback, verifica integrità |
| `file_operations.py` | Gestione file | Copia, compressione, cleanup |

### Flusso di Distribuzione

1. **Build Phase**: Creazione package con Python embedded
2. **Service Phase**: Generazione servizio Windows nativo
3. **Installer Phase**: Creazione setup Inno Setup
4. **Deploy Phase**: Installazione automatica con privilegi admin
5. **Configuration Phase**: Setup database, firewall, SSL

## 📈 Roadmap

### Versione 4.8 - STABILE
- [x] Sistema build modulare completo
- [x] Installer Inno Setup automatico
- [x] Servizio Windows nativo
- [x] Modalità kiosk integrata
- [x] Sistema di update automatico
- [x] Configurazione .NET avanzata
- [x] Moduli ingredients e listini completi
- [x] Documentazione README aggiornata

### Prossime Versioni (Roadmap)
- [ ] API REST complete con OpenAPI/Swagger
- [ ] Mobile app per scansioni
- [ ] Integrazione IoT sensori magazzino
- [ ] Dashboard analytics avanzate
- [ ] Sistema backup cloud
- [ ] Container Docker ufficiali
- [ ] Machine Learning per previsioni stock
- [ ] Integrazione sistemi ERP esterni
- [ ] Workflow automatizzati avanzati
- [ ] Multi-tenant architecture
- [ ] Plugin system per estensioni
- [ ] Blockchain per tracciabilità
- [ ] AI per ottimizzazione logistica
- [ ] Realtà aumentata per picking
- [ ] Integrazione e-commerce
- [ ] Advanced reporting e BI

---

## 📞 Supporto

### Documentazione
- **Wiki**: [Documentazione completa](https://github.com/your-org/DBLogiX/wiki)
- **API Reference**: [Endpoint documentation](https://api.dblogix.com/docs)
- **Video Tutorials**: [YouTube Channel](https://youtube.com/dblogix)

### Community
- **Forum**: [Community discussions](https://forum.dblogix.com)
- **Discord**: [Real-time chat](https://discord.gg/dblogix)
- **Telegram**: [Aggiornamenti e supporto](https://t.me/dblogix_support)

### Support Commerciale
- **Email**: support@dblogix.com  
- **Telefono**: +39 XXX XXX XXXX
- **Ticket System**: [Support portal](https://support.dblogix.com)

---

## 📄 Licenza

```
Copyright (c) 2024 DBLogiX Team
Tutti i diritti riservati.

Questo software è proprietario e confidenziale.
La distribuzione, modifica o utilizzo non autorizzato è vietato.

Per informazioni sulla licenza commerciale:
Email: licensing@dblogix.com
```

---

## 🙏 Ringraziamenti

- **Team di Sviluppo**: Per l'impegno costante nel migliorare il sistema
- **Beta Testers**: Aziende partner che hanno testato il sistema
- **Community**: Contributori e utilizzatori che forniscono feedback prezioso
- **Open Source Projects**: Flask, SQLAlchemy, Bootstrap e tutte le librerie utilizzate

## 🤖 Integrazione AI e RAG

### Sistema RAG (Retrieval-Augmented Generation)

Il progetto include documentazione per integrazione con sistemi AI avanzati:

```
RAG CURSOR.txt - Template per agent AI Cloud 4 Sonnet
├── Istruzioni sistema avanzate
├── Modalità continuazione chaining
├── Panoramica strumenti disponibili
├── Esempi e formati output
└── Workflow RAG completo
```

#### Strumenti AI Disponibili
- **Motore Ricerca Interno**: Query full-text su documentazione
- **Vector Database**: Ricerche semantiche con embedding
- **API RESTful**: Integrazione endpoint esterni
- **Code Execution**: Valutazione snippet Python
- **Summarization Tool**: Sintesi documenti lunghi
- **Database Query**: Interrogazioni SQL intelligenti

### Configurazioni Avanzate

#### File di Configurazione Multipli
Il sistema supporta configurazioni stratificate:

```
1. DBLogix.exe.config (Runtime .NET)
2. app/config.py (Flask application)
3. app/config_manager.py (External config)
4. .env (Environment variables)
```

#### Configurazioni Sistema
- **Database**: Connection pooling, timeout, charset
- **Sicurezza**: Session management, CSRF protection
- **Backup**: Frequenza, retention, percorsi
- **Email**: SMTP, notifiche automatiche
- **Chat**: Auto-cleanup, backup incrementali
- **Network**: Scan timeout, SSL/TLS

---

## 📋 Checklist Pre-Produzione

### ✅ Sistema Build
- [x] Build system modulare funzionante
- [x] Python 3.11.9 embedded integrato
- [x] Installer Inno Setup automatico
- [x] Servizio Windows auto-start
- [x] Certificati SSL self-signed
- [x] Firewall rules automatiche

### ✅ Database
- [x] Schema completo con migrazioni
- [x] Script installazione automatica
- [x] Backup automatico configurabile
- [x] Connection pooling ottimizzato

### ✅ Sicurezza
- [x] Autenticazione Flask-Login
- [x] CSRF protection abilitata
- [x] Session management sicuro
- [x] Password hashing Werkzeug
- [x] Logging eventi sicurezza

### ✅ Frontend
- [x] 15 fogli CSS specializzati
- [x] Responsive design completo
- [x] Componenti UI riutilizzabili
- [x] Sistema notifiche toast
- [x] Dashboard interattive

### ✅ Distribuzione
- [x] Modalità kiosk integrata
- [x] Sistema update automatico
- [x] Configurazione .NET avanzata
- [x] Script installazione database
- [x] Documentazione AI/RAG

---

*Ultima modifica: Gennaio 2025*
*Versione README: 4.0.0*
*Build System: 4.8.0*