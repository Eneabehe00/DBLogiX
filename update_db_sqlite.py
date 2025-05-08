"""
Script per aggiornare la struttura del database SQLite
Aggiunge le colonne necessarie alla tabella scan_log
"""
import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_sqlite_database():
    """Aggiunge colonne mancanti alla tabella scan_log su SQLite"""
    try:
        # Percorso del database SQLite
        db_path = os.path.join(os.getcwd(), 'instance', 'dblogix.db')
        logger.info(f"Utilizzo database: {db_path}")
        
        if not os.path.exists(db_path):
            logger.error(f"Database non trovato: {db_path}")
            return False
            
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica colonne esistenti
        cursor.execute("PRAGMA table_info(scan_log)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        logger.info(f"Colonne esistenti: {column_names}")
        
        # Colonne da aggiungere
        new_columns = {
            'raw_code': 'TEXT',
            'product_code': 'INTEGER',
            'scan_date': 'TEXT',
            'scan_time': 'TEXT'
        }
        
        # Aggiungi colonne mancanti
        for col_name, col_type in new_columns.items():
            if col_name not in column_names:
                logger.info(f"Aggiunta colonna {col_name} ({col_type})")
                cursor.execute(f"ALTER TABLE scan_log ADD COLUMN {col_name} {col_type}")
            else:
                logger.info(f"Colonna {col_name} già esistente")
                
        # Commit e chiusura
        conn.commit()
        conn.close()
        
        logger.info("Aggiornamento database completato con successo!")
        return True
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento del database: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Avvio aggiornamento database SQLite...")
    success = update_sqlite_database()
    if not success:
        logger.error("Aggiornamento database fallito. Controlla i log per maggiori dettagli.") 