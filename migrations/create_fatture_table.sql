-- Migrazione: Creazione tabella Fatture per tracciamento fatture elettroniche
-- Data: 2025-07-22
-- Descrizione: Tabella per salvare informazioni fatture generate (oltre ai file XML)

CREATE TABLE IF NOT EXISTS Fatture (
    IdFattura INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Informazioni base fattura
    NumeroFattura VARCHAR(50) NOT NULL,
    DataFattura DATE NOT NULL,
    TipoDocumento VARCHAR(10) DEFAULT 'TD01', -- TD01=fattura normale, TD24=fattura differita
    StatoFattura VARCHAR(20) DEFAULT 'generata', -- generata, inviata, pagata, annullata
    
    -- Collegamento al DDT (opzionale)
    IdDDT INTEGER NULL, -- Se generata da DDT
    NumeroDDT VARCHAR(50) NULL,
    DataDDT DATE NULL,
    
    -- Dati cliente
    IdCliente INTEGER NOT NULL,
    NomeCliente VARCHAR(255) NOT NULL,
    CodiceFiscaleCliente VARCHAR(50),
    PartitaIVACliente VARCHAR(50),
    IndirizzoCliente TEXT,
    
    -- Dati azienda emittente
    IdEmpresa INTEGER NOT NULL DEFAULT 1,
    NomeEmpresa VARCHAR(255) NOT NULL,
    PartitaIVAEmpresa VARCHAR(50) NOT NULL,
    
    -- Informazioni economiche
    ImportoImponibile DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ImportoIVA DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ImportoTotale DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Divisa VARCHAR(3) DEFAULT 'EUR',
    
    -- Dettagli pagamento
    ModalitaPagamento VARCHAR(10) DEFAULT 'MP05', -- MP05=bonifico
    DataScadenza DATE,
    StatoPagamento VARCHAR(20) DEFAULT 'non_pagata', -- non_pagata, pagata, parzialmente_pagata
    
    -- File e trasmissione
    NomeFileXML VARCHAR(255) NOT NULL, -- Nome del file XML generato
    PercorsoFileXML TEXT, -- Percorso completo del file
    ProgressivoInvio VARCHAR(20), -- ID trasmissione SDI
    CodiceDestinatario VARCHAR(10) DEFAULT '0000000',
    
    -- Informazioni tecniche
    Causale TEXT,
    Note TEXT,
    
    -- Audit e tracciamento
    CreatoIl DATETIME DEFAULT CURRENT_TIMESTAMP,
    CreatoDA VARCHAR(100),
    ModificatoIl DATETIME DEFAULT CURRENT_TIMESTAMP,
    ModificatoDA VARCHAR(100),
    
    -- Constraints
    FOREIGN KEY (IdCliente) REFERENCES Clientes(IdCliente),
    FOREIGN KEY (IdEmpresa) REFERENCES Company(IdEmpresa),
    FOREIGN KEY (IdDDT) REFERENCES dat_albaran_cabecera(IdAlbaran)
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_fatture_numero ON Fatture(NumeroFattura);
CREATE INDEX IF NOT EXISTS idx_fatture_data ON Fatture(DataFattura);
CREATE INDEX IF NOT EXISTS idx_fatture_cliente ON Fatture(IdCliente);
CREATE INDEX IF NOT EXISTS idx_fatture_ddt ON Fatture(IdDDT);
CREATE INDEX IF NOT EXISTS idx_fatture_stato ON Fatture(StatoFattura);
CREATE INDEX IF NOT EXISTS idx_fatture_tipo ON Fatture(TipoDocumento);

-- Tabella per le linee delle fatture
CREATE TABLE IF NOT EXISTS FattureLinee (
    IdLineaFattura INTEGER PRIMARY KEY AUTOINCREMENT,
    IdFattura INTEGER NOT NULL,
    NumeroLinea INTEGER NOT NULL,
    
    -- Dati prodotto
    IdArticolo INTEGER,
    Descrizione TEXT NOT NULL,
    Quantita DECIMAL(10,3) NOT NULL DEFAULT 0,
    UnitaMisura VARCHAR(10) DEFAULT 'PZ',
    
    -- Prezzi e importi
    PrezzoUnitario DECIMAL(10,8) NOT NULL DEFAULT 0,
    PrezzoTotale DECIMAL(10,2) NOT NULL DEFAULT 0,
    AliquotaIVA DECIMAL(5,2) NOT NULL DEFAULT 0,
    ImportoIVA DECIMAL(10,2) NOT NULL DEFAULT 0,
    
    -- Altri dati
    Sconto DECIMAL(5,2) DEFAULT 0,
    Note TEXT,
    
    -- Audit
    CreatoIl DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (IdFattura) REFERENCES Fatture(IdFattura) ON DELETE CASCADE,
    FOREIGN KEY (IdArticolo) REFERENCES Product(IdArticulo)
);

-- Indice per performance linee
CREATE INDEX IF NOT EXISTS idx_fatture_linee_fattura ON FattureLinee(IdFattura);
CREATE INDEX IF NOT EXISTS idx_fatture_linee_articolo ON FattureLinee(IdArticolo);

-- Trigger per aggiornare ModificatoIl
CREATE TRIGGER IF NOT EXISTS trigger_fatture_updated
    AFTER UPDATE ON Fatture
BEGIN
    UPDATE Fatture SET ModificatoIl = CURRENT_TIMESTAMP WHERE IdFattura = NEW.IdFattura;
END;

PRAGMA foreign_keys = ON; 