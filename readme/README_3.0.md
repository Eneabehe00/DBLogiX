# DB-LogiX - Modello DDT e Integrazione delle Tabelle

Questo documento descrive in dettaglio come le tabelle `dat_cliente`, `dat_ticket_cabecera`, `dat_ticket_linea` e `dat_articulo` vengono utilizzate nel modello del Documento Di Trasporto (DDT) all'interno del sistema DB-LogiX.

## Panoramica del Modello DDT

Il Documento Di Trasporto (DDT) è un documento fiscale italiano che accompagna la merce durante il trasporto. Nel sistema DB-LogiX, il DDT è implementato attraverso due tabelle principali:

1. `ddt_head` - Contiene le informazioni di intestazione del DDT
2. `ddt_line` - Contiene le linee di dettaglio del DDT, ciascuna associata a un ticket

Queste tabelle si integrano con altre tabelle del database per creare un sistema completo di gestione dei DDT.

## Integrazione delle Tabelle nel Modello DDT

### 1. Relazione tra `dat_cliente` e `ddt_head`

La tabella `dat_cliente` è fondamentale per il modello DDT poiché ogni DDT deve essere associato a un cliente specifico.

#### Flusso dei Dati:
1. Quando l'utente crea un nuovo DDT, deve prima selezionare un cliente dal database.
2. Il sistema recupera tutti i dati del cliente dalla tabella `dat_cliente`.
3. L'ID del cliente selezionato (`IdCliente`) viene salvato nel campo `id_cliente` della tabella `ddt_head`.
4. Le informazioni del cliente (nome, indirizzo, codice fiscale/P.IVA, ecc.) vengono visualizzate nel documento DDT.

#### Campi Chiave Utilizzati:
- `dat_cliente.IdCliente` → `ddt_head.id_cliente`
- `dat_cliente.Nombre` - Nome/Ragione sociale del cliente nel DDT
- `dat_cliente.Direccion` - Indirizzo del cliente nel DDT
- `dat_cliente.CodPostal` - CAP del cliente nel DDT
- `dat_cliente.Poblacion` - Città del cliente nel DDT
- `dat_cliente.Provincia` - Provincia del cliente nel DDT
- `dat_cliente.DNI` - Codice fiscale/P.IVA del cliente nel DDT

#### Codice di Implementazione:
```python
# Esempio di query per ottenere i dati del cliente per un DDT
def get_ddt_client_data(ddt_id):
    ddt = DDTHead.query.get(ddt_id)
    client = Client.query.get(ddt.id_cliente)
    return client
```

### 2. Relazione tra `dat_ticket_cabecera`, `ddt_line` e `ddt_head`

I ticket dalla tabella `dat_ticket_cabecera` vengono associati al DDT attraverso la tabella `ddt_line`, che funge da tabella di collegamento.

#### Flusso dei Dati:
1. Dopo aver selezionato un cliente, l'utente può selezionare uno o più ticket disponibili.
2. Per ogni ticket selezionato, viene creata una nuova riga nella tabella `ddt_line`.
3. Ogni riga in `ddt_line` contiene i riferimenti necessari per identificare univocamente il ticket in `dat_ticket_cabecera` (usando la chiave composita).
4. Il DDT così creato contiene tutti i ticket selezionati, che vengono visualizzati nella sezione dettagli del documento.

#### Campi Chiave Utilizzati:
- `ddt_line.id_ddt` → `ddt_head.id` (collegamento al DDT)
- `ddt_line.id_empresa` → `dat_ticket_cabecera.IdEmpresa` (parte della chiave composita)
- `ddt_line.id_tienda` → `dat_ticket_cabecera.IdTienda` (parte della chiave composita)
- `ddt_line.id_balanza_maestra` → `dat_ticket_cabecera.IdBalanzaMaestra` (parte della chiave composita)
- `ddt_line.id_balanza_esclava` → `dat_ticket_cabecera.IdBalanzaEsclava` (parte della chiave composita)
- `ddt_line.tipo_venta` → `dat_ticket_cabecera.TipoVenta` (parte della chiave composita)
- `ddt_line.id_ticket` → `dat_ticket_cabecera.IdTicket` (parte della chiave composita)

#### Codice di Implementazione:
```python
# Esempio di query per ottenere tutti i ticket associati a un DDT
def get_ddt_tickets(ddt_id):
    ddt_lines = DDTLine.query.filter_by(id_ddt=ddt_id).all()
    
    tickets = []
    for line in ddt_lines:
        ticket = TicketHeader.query.filter_by(
            IdEmpresa=line.id_empresa,
            IdTienda=line.id_tienda,
            IdBalanzaMaestra=line.id_balanza_maestra,
            IdBalanzaEsclava=line.id_balanza_esclava,
            TipoVenta=line.tipo_venta,
            IdTicket=line.id_ticket
        ).first()
        
        if ticket:
            tickets.append(ticket)
    
    return tickets
```

### 3. Relazione tra `dat_ticket_linea`, `dat_articulo` e il DDT

La tabella `dat_ticket_linea` contiene i dettagli delle linee di ciascun ticket, che a loro volta fanno riferimento ai prodotti nella tabella `dat_articulo`. Queste informazioni sono essenziali per calcolare i totali nel DDT.

#### Flusso dei Dati:
1. Per ogni ticket selezionato nel DDT, il sistema recupera tutte le linee associate dalla tabella `dat_ticket_linea`.
2. Per ogni linea del ticket, il sistema recupera le informazioni del prodotto dalla tabella `dat_articulo`.
3. Utilizzando queste informazioni, il sistema calcola i totali (importo, IVA, ecc.) per il DDT.
4. I dettagli dei prodotti e i totali vengono visualizzati nel documento DDT.

#### Campi Chiave Utilizzati:
- `dat_ticket_linea.IdEmpresa`, `dat_ticket_linea.IdTienda`, ecc. → collegamento alla chiave composita in `dat_ticket_cabecera`
- `dat_ticket_linea.IdArticulo` → `dat_articulo.IdArticulo` (riferimento al prodotto)
- `dat_articulo.PrecioConIVA` - Utilizzato per calcolare i totali
- `dat_articulo.IdIva` - Utilizzato per identificare l'aliquota IVA applicabile
- `dat_ticket_linea.Peso` - Utilizzato per calcolare quantità/importo nel DDT

#### Codice di Implementazione:
```python
# Esempio di funzione per calcolare i totali di un DDT
def calculate_ddt_totals(ddt_id):
    total_without_vat = 0
    total_vat = 0
    
    ddt_lines = DDTLine.query.filter_by(id_ddt=ddt_id).all()
    
    for line in ddt_lines:
        # Ottieni il ticket
        ticket = TicketHeader.query.filter_by(
            IdEmpresa=line.id_empresa,
            IdTienda=line.id_tienda,
            IdBalanzaMaestra=line.id_balanza_maestra,
            IdBalanzaEsclava=line.id_balanza_esclava,
            TipoVenta=line.tipo_venta,
            IdTicket=line.id_ticket
        ).first()
        
        if not ticket:
            continue
        
        # Ottieni le linee del ticket
        ticket_lines = TicketLine.query.filter_by(
            IdEmpresa=ticket.IdEmpresa,
            IdTienda=ticket.IdTienda,
            IdBalanzaMaestra=ticket.IdBalanzaMaestra,
            IdBalanzaEsclava=ticket.IdBalanzaEsclava,
            TipoVenta=ticket.TipoVenta,
            IdTicket=ticket.IdTicket
        ).all()
        
        # Calcola i totali per ogni linea
        for t_line in ticket_lines:
            product = Product.query.get(t_line.IdArticulo)
            
            if not product:
                continue
            
            # Determina l'aliquota IVA
            vat_rate = 0
            if product.IdIva == 1:
                vat_rate = 0.04  # 4%
            elif product.IdIva == 2:
                vat_rate = 0.10  # 10%
            elif product.IdIva == 3:
                vat_rate = 0.22  # 22%
            
            # Calcola prezzo senza IVA
            price_with_vat = product.PrecioConIVA
            price_without_vat = price_with_vat / (1 + vat_rate)
            
            # Moltiplica per il peso/quantità
            line_total = price_without_vat * t_line.Peso
            line_vat = line_total * vat_rate
            
            total_without_vat += line_total
            total_vat += line_vat
    
    total_amount = total_without_vat + total_vat
    
    # Aggiorna il DDT con i totali calcolati
    ddt = DDTHead.query.get(ddt_id)
    ddt.totale_senza_iva = total_without_vat
    ddt.totale_iva = total_vat
    ddt.totale_importo = total_amount
    db.session.commit()
    
    return {
        'totale_senza_iva': total_without_vat,
        'totale_iva': total_vat,
        'totale_importo': total_amount
    }
```

## Flusso Completo di Creazione di un DDT

### Passo 1: Selezione del Cliente
1. L'utente cerca un cliente nella tabella `dat_cliente`
2. Una volta selezionato il cliente, le sue informazioni vengono recuperate per l'intestazione del DDT

### Passo 2: Selezione dei Ticket
1. Il sistema mostra tutti i ticket disponibili dalla tabella `dat_ticket_cabecera`
2. L'utente seleziona uno o più ticket da includere nel DDT

### Passo 3: Generazione del DDT
1. Un nuovo record viene creato nella tabella `ddt_head` con le informazioni del cliente
2. Per ogni ticket selezionato, viene creato un record nella tabella `ddt_line`
3. Il sistema recupera i dettagli dei ticket dalla tabella `dat_ticket_linea`
4. Il sistema recupera le informazioni sui prodotti dalla tabella `dat_articulo`
5. Il sistema calcola i totali per il DDT basandosi su queste informazioni
6. I totali calcolati vengono salvati nel record in `ddt_head`

### Passo 4: Visualizzazione/Stampa del DDT
1. Il sistema recupera tutte le informazioni necessarie dal database
2. Il sistema genera un documento DDT con intestazione (cliente), dettagli (prodotti) e totali

## Diagramma delle Relazioni

```
┌─────────────┐     ┌──────────┐
│ dat_cliente │◄────┤ ddt_head │
└─────────────┘     └────┬─────┘
                         │
                         │
                         ▼
                    ┌─────────┐
                    │ ddt_line│
                    └────┬────┘
                         │
                         │
                         ▼
┌─────────────┐     ┌────────────────────┐
│ dat_articulo│◄────┤ dat_ticket_linea   │◄─────┐
└─────────────┘     └────────────────────┘      │
                                                │
                                                │
                                          ┌─────┴──────────────┐
                                          │ dat_ticket_cabecera│
                                          └────────────────────┘
```

## Conclusione

Il modello DDT nel sistema DB-LogiX si basa su un'integrazione complessa tra diverse tabelle:

1. `dat_cliente` fornisce le informazioni sul destinatario del DDT
2. `dat_ticket_cabecera` fornisce i ticket che vengono inclusi nel DDT
3. `dat_ticket_linea` fornisce i dettagli delle linee di ciascun ticket
4. `dat_articulo` fornisce le informazioni sui prodotti inclusi nei ticket

Questa architettura permette di:
- Associare facilmente i ticket esistenti ai DDT
- Calcolare automaticamente i totali basati sui prodotti inclusi
- Mantenere una traccia completa della documentazione di trasporto

Il sistema è progettato per supportare il flusso di lavoro tipico della gestione dei documenti di trasporto in un contesto aziendale italiano, rispettando i requisiti fiscali e operativi. 