import os
from datetime import timedelta
import pymysql.cursors
import logging
import sys

logger = logging.getLogger(__name__)

# Importa il ConfigManager - OBBLIGATORIO
try:
    from app.config_manager import get_config_manager
    config_manager = get_config_manager()
    logger.info("External configuration loaded successfully")
except Exception as e:
    logger.critical(f"FATAL: Could not load external configuration: {str(e)}")
    logger.critical("La configurazione esterna è obbligatoria. Verifica che il file DBLogix.exe.config esista e sia valido.")
    sys.exit(1)

# Flask application configuration - basata completamente sul file .config
class Config:
    """Configurazione Flask basata esclusivamente sul file .config"""
    
    SECRET_KEY = config_manager.get_setting('SECRET_KEY')
    if not SECRET_KEY:
        logger.critical("SECRET_KEY non trovato nel file di configurazione")
        sys.exit(1)
    
    DEBUG = config_manager.get_setting('FLASK_DEBUG', False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=config_manager.get_setting('SESSION_TIMEOUT_HOURS', 2))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy Database URI - deve essere un attributo della classe per PyInstaller
    try:
        _remote_db_config = config_manager.get_db_config()
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{_remote_db_config['user']}:{_remote_db_config['password']}"
            f"@{_remote_db_config['host']}:{_remote_db_config['port']}"
            f"/{_remote_db_config['database']}?charset=utf8"
        )
        logger.info("SQLAlchemy URI added to Config class for PyInstaller compatibility")
    except Exception as e:
        logger.critical(f"FATAL: Errore nella creazione dell'URI SQLAlchemy per Config class: {str(e)}")
        sys.exit(1)

# Configurazione database remoto - completamente basata sul file .config
try:
    REMOTE_DB_CONFIG = config_manager.get_db_config()
    logger.info(f"Database configuration loaded: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
    
    # Verifica che i parametri essenziali siano presenti
    required_db_params = ['host', 'user', 'password', 'database', 'port']
    missing_params = [param for param in required_db_params if not REMOTE_DB_CONFIG.get(param)]
    
    if missing_params:
        logger.critical(f"Parametri database mancanti nel file di configurazione: {missing_params}")
        sys.exit(1)
        
except Exception as e:
    logger.critical(f"FATAL: Errore nel caricamento della configurazione database: {str(e)}")
    sys.exit(1)

# SQLAlchemy URI per il database locale
try:
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}"
        f"@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}"
        f"/{REMOTE_DB_CONFIG['database']}?charset=utf8"
    )
    logger.info("SQLAlchemy URI creato con successo")
except Exception as e:
    logger.critical(f"FATAL: Errore nella creazione dell'URI SQLAlchemy: {str(e)}")
    sys.exit(1)

def get_direct_connection_config():
    """Restituisce un dizionario per la connessione diretta a MySQL senza SQLAlchemy"""
    try:
        return {
            'host': REMOTE_DB_CONFIG['host'],
            'user': REMOTE_DB_CONFIG['user'],
            'password': REMOTE_DB_CONFIG['password'],
            'database': REMOTE_DB_CONFIG['database'],
            'port': REMOTE_DB_CONFIG['port'],
            'charset': REMOTE_DB_CONFIG['charset'],
            'cursorclass': REMOTE_DB_CONFIG['cursorclass'],
            'connect_timeout': REMOTE_DB_CONFIG.get('connect_timeout', 10),
            'read_timeout': REMOTE_DB_CONFIG.get('read_timeout', 30),
            'write_timeout': REMOTE_DB_CONFIG.get('write_timeout', 30),
            'ssl_disabled': REMOTE_DB_CONFIG.get('ssl_disabled', True),
            'use_unicode': REMOTE_DB_CONFIG.get('use_unicode', True)
        }
    except Exception as e:
        logger.error(f"Errore nella creazione della configurazione di connessione diretta: {str(e)}")
        raise

def update_db_config(new_config):
    """Aggiorna la configurazione del database nel file .config"""
    global REMOTE_DB_CONFIG, SQLALCHEMY_DATABASE_URI
    
    try:
        # Aggiorna usando il config manager
        config_manager.update_db_config(new_config)
        REMOTE_DB_CONFIG = config_manager.get_db_config()
        
        # Aggiorna l'URI di SQLAlchemy
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}"
            f"@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}"
            f"/{REMOTE_DB_CONFIG['database']}?charset=utf8"
        )
        
        logger.info(f"Database configuration updated: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
        
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento della configurazione database: {str(e)}")
        raise

def reload_config():
    """Ricarica la configurazione dal file .config"""
    global config_manager, REMOTE_DB_CONFIG, SQLALCHEMY_DATABASE_URI
    
    try:
        from app.config_manager import reload_config as reload_external_config
        config_manager = reload_external_config()
        
        if not config_manager:
            logger.critical("FATAL: Impossibile ricaricare il config manager")
            sys.exit(1)
        
        REMOTE_DB_CONFIG = config_manager.get_db_config()
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}"
            f"@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}"
            f"/{REMOTE_DB_CONFIG['database']}?charset=utf8"
        )
        
        logger.info("Configuration reloaded from external file")
        
    except Exception as e:
        logger.error(f"Errore nel ricaricamento della configurazione: {str(e)}")
        raise

# Funzioni helper per accedere alle configurazioni specifiche
def get_company_config_from_file():
    """Ottiene la configurazione azienda dal file .config"""
    try:
        return config_manager.get_company_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione azienda: {str(e)}")
        return {}

def get_system_config_from_file():
    """Ottiene le configurazioni sistema dal file .config"""
    try:
        return config_manager.get_system_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazioni sistema: {str(e)}")
        return {}

def get_chat_config_from_file():
    """Ottiene la configurazione chat dal file .config"""
    try:
        return config_manager.get_chat_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione chat: {str(e)}")
        return {}

def get_clienti_config_from_file():
    """Ottiene la configurazione clienti dal file .config"""
    try:
        return config_manager.get_clienti_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione clienti: {str(e)}")
        return {}

def get_ddt_config_from_file():
    """Ottiene la configurazione DDT dal file .config"""
    try:
        return config_manager.get_ddt_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione DDT: {str(e)}")
        return {}

def get_fatture_config_from_file():
    """Ottiene la configurazione fatture dal file .config"""
    try:
        return config_manager.get_fatture_config()
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione fatture: {str(e)}")
        return {}

# Funzioni per aggiornare le configurazioni nel file .config
def update_company_config(company_config):
    """Aggiorna la configurazione azienda nel file .config"""
    try:
        config_manager.update_company_config(company_config)
        logger.info("Company configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione azienda: {str(e)}")
        raise

def update_system_config(system_config):
    """Aggiorna le configurazioni sistema nel file .config"""
    try:
        config_manager.update_system_config(system_config)
        logger.info("System configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazioni sistema: {str(e)}")
        raise

def update_chat_config(chat_config):
    """Aggiorna la configurazione chat nel file .config"""
    try:
        config_manager.update_chat_config(chat_config)
        logger.info("Chat configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione chat: {str(e)}")
        raise

def update_clienti_config(clienti_config):
    """Aggiorna la configurazione clienti nel file .config"""
    try:
        config_manager.update_clienti_config(clienti_config)
        logger.info("Clienti configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione clienti: {str(e)}")
        raise

def update_ddt_config(ddt_config):
    """Aggiorna la configurazione DDT nel file .config"""
    try:
        config_manager.update_ddt_config(ddt_config)
        logger.info("DDT configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione DDT: {str(e)}")
        raise

def update_fatture_config(fatture_config):
    """Aggiorna la configurazione fatture nel file .config"""
    try:
        config_manager.update_fatture_config(fatture_config)
        logger.info("Fatture configuration updated in external file")
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento configurazione fatture: {str(e)}")
        raise

# Funzioni di utilità per ottenere configurazioni specifiche
def get_app_config():
    """Ottiene la configurazione dell'applicazione Flask"""
    try:
        return {
            'host': config_manager.get_setting('APP_HOST', '0.0.0.0'),
            'port': config_manager.get_setting('APP_PORT', 5000),
            'debug': config_manager.get_setting('FLASK_DEBUG', False),
            'use_ssl': config_manager.get_setting('USE_SSL', False)
        }
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione app: {str(e)}")
        return {'host': '0.0.0.0', 'port': 5000, 'debug': False, 'use_ssl': False}

def get_network_config():
    """Ottiene la configurazione di rete"""
    try:
        return {
            'scan_timeout': config_manager.get_setting('NETWORK_SCAN_TIMEOUT', 5),
            'network_prefix': config_manager.get_setting('NETWORK_PREFIX', '192.168.1')
        }
    except Exception as e:
        logger.error(f"Errore nel caricamento configurazione di rete: {str(e)}")
        return {'scan_timeout': 5, 'network_prefix': '192.168.1'}

def test_db_connection():
    """Testa la connessione al database utilizzando la configurazione dal file .config"""
    try:
        import pymysql
        connection = pymysql.connect(**get_direct_connection_config())
        connection.close()
        logger.info("Test connessione database: SUCCESSO")
        return True
    except Exception as e:
        logger.error(f"Test connessione database: FALLITO - {str(e)}")
        return False

# Verifica iniziale della configurazione
def verify_config():
    """Verifica che la configurazione sia valida e completa"""
    try:
        # Verifica config manager
        if not config_manager:
            raise Exception("Config manager non disponibile")
        
        # Verifica configurazione database
        db_config = get_direct_connection_config()
        required_fields = ['host', 'user', 'password', 'database', 'port']
        missing_fields = [field for field in required_fields if not db_config.get(field)]
        
        if missing_fields:
            raise Exception(f"Campi database mancanti: {missing_fields}")
        
        # Verifica SECRET_KEY
        if not config_manager.get_setting('SECRET_KEY'):
            raise Exception("SECRET_KEY non configurato")
        
        logger.info("Verifica configurazione: SUCCESSO")
        return True
        
    except Exception as e:
        logger.critical(f"Verifica configurazione: FALLITA - {str(e)}")
        return False

# Esegui verifica all'import
if not verify_config():
    logger.critical("FATAL: Configurazione non valida. L'applicazione non può continuare.")
    sys.exit(1) 