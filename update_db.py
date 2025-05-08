"""
Script per aggiornare la struttura del database
Ricrea le tabelle necessarie per adattarsi alle modifiche nei modelli
"""
from app import app, db
import logging
from sqlalchemy import inspect

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    """Ricrea le tabelle mancanti o aggiorna quelle esistenti"""
    with app.app_context():
        try:
            logger.info("Aggiornamento database...")
            
            # Crea solo le tabelle che non esistono già
            db.create_all()
            
            # Per le tabelle esistenti, verifica se ci sono colonne da aggiungere
            # Questo approccio è più sicuro perché non perderemo dati
            inspector = inspect(db.engine)
            
            # Verifica la tabella scan_log
            if 'scan_log' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('scan_log')]
                logger.info(f"Colonne esistenti in scan_log: {columns}")
                
                # Se mancano colonne, crea una nuova tabella temporanea e migra i dati
                missing_columns = []
                for expected_col in ['raw_code', 'product_code', 'scan_date', 'scan_time']:
                    if expected_col not in columns:
                        missing_columns.append(expected_col)
                
                if missing_columns:
                    logger.info(f"Colonne mancanti: {missing_columns}")
                    logger.info("Per aggiungere le colonne mancanti, esegui il seguente SQL sul tuo database:")
                    for col in missing_columns:
                        if col == 'raw_code':
                            logger.info("ALTER TABLE scan_log ADD COLUMN raw_code VARCHAR(50);")
                        elif col == 'product_code':
                            logger.info("ALTER TABLE scan_log ADD COLUMN product_code INT;")
                        elif col == 'scan_date' or col == 'scan_time':
                            logger.info(f"ALTER TABLE scan_log ADD COLUMN {col} VARCHAR(20);")
            
            logger.info("Database aggiornato! Le tabelle esistenti potrebbero richiedere un aggiornamento manuale.")
            return True
        except Exception as e:
            logger.error(f"Errore durante l'aggiornamento del database: {str(e)}")
            return False

if __name__ == "__main__":
    logger.info("Avvio aggiornamento database...")
    success = update_database()
    if success:
        logger.info("Processo di aggiornamento completato.")
    else:
        logger.error("Aggiornamento fallito. Controlla i log per maggiori dettagli.") 