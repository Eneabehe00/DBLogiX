-- ===========================================
-- DBLogiX - Nuovo Sistema Gestione Ingredienti
-- Design Semplificato con Relazioni N-N
-- Compatible with MySQL 5.x+
-- ===========================================

-- Utilizzare il database DBLogiX
USE DBLogiX;

-- ===========================================
-- 1. ELIMINAZIONE TABELLE PRECEDENTI
-- ===========================================

-- Elimina le viste se esistono
DROP VIEW IF EXISTS `view_food_cost_articolo`;
DROP VIEW IF EXISTS `view_fornitore_ingredienti`;

-- Elimina le tabelle di associazione prima
DROP TABLE IF EXISTS `dat_articolo_ingrediente`;
DROP TABLE IF EXISTS `dat_fornitore_ingrediente`;

-- Elimina le tabelle principali
DROP TABLE IF EXISTS `dat_ingrediente`;
DROP TABLE IF EXISTS `dat_fornitore`;

-- ===========================================
-- 2. NUOVA TABELLA INGREDIENTI
-- ===========================================
CREATE TABLE `ingredienti` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `nome` VARCHAR(100) NOT NULL,
    `descrizione` TEXT NULL,
    `unita_misura` VARCHAR(10) NOT NULL DEFAULT 'kg',
    `categoria` VARCHAR(50) NULL,

    -- Informazioni nutrizionali per 100g
    `calorie` DECIMAL(6,1) NULL COMMENT 'Calorie per 100g',
    `proteine` DECIMAL(5,2) NULL COMMENT 'Proteine in grammi per 100g',
    `carboidrati` DECIMAL(5,2) NULL COMMENT 'Carboidrati in grammi per 100g',
    `grassi` DECIMAL(5,2) NULL COMMENT 'Grassi in grammi per 100g',

    -- Informazioni aggiuntive
    `allergeni` TEXT NULL COMMENT 'Lista allergeni separati da virgola',
    `conservazione` TEXT NULL COMMENT 'Modalità di conservazione',

    -- Campi sistema (una sola colonna TIMESTAMP auto-gestita)
    `attivo` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NULL DEFAULT NULL,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_ingredienti_nome` (`nome`),
    INDEX `idx_ingredienti_nome` (`nome`),
    INDEX `idx_ingredienti_categoria` (`categoria`),
    INDEX `idx_ingredienti_attivo` (`attivo`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8
  COLLATE=utf8_unicode_ci
  COMMENT='Catalogo ingredienti - versione semplificata';


-- ===========================================
-- 3. NUOVA TABELLA FORNITORI
-- ===========================================
CREATE TABLE `fornitori` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `nome` VARCHAR(100) NOT NULL,
    `email` VARCHAR(100) NULL,
    `telefono` VARCHAR(20) NULL,
    `indirizzo` VARCHAR(200) NULL,
    `citta` VARCHAR(100) NULL,
    `provincia` VARCHAR(50) NULL,
    `cap` VARCHAR(10) NULL,
    `paese` VARCHAR(50) DEFAULT 'Italia',
    `partita_iva` VARCHAR(16) NULL,
    `codice_fiscale` VARCHAR(16) NULL,
    `iban` VARCHAR(34) NULL,
    `note` TEXT NULL,

    -- Campi sistema (una sola TIMESTAMP auto-gestita nativamente)
    `attivo` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NULL DEFAULT NULL,

    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_fornitori_nome` (`nome`),
    INDEX `idx_fornitori_nome` (`nome`),
    INDEX `idx_fornitori_email` (`email`),
    INDEX `idx_fornitori_attivo` (`attivo`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8
  COLLATE=utf8_unicode_ci
  COMMENT='Anagrafica fornitori - versione semplificata';

-- ===========================================
-- 4. TABELLA ASSOCIAZIONE INGREDIENTI-FORNITORI (N-N)
-- ===========================================
CREATE TABLE `ingredienti_fornitori` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `ingrediente_id` INT(11) NOT NULL,
    `fornitore_id` INT(11) NOT NULL,
    `prezzo_unitario` DECIMAL(10,3) NOT NULL COMMENT 'Prezzo per unità di misura',
    `codice_fornitore` VARCHAR(50) NULL COMMENT 'Codice prodotto del fornitore',
    `tempo_consegna_giorni` INT(3) NULL DEFAULT 0 COMMENT 'Giorni di consegna standard',
    `quantita_minima` DECIMAL(10,3) NULL DEFAULT 0.000 COMMENT 'Quantità minima ordinabile',
    `note` TEXT NULL,
    
    -- Campi sistema
    `attivo` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NULL DEFAULT NULL,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_ingredienti_fornitori` (`ingrediente_id`, `fornitore_id`),
    
    CONSTRAINT `fk_if_ingrediente` 
        FOREIGN KEY (`ingrediente_id`) REFERENCES `ingredienti`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    CONSTRAINT `fk_if_fornitore` 
        FOREIGN KEY (`fornitore_id`) REFERENCES `fornitori`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
        
    INDEX `idx_if_ingrediente` (`ingrediente_id`),
    INDEX `idx_if_fornitore` (`fornitore_id`),
    INDEX `idx_if_attivo` (`attivo`)
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci 
COMMENT='Associazioni ingredienti-fornitori con prezzi';

-- ===========================================
-- 5. TABELLA ASSOCIAZIONE INGREDIENTI-ARTICOLI (N-N)
-- ===========================================
CREATE TABLE `articoli_ingredienti` (
    `id` INT(11) NOT NULL AUTO_INCREMENT,
    `articolo_id` INT(11) NOT NULL COMMENT 'Riferimento a dat_articulo.IdArticulo',
    `ingrediente_id` INT(11) NOT NULL,
    `fornitore_preferito_id` INT(11) NULL COMMENT 'Fornitore preferito per questo ingrediente',
    `quantita` DECIMAL(10,3) NOT NULL DEFAULT 0.000 COMMENT 'Quantità di ingrediente necessaria',
    `note` TEXT NULL,
    
    -- Campi sistema
    `attivo` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP NULL DEFAULT NULL,
    
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_articoli_ingredienti` (`articolo_id`, `ingrediente_id`),
    
    CONSTRAINT `fk_ai_ingrediente` 
        FOREIGN KEY (`ingrediente_id`) REFERENCES `ingredienti`(`id`) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    CONSTRAINT `fk_ai_fornitore` 
        FOREIGN KEY (`fornitore_preferito_id`) REFERENCES `fornitori`(`id`) 
        ON DELETE SET NULL ON UPDATE CASCADE,
        
    -- Non creiamo foreign key per articolo_id perché punta a dat_articulo che potrebbe avere struttura diversa
    INDEX `idx_ai_articolo` (`articolo_id`),
    INDEX `idx_ai_ingrediente` (`ingrediente_id`),
    INDEX `idx_ai_fornitore` (`fornitore_preferito_id`),
    INDEX `idx_ai_attivo` (`attivo`)
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci 
COMMENT='Associazione articoli-ingredienti per calcolo food cost';

-- ===========================================
-- 6. VISTA FOOD COST ARTICOLI
-- ===========================================
CREATE OR REPLACE VIEW `view_food_cost` AS
SELECT 
    a.IdArticulo as articolo_id,
    a.Descripcion as nome_articolo,
    a.PrecioConIVA as prezzo_vendita,
    COALESCE(SUM(
        ai.quantita * COALESCE(if_prezzi.prezzo_unitario, 0)
    ), 0) as costo_ingredienti,
    CASE 
        WHEN a.PrecioConIVA > 0 AND COALESCE(SUM(ai.quantita * COALESCE(if_prezzi.prezzo_unitario, 0)), 0) > 0
        THEN (COALESCE(SUM(ai.quantita * COALESCE(if_prezzi.prezzo_unitario, 0)), 0) / a.PrecioConIVA) * 100
        ELSE 0
    END as percentuale_food_cost,
    COUNT(ai.ingrediente_id) as numero_ingredienti,
    a.EnVenta as attivo,
    MAX(ai.updated_at) as ultimo_aggiornamento
FROM dat_articulo a
LEFT JOIN articoli_ingredienti ai ON a.IdArticulo = ai.articolo_id AND ai.attivo = 1
LEFT JOIN ingredienti i ON ai.ingrediente_id = i.id AND i.attivo = 1
LEFT JOIN ingredienti_fornitori if_prezzi ON (
    ai.ingrediente_id = if_prezzi.ingrediente_id 
    AND (ai.fornitore_preferito_id = if_prezzi.fornitore_id OR ai.fornitore_preferito_id IS NULL)
    AND if_prezzi.attivo = 1
)
WHERE a.EnVenta = 1
GROUP BY a.IdArticulo, a.Descripcion, a.PrecioConIVA, a.EnVenta;

-- ===========================================
-- 7. VISTA RIEPILOGO FORNITORI-INGREDIENTI
-- ===========================================
CREATE OR REPLACE VIEW `view_fornitori_ingredienti` AS
SELECT 
    f.id as fornitore_id,
    f.nome as nome_fornitore,
    f.telefono,
    f.email,
    i.id as ingrediente_id,
    i.nome as nome_ingrediente,
    i.unita_misura,
    if_rel.prezzo_unitario,
    if_rel.quantita_minima,
    if_rel.tempo_consegna_giorni,
    if_rel.attivo
FROM fornitori f
INNER JOIN ingredienti_fornitori if_rel ON f.id = if_rel.fornitore_id
INNER JOIN ingredienti i ON if_rel.ingrediente_id = i.id
WHERE f.attivo = 1 AND i.attivo = 1;

-- ===========================================
-- 8. DATI DI ESEMPIO (OPZIONALE)
-- ===========================================

-- Inserimento fornitori di esempio
INSERT INTO `fornitori` (`nome`, `email`, `telefono`, `citta`, `provincia`, `paese`) VALUES
('Metro Cash & Carry', 'ordini@metro.it', '800-123456', 'Milano', 'MI', 'Italia'),
('Despar Forniture', 'vendite@despar.it', '041-234567', 'Venezia', 'VE', 'Italia'),
('Conad Professional', 'info@conadpro.it', '06-345678', 'Roma', 'RM', 'Italia');

-- Inserimento ingredienti di esempio
INSERT INTO `ingredienti` (`nome`, `descrizione`, `unita_misura`, `categoria`, `calorie`, `proteine`, `carboidrati`, `grassi`) VALUES
('Farina 00', 'Farina di grano tenero tipo 00', 'kg', 'Cereali', 364.0, 11.0, 74.0, 0.7),
('Pomodori pelati', 'Pomodori pelati italiani in scatola', 'kg', 'Verdure', 18.0, 0.9, 3.5, 0.2),
('Mozzarella di bufala', 'Mozzarella di bufala DOP', 'kg', 'Latticini', 280.0, 16.7, 4.9, 19.5),
('Olio extravergine oliva', 'Olio EVO italiano', 'l', 'Condimenti', 884.0, 0.0, 0.0, 100.0),
('Basilico fresco', 'Basilico fresco biologico', 'kg', 'Erbe aromatiche', 251.0, 3.2, 2.6, 0.6);

-- Associazioni ingredienti-fornitori con prezzi
INSERT INTO `ingredienti_fornitori` (`ingrediente_id`, `fornitore_id`, `prezzo_unitario`, `tempo_consegna_giorni`, `quantita_minima`) VALUES
-- Farina 00
(1, 1, 1.250, 2, 25.000), -- Metro
(1, 2, 1.180, 3, 20.000), -- Despar
(1, 3, 1.300, 1, 10.000), -- Conad

-- Pomodori pelati
(2, 1, 2.850, 2, 12.000), -- Metro
(2, 3, 2.950, 1, 6.000),  -- Conad

-- Mozzarella di bufala
(3, 1, 18.500, 1, 2.000), -- Metro
(3, 2, 17.800, 2, 3.000), -- Despar

-- Olio EVO
(4, 1, 8.750, 3, 5.000),  -- Metro
(4, 2, 8.200, 2, 3.000),  -- Despar
(4, 3, 9.100, 1, 2.000),  -- Conad

-- Basilico fresco
(5, 2, 12.500, 1, 0.500), -- Despar
(5, 3, 13.200, 1, 0.250); -- Conad

-- ===========================================
-- OPERAZIONI COMPLETATE
-- ===========================================

SELECT 'Nuovo sistema ingredienti creato con successo!' as Messaggio;
SELECT COUNT(*) as Fornitori FROM fornitori;
SELECT COUNT(*) as Ingredienti FROM ingredienti;
SELECT COUNT(*) as Associazioni FROM ingredienti_fornitori;


ALTER TABLE `ingredienti`
ADD COLUMN `fornitore_preferito_id` INT(11) NULL AFTER `conservazione`,
ADD INDEX `idx_ingredienti_fornitore_preferito` (`fornitore_preferito_id`),
ADD CONSTRAINT `fk_ingredienti_fornitore_preferito`
    FOREIGN KEY (`fornitore_preferito_id`) REFERavaENCES `fornitori`(`id`)
    ON DELETE SET NULL ON UPDATE CASCADE;