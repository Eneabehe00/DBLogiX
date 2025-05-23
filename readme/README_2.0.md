# DB-LogiX - Database Schema Documentation

Questo documento fornisce una panoramica dettagliata di tutte le tabelle e i campi utilizzati nel progetto DB-LogiX per la gestione dei documenti di trasporto (DDT).

## Tabelle del Database

### 1. dat_cliente
Contiene le informazioni relative ai clienti.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [IdCliente](#client-model) | Integer | Chiave primaria | [models.py:18](#client-model) |
| [IdEmpresa](#client-model) | Integer | ID dell'azienda associata | [models.py:19](#client-model) |
| [Nombre](#client-model) | String(100) | Nome del cliente | [models.py:20](#client-model) |
| [Direccion](#client-model) | String(200) | Indirizzo | [models.py:21](#client-model) |
| [CodPostal](#client-model) | String(10) | Codice postale | [models.py:22](#client-model) |
| [Poblacion](#client-model) | String(100) | Città | [models.py:23](#client-model) |
| [Provincia](#client-model) | String(100) | Provincia | [models.py:24](#client-model) |
| [Pais](#client-model) | String(100) | Paese | [models.py:25](#client-model) |
| [DNI](#client-model) | String(20) | Partita IVA o codice fiscale | [models.py:26](#client-model) |
| [Telefono1](#client-model) | String(20) | Numero di telefono principale | [models.py:27](#client-model) |
| [Telefono2](#client-model) | String(20) | Numero di telefono secondario | [models.py:28](#client-model) |
| [Telefono3](#client-model) | String(20) | Numero di telefono alternativo | [models.py:29](#client-model) |
| [Email](#client-model) | String(100) | Indirizzo email | [models.py:30](#client-model) |
| [TipoEmailTicket](#client-model) | Integer | Flag per l'invio dei ticket via email | [models.py:31](#client-model) |
| [TipoEmailAlbaran](#client-model) | Integer | Flag per l'invio degli albaran via email | [models.py:32](#client-model) |
| [TipoEmailFactura](#client-model) | Integer | Flag per l'invio delle fatture via email | [models.py:33](#client-model) |
| [Foto](#client-model) | LargeBinary | Foto del cliente | [models.py:34](#client-model) |
| [IdTarifa](#client-model) | Integer | ID della tariffa applicata | [models.py:35](#client-model) |
| [Ofertas](#client-model) | Integer | Flag per offerte speciali | [models.py:36](#client-model) |
| [IdFormaPago](#client-model) | Integer | Modalità di pagamento | [models.py:37](#client-model) |
| [IdEstado](#client-model) | Integer | Stato del cliente | [models.py:38](#client-model) |
| [Observaciones](#client-model) | Text | Note e osservazioni | [models.py:39](#client-model) |
| [CodInterno](#client-model) | String(50) | Codice interno | [models.py:40](#client-model) |
| [Descuento](#client-model) | Numeric(10,2) | Sconto applicato | [models.py:41](#client-model) |
| [PuntosFidelidad](#client-model) | Integer | Punti fedeltà | [models.py:42](#client-model) |
| [CuentaPendiente](#client-model) | Numeric(10,2) | Saldo in sospeso | [models.py:43](#client-model) |
| [EANScanner](#client-model) | String(50) | Codice EAN | [models.py:44](#client-model) |
| [FormatoAlbaran](#client-model) | String(100) | Formato albaran | [models.py:45](#client-model) |
| [UsarRecargoEquivalencia](#client-model) | Integer | Flag per la ricarica di equivalenza | [models.py:46](#client-model) |
| [DtoProntoPago](#client-model) | Numeric(10,2) | Sconto per pagamento anticipato | [models.py:47](#client-model) |
| [NombreBanco](#client-model) | String(100) | Nome della banca | [models.py:48](#client-model) |
| [CodigoCuenta](#client-model) | String(50) | Codice conto bancario | [models.py:49](#client-model) |
| [NumeroVencimientos](#client-model) | Integer | Numero di scadenze | [models.py:50](#client-model) |
| [DiasEntreVencimientos](#client-model) | Integer | Giorni tra le scadenze | [models.py:51](#client-model) |
| [TotalPorArticulo](#client-model) | Integer | Flag per totale per articolo | [models.py:52](#client-model) |
| [AplicarTarifaEtiqueta](#client-model) | Integer | Flag per applicare tariffa etichetta | [models.py:53](#client-model) |
| [FormatoFactura](#client-model) | String(100) | Formato fattura | [models.py:54](#client-model) |
| [ModoFacturacion](#client-model) | Integer | Modalità di fatturazione | [models.py:55](#client-model) |
| [Modificado](#client-model) | Integer | Flag di modifica | [models.py:56](#client-model) |
| [Operacion](#client-model) | Integer | Operazione | [models.py:57](#client-model) |
| [Usuario](#client-model) | String(50) | Utente che ha effettuato modifiche | [models.py:58](#client-model) |
| [TimeStamp](#client-model) | DateTime | Data e ora dell'ultima modifica | [models.py:59](#client-model) |

### 2. dat_ticket_cabecera
Contiene le informazioni di intestazione dei ticket.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [IdTicket](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:99](#ticket-header-model) |
| [IdEmpresa](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:100](#ticket-header-model) |
| [IdTienda](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:101](#ticket-header-model) |
| [IdBalanzaMaestra](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:102](#ticket-header-model) |
| [IdBalanzaEsclava](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:103](#ticket-header-model) |
| [TipoVenta](#ticket-header-model) | Integer | Parte della chiave primaria composita | [models.py:104](#ticket-header-model) |
| [NumTicket](#ticket-header-model) | Integer | Numero del ticket | [models.py:105](#ticket-header-model) |
| [Fecha](#ticket-header-model) | DateTime | Data e ora del ticket | [models.py:106](#ticket-header-model) |
| [CodigoBarras](#ticket-header-model) | String(50) | Codice a barre | [models.py:107](#ticket-header-model) |
| [NumLineas](#ticket-header-model) | Integer | Numero di linee nel ticket | [models.py:108](#ticket-header-model) |
| [Enviado](#ticket-header-model) | Integer | Flag che indica se il ticket è stato inviato | [models.py:109](#ticket-header-model) |

### 3. dat_ticket_linea
Contiene le informazioni dettagliate delle linee di ciascun ticket.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [IdLineaTicket](#ticket-line-model) | Integer | Chiave primaria | [models.py:134](#ticket-line-model) |
| [IdEmpresa](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:135](#ticket-line-model) |
| [IdTienda](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:136](#ticket-line-model) |
| [IdBalanzaMaestra](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:137](#ticket-line-model) |
| [IdBalanzaEsclava](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:138](#ticket-line-model) |
| [TipoVenta](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:139](#ticket-line-model) |
| [IdTicket](#ticket-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:140](#ticket-line-model) |
| [IdArticulo](#ticket-line-model) | Integer | FK - Riferimento a dat_articulo | [models.py:141](#ticket-line-model) |
| [Descripcion](#ticket-line-model) | String(100) | Descrizione dell'articolo | [models.py:142](#ticket-line-model) |
| [Peso](#ticket-line-model) | Numeric(15,3) | Peso dell'articolo | [models.py:143](#ticket-line-model) |
| [FechaCaducidad](#ticket-line-model) | DateTime | Data di scadenza | [models.py:144](#ticket-line-model) |

### 4. dat_articulo
Contiene le informazioni sui prodotti.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [IdArticulo](#product-model) | Integer | Chiave primaria | [models.py:68](#product-model) |
| [Descripcion](#product-model) | String(100) | Descrizione del prodotto | [models.py:69](#product-model) |
| [PrecioConIVA](#product-model) | Numeric(13,3) | Prezzo con IVA inclusa | [models.py:70](#product-model) |
| [EANScanner](#product-model) | String(50) | Codice EAN | [models.py:71](#product-model) |
| [IdFamilia](#product-model) | Integer | ID della famiglia di prodotti | [models.py:72](#product-model) |
| [IdSubFamilia](#product-model) | Integer | ID della sottofamiglia di prodotti | [models.py:73](#product-model) |
| [IdIva](#product-model) | Integer | ID dell'aliquota IVA (1=4%, 2=10%, 3=22%) | [models.py:74](#product-model) |

### 5. dat_empresa
Contiene le informazioni sulle aziende.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [IdEmpresa](#company-model) | Integer | Chiave primaria | [models.py:216](#company-model) |
| [Nombre](#company-model) | String(100) | Nome dell'azienda | [models.py:217](#company-model) |
| [Direccion](#company-model) | String(200) | Indirizzo | [models.py:218](#company-model) |
| [CodPostal](#company-model) | String(10) | Codice postale | [models.py:219](#company-model) |
| [Ciudad](#company-model) | String(100) | Città | [models.py:220](#company-model) |
| [Provincia](#company-model) | String(100) | Provincia | [models.py:221](#company-model) |
| [Pais](#company-model) | String(100) | Paese | [models.py:222](#company-model) |
| [VAT](#company-model) | String(50) | Partita IVA | [models.py:223](#company-model) |
| [Telefono](#company-model) | String(20) | Numero di telefono | [models.py:224](#company-model) |
| [Email](#company-model) | String(100) | Indirizzo email | [models.py:225](#company-model) |

### 6. ddt_head
Contiene le informazioni di intestazione dei documenti di trasporto (DDT).

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [id](#ddt-head-model) | Integer | Chiave primaria | [models.py:230](#ddt-head-model) |
| [id_cliente](#ddt-head-model) | Integer | FK - Riferimento a dat_cliente.IdCliente | [models.py:231](#ddt-head-model) |
| [id_empresa](#ddt-head-model) | Integer | FK - Riferimento a dat_empresa.IdEmpresa | [models.py:232](#ddt-head-model) |
| [data_creazione](#ddt-head-model) | DateTime | Data di creazione del DDT | [models.py:233](#ddt-head-model) |
| [totale_senza_iva](#ddt-head-model) | Numeric(10,2) | Totale senza IVA | [models.py:234](#ddt-head-model) |
| [totale_iva](#ddt-head-model) | Numeric(10,2) | Totale dell'IVA | [models.py:235](#ddt-head-model) |
| [totale_importo](#ddt-head-model) | Numeric(10,2) | Totale complessivo | [models.py:236](#ddt-head-model) |

### 7. ddt_line
Contiene le informazioni dettagliate delle linee di ciascun DDT.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [id](#ddt-line-model) | Integer | Chiave primaria | [models.py:267](#ddt-line-model) |
| [id_ddt](#ddt-line-model) | Integer | FK - Riferimento a ddt_head.id | [models.py:268](#ddt-line-model) |
| [id_empresa](#ddt-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:269](#ddt-line-model) |
| [id_tienda](#ddt-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:270](#ddt-line-model) |
| [id_balanza_maestra](#ddt-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:271](#ddt-line-model) |
| [id_balanza_esclava](#ddt-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:272](#ddt-line-model) |
| [tipo_venta](#ddt-line-model) | Integer | FK - Riferimento a dat_ticket_cabecera | [models.py:273](#ddt-line-model) |
| [id_ticket](#ddt-line-model) | BigInteger | FK - Riferimento a dat_ticket_cabecera | [models.py:274](#ddt-line-model) |

### 8. users
Contiene le informazioni sugli utenti del sistema.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [id](#user-model) | Integer | Chiave primaria | [models.py:175](#user-model) |
| [username](#user-model) | String(64) | Nome utente (unico) | [models.py:176](#user-model) |
| [email](#user-model) | String(120) | Email (unica) | [models.py:177](#user-model) |
| [password_hash](#user-model) | String(128) | Hash della password | [models.py:178](#user-model) |
| [is_admin](#user-model) | Boolean | Flag che indica se l'utente è amministratore | [models.py:179](#user-model) |
| [created_at](#user-model) | DateTime | Data di creazione dell'account | [models.py:180](#user-model) |

### 9. scan_log
Contiene i log delle operazioni di scansione.

| Campo | Tipo | Descrizione | Gestito in |
|-------|------|-------------|------------|
| [id](#scan-log-model) | Integer | Chiave primaria | [models.py:195](#scan-log-model) |
| [user_id](#scan-log-model) | Integer | FK - Riferimento a users.id | [models.py:196](#scan-log-model) |
| [ticket_id](#scan-log-model) | Integer | ID del ticket scansionato | [models.py:197](#scan-log-model) |
| [action](#scan-log-model) | String(20) | Tipo di azione (view, scan, scan_attempt, checkout) | [models.py:198](#scan-log-model) |
| [timestamp](#scan-log-model) | DateTime | Data e ora dell'azione | [models.py:199](#scan-log-model) |
| [raw_code](#scan-log-model) | String(50) | Codice grezzo scansionato | [models.py:200](#scan-log-model) |
| [product_code](#scan-log-model) | Integer | Codice del prodotto | [models.py:201](#scan-log-model) |
| [scan_date](#scan-log-model) | String(20) | Data della scansione | [models.py:202](#scan-log-model) |
| [scan_time](#scan-log-model) | String(20) | Ora della scansione | [models.py:203](#scan-log-model) |

## Relazioni tra Tabelle

### Relazioni Principali

1. **Cliente - DDT**:
   - Un cliente può avere molti DDT
   - Relazione: [`ddt_head.id_cliente`](#ddt-head-model) → [`dat_cliente.IdCliente`](#client-model)

2. **DDT - Ticket**:
   - Un DDT può contenere molti ticket
   - Relazione attraverso [`ddt_line`](#ddt-line-model) che collega [`ddt_head`](#ddt-head-model) a [`dat_ticket_cabecera`](#ticket-header-model)

3. **Ticket - Linee Ticket**:
   - Un ticket contiene molte linee di dettaglio
   - Relazione: composite key in [`dat_ticket_linea`](#ticket-line-model) → composite key in [`dat_ticket_cabecera`](#ticket-header-model)

4. **Linee Ticket - Prodotti**:
   - Ogni linea ticket si riferisce a un prodotto
   - Relazione: [`dat_ticket_linea.IdArticulo`](#ticket-line-model) → [`dat_articulo.IdArticulo`](#product-model)

5. **Azienda - Cliente**:
   - Un'azienda può avere molti clienti
   - Relazione: [`dat_cliente.IdEmpresa`](#client-model) → [`dat_empresa.IdEmpresa`](#company-model)

6. **Azienda - DDT**:
   - Un'azienda può emettere molti DDT
   - Relazione: [`ddt_head.id_empresa`](#ddt-head-model) → [`dat_empresa.IdEmpresa`](#company-model)

## Implementazione dei modelli nel codice

### <a id="client-model"></a>Client Model (models.py)
La classe `Client` in models.py gestisce i dati della tabella `dat_cliente`. I campi sono definiti alle righe 18-59.

```python
class Client(db.Model):
    __tablename__ = 'dat_cliente'
    
    IdCliente = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer)
    Nombre = db.Column(db.String(100))
    # Altri campi...
```

### <a id="ticket-header-model"></a>TicketHeader Model (models.py)
La classe `TicketHeader` in models.py gestisce i dati della tabella `dat_ticket_cabecera`. I campi sono definiti alle righe 99-109.

```python
class TicketHeader(db.Model):
    __tablename__ = 'dat_ticket_cabecera'
    
    IdTicket = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer, primary_key=True)
    # Altri campi...
```

### <a id="ticket-line-model"></a>TicketLine Model (models.py)
La classe `TicketLine` in models.py gestisce i dati della tabella `dat_ticket_linea`. I campi sono definiti alle righe 134-144.

```python
class TicketLine(db.Model):
    __tablename__ = 'dat_ticket_linea'
    
    IdLineaTicket = db.Column(db.Integer, primary_key=True)
    IdEmpresa = db.Column(db.Integer, nullable=False)
    # Altri campi...
```

### <a id="product-model"></a>Product Model (models.py)
La classe `Product` in models.py gestisce i dati della tabella `dat_articulo`. I campi sono definiti alle righe 68-74.

```python
class Product(db.Model):
    __tablename__ = 'dat_articulo'
    
    IdArticulo = db.Column(db.Integer, primary_key=True)
    Descripcion = db.Column(db.String(100))
    # Altri campi...
```

### <a id="company-model"></a>Company Model (models.py)
La classe `Company` in models.py gestisce i dati della tabella `dat_empresa`. I campi sono definiti alle righe 216-225.

```python
class Company(db.Model):
    __tablename__ = 'dat_empresa'
    
    id = db.Column('IdEmpresa', db.Integer, primary_key=True)
    name = db.Column('Nombre', db.String(100))
    # Altri campi...
```

### <a id="ddt-head-model"></a>DDTHead Model (models.py)
La classe `DDTHead` in models.py gestisce i dati della tabella `ddt_head`. I campi sono definiti alle righe 230-236.

```python
class DDTHead(db.Model):
    __tablename__ = 'ddt_head'
    
    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, nullable=False)
    # Altri campi...
```

### <a id="ddt-line-model"></a>DDTLine Model (models.py)
La classe `DDTLine` in models.py gestisce i dati della tabella `ddt_line`. I campi sono definiti alle righe 267-274.

```python
class DDTLine(db.Model):
    __tablename__ = 'ddt_line'
    
    id = db.Column(db.Integer, primary_key=True)
    id_ddt = db.Column(db.Integer, db.ForeignKey('ddt_head.id'), nullable=False)
    # Altri campi...
```

### <a id="user-model"></a>User Model (models.py)
La classe `User` in models.py gestisce i dati della tabella `users`. I campi sono definiti alle righe 175-180.

```python
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    # Altri campi...
```

### <a id="scan-log-model"></a>ScanLog Model (models.py)
La classe `ScanLog` in models.py gestisce i dati della tabella `scan_log`. I campi sono definiti alle righe 195-203.

```python
class ScanLog(db.Model):
    __tablename__ = 'scan_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Altri campi...
```

## Flusso di Lavoro nel Sistema

1. Gli utenti possono cercare i clienti nel database [`dat_cliente`](#client-model)
2. Possono visualizzare e selezionare i ticket disponibili in [`dat_ticket_cabecera`](#ticket-header-model)
3. I ticket selezionati vengono associati a un cliente per creare un nuovo DDT
4. Il sistema calcola i totali basati sulle linee dei ticket e le informazioni sui prodotti
5. Il DDT viene salvato nelle tabelle [`ddt_head`](#ddt-head-model) e [`ddt_line`](#ddt-line-model)
6. Le operazioni vengono registrate nella tabella [`scan_log`](#scan-log-model) 