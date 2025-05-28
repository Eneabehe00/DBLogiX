-- Query MySQL per creare le tabelle chat del sistema DBLogiX
-- Eseguire nell'ordine specificato per rispettare le foreign key

-- 1. Creazione tabella chat_rooms
CREATE TABLE chat_rooms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_global BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_by INT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_chat_rooms_created_by (created_by),
    INDEX idx_chat_rooms_global (is_global)
);

-- 2. Creazione tabella chat_messages
CREATE TABLE chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    room_id INT DEFAULT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE,
    INDEX idx_chat_messages_user (user_id),
    INDEX idx_chat_messages_timestamp (timestamp),
    INDEX idx_chat_messages_room (room_id),
    INDEX idx_chat_messages_read (is_read)
);

-- 3. Inserimento chat room globale di default
INSERT INTO chat_rooms (name, description, is_global, created_by) 
VALUES ('Chat Globale', 'Chat room principale per tutti gli utenti del sistema', TRUE, 1);

-- 4. Commenti per riferimento futuro
/*
Struttura delle tabelle:

chat_rooms:
- id: Chiave primaria auto-incrementale
- name: Nome della chat room (max 100 caratteri)
- description: Descrizione opzionale della room
- is_global: Flag per identificare chat globali vs private
- created_at: Timestamp di creazione automatico
- created_by: ID dell'utente che ha creato la room (nullable)

chat_messages:
- id: Chiave primaria auto-incrementale
- user_id: ID dell'utente che ha inviato il messaggio (NOT NULL)
- message: Contenuto del messaggio (TEXT per messaggi lunghi)
- timestamp: Timestamp di invio automatico
- is_read: Flag per messaggi letti/non letti
- room_id: ID della chat room (nullable per compatibilità)

Indici creati per ottimizzare le query più frequenti:
- Ricerca messaggi per utente
- Ordinamento per timestamp
- Filtro per room
- Filtro per messaggi non letti
*/ 