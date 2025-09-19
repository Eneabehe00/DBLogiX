-- Migrazione MySQL: Creazione tabelle Fatture per tracciamento fatture elettroniche
-- Data: 2025-07-22
-- Descrizione: Tabelle per salvare informazioni fatture generate (oltre ai file XML)

-- Tabella principale Fatture
CREATE TABLE IF NOT EXISTS Fatture (
    IdFattura INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Informazioni base fattura
    NumeroFattura VARCHAR(50) NOT NULL,
    DataFattura DATE NOT NULL,
    TipoDocumento VARCHAR(10) DEFAULT 'TD01', -- TD01=fattura normale, TD24=fattura differita
    StatoFattura VARCHAR(20) DEFAULT 'generata', -- generata, inviata, pagata, annullata
    
    -- Collegamento al DDT (opzionale)
    IdDDT INT NULL, -- Se generata da DDT
    NumeroDDT VARCHAR(50) NULL,
    DataDDT DATE NULL,
    
    -- Dati cliente
    IdCliente INT NOT NULL,
    NomeCliente VARCHAR(255) NOT NULL,
    CodiceFiscaleCliente VARCHAR(50) NULL,
    PartitaIVACliente VARCHAR(50) NULL,
    IndirizzoCliente TEXT NULL,
    
    -- Dati azienda emittente
    IdEmpresa INT NOT NULL DEFAULT 1,
    NomeEmpresa VARCHAR(255) NOT NULL,
    PartitaIVAEmpresa VARCHAR(50) NOT NULL,
    
    -- Informazioni economiche
    ImportoImponibile DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ImportoIVA DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    ImportoTotale DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    Divisa VARCHAR(3) DEFAULT 'EUR',
    
    -- Dettagli pagamento
    ModalitaPagamento VARCHAR(10) DEFAULT 'MP05', -- MP05=bonifico
    DataScadenza DATE NULL,
    StatoPagamento VARCHAR(20) DEFAULT 'non_pagata', -- non_pagata, pagata, parzialmente_pagata
    
    -- File e trasmissione
    NomeFileXML VARCHAR(255) NOT NULL, -- Nome del file XML generato
    PercorsoFileXML TEXT NULL, -- Percorso completo del file
    ProgressivoInvio VARCHAR(20) NULL, -- ID trasmissione SDI
    CodiceDestinatario VARCHAR(10) DEFAULT '0000000',
    
    -- Informazioni tecniche
    Causale TEXT NULL,
    Note TEXT NULL,
    
    -- Audit e tracciamento
    CreatoIl DATETIME DEFAULT CURRENT_TIMESTAMP,
    CreatoDA VARCHAR(100) NULL,
    ModificatoIl DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ModificatoDA VARCHAR(100) NULL,
    
    -- Indici
    INDEX idx_fatture_numero (NumeroFattura),
    INDEX idx_fatture_data (DataFattura),
    INDEX idx_fatture_cliente (IdCliente),
    INDEX idx_fatture_ddt (IdDDT),
    INDEX idx_fatture_stato (StatoFattura),
    INDEX idx_fatture_tipo (TipoDocumento)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabella per le linee delle fatture
CREATE TABLE IF NOT EXISTS FattureLinee (
    IdLineaFattura INT AUTO_INCREMENT PRIMARY KEY,
    IdFattura INT NOT NULL,
    NumeroLinea INT NOT NULL,
    
    -- Dati prodotto
    IdArticolo INT NULL,
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
    Note TEXT NULL,
    
    -- Audit
    CreatoIl DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Indici
    INDEX idx_fatture_linee_fattura (IdFattura),
    INDEX idx_fatture_linee_articolo (IdArticolo),
    
    -- Foreign keys
    FOREIGN KEY (IdFattura) REFERENCES Fatture(IdFattura) ON DELETE CASCADE,
    FOREIGN KEY (IdArticolo) REFERENCES dat_articulo(IdArticolo) ON DELETE SET NULL
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci; 