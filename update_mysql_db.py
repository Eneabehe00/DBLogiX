"""
Script per aggiornare la struttura del database MySQL
Aggiunge le colonne necessarie alla tabella scan_log
"""
import os
import pymysql
import logging
from config import REMOTE_DB_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_mysql_database():
    """Aggiunge colonne mancanti alla tabella scan_log in MySQL"""
    try:
        # Connessione al database MySQL
        logger.info(f"Connessione al database MySQL: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}")
        
        conn = pymysql.connect(
            host=REMOTE_DB_CONFIG['host'],
            user=REMOTE_DB_CONFIG['user'],
            password=REMOTE_DB_CONFIG['password'],
            database=REMOTE_DB_CONFIG['database'],
            port=REMOTE_DB_CONFIG['port'],
            charset=REMOTE_DB_CONFIG['charset'],
            connect_timeout=REMOTE_DB_CONFIG['connect_timeout'],
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = conn.cursor()
        
        # Verifica colonne esistenti
        cursor.execute("DESCRIBE scan_log")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        logger.info(f"Colonne esistenti in scan_log: {column_names}")
        
        # Colonne da aggiungere
        alter_statements = []
        if 'raw_code' not in column_names:
            alter_statements.append("ADD COLUMN raw_code VARCHAR(50) NULL")
        if 'product_code' not in column_names:
            alter_statements.append("ADD COLUMN product_code INT NULL")
        if 'scan_date' not in column_names:
            alter_statements.append("ADD COLUMN scan_date VARCHAR(20) NULL")
        if 'scan_time' not in column_names:
            alter_statements.append("ADD COLUMN scan_time VARCHAR(20) NULL")
        
        # Esegui gli ALTER TABLE se necessario
        if alter_statements:
            alter_sql = "ALTER TABLE scan_log " + ", ".join(alter_statements)
            logger.info(f"Esecuzione SQL: {alter_sql}")
            cursor.execute(alter_sql)
            conn.commit()
            logger.info("Colonne aggiunte con successo!")
        else:
            logger.info("Nessuna colonna da aggiungere.")
        
        # Verifica le colonne dopo le modifiche
        cursor.execute("DESCRIBE scan_log")
        columns_after = cursor.fetchall()
        column_names_after = [col['Field'] for col in columns_after]
        logger.info(f"Colonne dopo l'aggiornamento: {column_names_after}")
        
        conn.close()
        logger.info("Aggiornamento database MySQL completato!")
        return True
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento del database: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Avvio aggiornamento database MySQL...")
    success = update_mysql_database()
    if not success:
        logger.error("Aggiornamento database fallito. Controlla i log per maggiori dettagli.") 