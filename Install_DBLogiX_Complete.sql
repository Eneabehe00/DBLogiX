-- ========================================
-- DBLOGIX - INSTALLAZIONE COMPLETA DATABASE
-- Script di installazione per tutte le tabelle del sistema
-- ========================================

SELECT 'INIZIO INSTALLAZIONE DBLOGIX' AS Status;
SELECT NOW() AS 'Timestamp Inizio';

-- ========================================
-- FASE 1: RIMOZIONE TABELLE ESISTENTI
-- ========================================

SELECT 'FASE 1: Rimozione tabelle esistenti...' AS Status;

-- Rimozione tabelle Task Management (ordine importante per foreign key)
DROP TABLE IF EXISTS task_notifications;
SELECT 'Rimossa tabella task_notifications' AS Status;

DROP TABLE IF EXISTS task_ticket_scans;
SELECT 'Rimossa tabella task_ticket_scans' AS Status;

DROP TABLE IF EXISTS task_tickets;
SELECT 'Rimossa tabella task_tickets' AS Status;

DROP TABLE IF EXISTS tasks;
SELECT 'Rimossa tabella tasks' AS Status;

-- Rimozione tabelle Chat
DROP TABLE IF EXISTS chat_message;
SELECT 'Rimossa tabella chat_message' AS Status;

DROP TABLE IF EXISTS chat_room;
SELECT 'Rimossa tabella chat_room' AS Status;

-- Rimozione tabelle Sistema
DROP TABLE IF EXISTS system_config;
SELECT 'Rimossa tabella system_config' AS Status;

DROP TABLE IF EXISTS scan_log;
SELECT 'Rimossa tabella scan_log' AS Status;

DROP TABLE IF EXISTS users;
SELECT 'Rimossa tabella users' AS Status;

SELECT 'FASE 1 COMPLETATA: Tutte le tabelle rimosse' AS Status;

-- ========================================
-- FASE 2: CREAZIONE TABELLE BASE
-- ========================================

SELECT 'FASE 2: Creazione tabelle base...' AS Status;

-- 1. TABELLA USERS
SELECT 'Creazione tabella users...' AS Status;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(128),
  is_admin BOOLEAN DEFAULT FALSE,
  screen_task BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella users creata con successo' AS Status;

-- 2. TABELLA SCAN_LOG
SELECT 'Creazione tabella scan_log...' AS Status;

CREATE TABLE scan_log (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  ticket_id INT,
  action VARCHAR(20),
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  raw_code VARCHAR(50),
  product_code INT,
  scan_date VARCHAR(20),
  scan_time VARCHAR(20),
  FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella scan_log creata con successo' AS Status;

-- 3. TABELLA SYSTEM_CONFIG
SELECT 'Creazione tabella system_config...' AS Status;

CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(50) UNIQUE NOT NULL,
    config_value VARCHAR(255),
    description VARCHAR(255),
    data_type VARCHAR(20) DEFAULT 'string',
    created_at TIMESTAMP DEFAULT 0, -- verrà impostato manualmente in INSERT
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

SELECT 'Tabella system_config creata con successo' AS Status;

-- ========================================
-- FASE 3: CREAZIONE TABELLE CHAT
-- ========================================

SELECT 'FASE 3: Creazione tabelle chat...' AS Status;

-- 1. TABELLA CHAT_ROOM
SELECT 'Creazione tabella chat_room...' AS Status;

CREATE TABLE chat_room (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_global BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_chat_room_created_by (created_by),
    INDEX idx_chat_room_global (is_global)
);

SELECT 'Tabella chat_room creata con successo' AS Status;

-- 2. TABELLA CHAT_MESSAGE
SELECT 'Creazione tabella chat_message...' AS Status;

CREATE TABLE chat_message (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    room_id INT DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES chat_room(id) ON DELETE CASCADE,
    INDEX idx_chat_message_user (user_id),
    INDEX idx_chat_message_timestamp (timestamp),
    INDEX idx_chat_message_room (room_id),
    INDEX idx_chat_message_read (is_read)
);

SELECT 'Tabella chat_message creata con successo' AS Status;

-- 3. INSERIMENTO CHAT ROOM GLOBALE
SELECT 'Inserimento chat room globale di default...' AS Status;

INSERT INTO chat_room (name, description, is_global, created_by) 
VALUES ('Chat Globale', 'Chat room principale per tutti gli utenti del sistema', TRUE, NULL);

SELECT 'Chat room globale inserita con successo' AS Status;

-- ========================================
-- FASE 4: CREAZIONE TABELLE TASK MANAGEMENT
-- ========================================

SELECT 'FASE 4: Creazione tabelle task management...' AS Status;

-- 1. TABELLA TASKS
SELECT 'Creazione tabella tasks...' AS Status;

CREATE TABLE tasks (
    id_task INT AUTO_INCREMENT PRIMARY KEY,
    task_number VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_by INT NOT NULL,
    assigned_to INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    deadline TIMESTAMP NULL,
    priority VARCHAR(10) DEFAULT 'medium',
    total_tickets INT DEFAULT 0,
    completed_tickets INT DEFAULT 0,
    client_id INT,
    ddt_generated BOOLEAN DEFAULT FALSE,
    ddt_id BIGINT,
    
    INDEX idx_task_number (task_number),
    INDEX idx_task_status (status),
    INDEX idx_task_created_by (created_by),
    INDEX idx_task_assigned_to (assigned_to),
    INDEX idx_task_client (client_id),
    INDEX idx_task_priority (priority),
    INDEX idx_task_deadline (deadline)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella tasks creata con successo' AS Status;

-- 2. TABELLA TASK_TICKETS
SELECT 'Creazione tabella task_tickets...' AS Status;

CREATE TABLE task_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    ticket_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    verified_by INT,
    notes TEXT,
    total_items INT DEFAULT 0,
    scanned_items INT DEFAULT 0,
    
    UNIQUE KEY unique_task_ticket (task_id, ticket_id),
    INDEX idx_task_tickets_task (task_id),
    INDEX idx_task_tickets_ticket (ticket_id),
    INDEX idx_task_tickets_status (status),
    INDEX idx_task_tickets_verified_by (verified_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella task_tickets creata con successo' AS Status;

-- 3. TABELLA TASK_TICKET_SCANS
SELECT 'Creazione tabella task_ticket_scans...' AS Status;

CREATE TABLE task_ticket_scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_ticket_id INT NOT NULL,
    ticket_line_id INT,
    product_id INT,
    scanned_by INT NOT NULL,
    scanned_code VARCHAR(100),
    expected_code VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    weight_expected DECIMAL(15,3),
    weight_scanned DECIMAL(15,3),
    expiry_date_expected TIMESTAMP NULL,
    expiry_date_scanned TIMESTAMP NULL,
    
    INDEX idx_task_scans_task_ticket (task_ticket_id),
    INDEX idx_task_scans_ticket_line (ticket_line_id),
    INDEX idx_task_scans_product (product_id),
    INDEX idx_task_scans_scanned_by (scanned_by),
    INDEX idx_task_scans_status (status),
    INDEX idx_task_scans_date (scanned_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella task_ticket_scans creata con successo' AS Status;

-- 4. TABELLA TASK_NOTIFICATIONS
SELECT 'Creazione tabella task_notifications...' AS Status;

CREATE TABLE task_notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    user_id INT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    
    INDEX idx_task_notifications_task (task_id),
    INDEX idx_task_notifications_user (user_id),
    INDEX idx_task_notifications_type (notification_type),
    INDEX idx_task_notifications_read (is_read),
    INDEX idx_task_notifications_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

SELECT 'Tabella task_notifications creata con successo' AS Status;

-- ========================================
-- FASE 5: AGGIUNTA FOREIGN KEY CONSTRAINTS
-- ========================================

SELECT 'FASE 5: Aggiunta foreign key constraints...' AS Status;

-- Foreign key per tabella TASKS
SELECT 'Aggiunta foreign key per tasks...' AS Status;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_created_by FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE tasks ADD CONSTRAINT fk_tasks_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL;

-- Foreign key per tabella TASK_TICKETS
SELECT 'Aggiunta foreign key per task_tickets...' AS Status;
ALTER TABLE task_tickets ADD CONSTRAINT fk_task_tickets_task_id FOREIGN KEY (task_id) REFERENCES tasks(id_task) ON DELETE CASCADE;
ALTER TABLE task_tickets ADD CONSTRAINT fk_task_tickets_verified_by FOREIGN KEY (verified_by) REFERENCES users(id) ON DELETE SET NULL;

-- Foreign key per tabella TASK_TICKET_SCANS
SELECT 'Aggiunta foreign key per task_ticket_scans...' AS Status;
ALTER TABLE task_ticket_scans ADD CONSTRAINT fk_task_scans_task_ticket_id FOREIGN KEY (task_ticket_id) REFERENCES task_tickets(id) ON DELETE CASCADE;
ALTER TABLE task_ticket_scans ADD CONSTRAINT fk_task_scans_scanned_by FOREIGN KEY (scanned_by) REFERENCES users(id) ON DELETE CASCADE;

-- Foreign key per tabella TASK_NOTIFICATIONS
SELECT 'Aggiunta foreign key per task_notifications...' AS Status;
ALTER TABLE task_notifications ADD CONSTRAINT fk_task_notifications_task_id FOREIGN KEY (task_id) REFERENCES tasks(id_task) ON DELETE CASCADE;
ALTER TABLE task_notifications ADD CONSTRAINT fk_task_notifications_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

SELECT 'FASE 5 COMPLETATA: Tutte le foreign key aggiunte' AS Status;

-- ========================================
-- FASE 6: MODIFICA TABELLE ESISTENTI
-- ========================================

SELECT 'FASE 6: Modifica tabelle esistenti...' AS Status;

-- Aggiunta campo IdTicket alla tabella dat_albaran_linea (se esiste e se la colonna non c'è già)
SELECT 'Verifica esistenza tabella dat_albaran_linea...' AS Status;

-- Controlla se la tabella esiste
SET @table_exists = (SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'dat_albaran_linea');

-- Controlla se la colonna IdTicket esiste già
SET @column_exists = (SELECT COUNT(*) FROM information_schema.columns 
                     WHERE table_schema = DATABASE() 
                     AND table_name = 'dat_albaran_linea' 
                     AND column_name = 'IdTicket');

-- Esegui solo se la tabella esiste E la colonna non esiste
SET @sql = IF(@table_exists > 0 AND @column_exists = 0,
              'ALTER TABLE dat_albaran_linea ADD COLUMN IdTicket BIGINT(20) NULL',
              'SELECT "Campo IdTicket non aggiunto: tabella inesistente o colonna già presente" AS Info');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Messaggi di debug
SELECT CASE 
    WHEN @table_exists = 0 THEN 'Tabella dat_albaran_linea non trovata'
    WHEN @column_exists > 0 THEN 'Campo IdTicket già presente in dat_albaran_linea'
    ELSE 'Campo IdTicket aggiunto con successo a dat_albaran_linea'
END AS 'Risultato modifica tabella';

SELECT 'FASE 6 COMPLETATA: Modifiche tabelle esistenti' AS Status;

-- ========================================
-- FASE 7: VERIFICA INSTALLAZIONE
-- ========================================

SELECT 'FASE 7: Verifica installazione...' AS Status;

-- Verifica tabelle create
SELECT 'Verifica tabelle create:' AS Status;
SHOW TABLES LIKE '%users%';
SHOW TABLES LIKE '%scan_log%';
SHOW TABLES LIKE '%system_config%';
SHOW TABLES LIKE '%chat%';
SHOW TABLES LIKE '%task%';

-- Conteggio tabelle
SELECT COUNT(*) AS 'Tabelle DBLogiX create' FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME IN ('users', 'scan_log', 'system_config', 'chat_room', 'chat_message', 'tasks', 'task_tickets', 'task_ticket_scans', 'task_notifications');

-- ========================================
-- INSTALLAZIONE COMPLETATA
-- ========================================

SELECT 'INSTALLAZIONE COMPLETATA CON SUCCESSO!' AS Status;
SELECT NOW() AS 'Timestamp Fine';
SELECT 'Controllare i messaggi sopra per eventuali errori' AS Nota;
SELECT 'Premere un tasto per chiudere...' AS Azione; 