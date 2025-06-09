import os
from datetime import timedelta
import pymysql.cursors
import logging

logger = logging.getLogger(__name__)

# Importa il ConfigManager
try:
    from app.config_manager import get_config_manager
    config_manager = get_config_manager()
    logger.info("External configuration loaded successfully")
except Exception as e:
    logger.warning(f"Could not load external configuration: {str(e)}. Using default values.")
    config_manager = None

# Flask application configuration
class Config:
    # Usa il config manager se disponibile, altrimenti usa i valori di default
    if config_manager:
        SECRET_KEY = config_manager.get_setting('SECRET_KEY', os.environ.get('SECRET_KEY', 'dev-key-for-dblogix'))
        DEBUG = config_manager.get_setting('FLASK_DEBUG', os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't'])
        PERMANENT_SESSION_LIFETIME = timedelta(hours=config_manager.get_setting('SESSION_TIMEOUT_HOURS', 2))
    else:
        SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-dblogix'
        DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
        PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

# Remote database configuration (Bilancia)
# Usa il config manager se disponibile, altrimenti usa i valori di default
if config_manager:
    REMOTE_DB_CONFIG = config_manager.get_db_config()
    logger.info(f"Database configuration loaded from external config: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")
else:
    REMOTE_DB_CONFIG = {
        'host': os.environ.get('DB_HOST', '192.168.1.32'),
        'user': os.environ.get('DB_USER', 'user'),
        'password': os.environ.get('DB_PASSWORD', 'dibal'),
        'database': os.environ.get('DB_DATABASE', 'sys_datos'),
        'port': int(os.environ.get('DB_PORT', 3306)),
        'connect_timeout': 10,
        'read_timeout': 30,
        'write_timeout': 30,
        'charset': 'utf8',
        'use_unicode': True,
        'ssl_disabled': True,
        'cursorclass': 'pymysql.cursors.DictCursor',
    }

# SQLAlchemy URI for the local database
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"

# Optional easier-to-use configuration without SQLAlchemy for direct connections
def get_direct_connection_config():
    """Returns a dictionary for direct connection to MySQL without SQLAlchemy"""
    return {
        'host': REMOTE_DB_CONFIG['host'],
        'user': REMOTE_DB_CONFIG['user'],
        'password': REMOTE_DB_CONFIG['password'],
        'database': REMOTE_DB_CONFIG['database'],
        'port': REMOTE_DB_CONFIG['port'],
        'charset': REMOTE_DB_CONFIG['charset'],
        'cursorclass': REMOTE_DB_CONFIG['cursorclass'],
        'ssl_disabled': REMOTE_DB_CONFIG.get('ssl_disabled', True)
    }

# Funzione per aggiornare la configurazione del database dall'esterno
def update_db_config(new_config):
    """Aggiorna la configurazione del database"""
    global REMOTE_DB_CONFIG, SQLALCHEMY_DATABASE_URI
    
    if config_manager:
        # Aggiorna usando il config manager
        config_manager.update_db_config(new_config)
        REMOTE_DB_CONFIG = config_manager.get_db_config()
    else:
        # Fallback: aggiorna solo in memoria
        REMOTE_DB_CONFIG.update(new_config)
    
    # Aggiorna anche l'URI di SQLAlchemy
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
    
    logger.info(f"Database configuration updated: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}")

# Funzione per ricaricare la configurazione
def reload_config():
    """Ricarica la configurazione dal file esterno"""
    global config_manager, REMOTE_DB_CONFIG, SQLALCHEMY_DATABASE_URI
    
    if config_manager:
        from app.config_manager import reload_config as reload_external_config
        config_manager = reload_external_config()
        REMOTE_DB_CONFIG = config_manager.get_db_config()
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
        logger.info("Configuration reloaded from external file")

# Funzioni helper per accedere alle configurazioni specifiche
def get_company_config_from_file():
    """Ottiene la configurazione azienda dal file esterno"""
    if config_manager:
        return config_manager.get_company_config()
    return {}

def get_system_config_from_file():
    """Ottiene le configurazioni sistema dal file esterno"""
    if config_manager:
        return config_manager.get_system_config()
    return {}

def get_chat_config_from_file():
    """Ottiene la configurazione chat dal file esterno"""
    if config_manager:
        return config_manager.get_chat_config()
    return {}

def get_clienti_config_from_file():
    """Ottiene la configurazione clienti dal file esterno"""
    if config_manager:
        return config_manager.get_clienti_config()
    return {}

def get_ddt_config_from_file():
    """Ottiene la configurazione DDT dal file esterno"""
    if config_manager:
        return config_manager.get_ddt_config()
    return {}

def get_fatture_config_from_file():
    """Ottiene la configurazione fatture dal file esterno"""
    if config_manager:
        return config_manager.get_fatture_config()
    return {}

# Funzioni per aggiornare le configurazioni
def update_company_config(company_config):
    """Aggiorna la configurazione azienda"""
    if config_manager:
        config_manager.update_company_config(company_config)
        logger.info("Company configuration updated in external file")

def update_system_config(system_config):
    """Aggiorna le configurazioni sistema"""
    if config_manager:
        config_manager.update_system_config(system_config)
        logger.info("System configuration updated in external file")

def update_chat_config(chat_config):
    """Aggiorna la configurazione chat"""
    if config_manager:
        config_manager.update_chat_config(chat_config)
        logger.info("Chat configuration updated in external file")

def update_clienti_config(clienti_config):
    """Aggiorna la configurazione clienti"""
    if config_manager:
        config_manager.update_clienti_config(clienti_config)
        logger.info("Clienti configuration updated in external file")

def update_ddt_config(ddt_config):
    """Aggiorna la configurazione DDT"""
    if config_manager:
        config_manager.update_ddt_config(ddt_config)
        logger.info("DDT configuration updated in external file")

def update_fatture_config(fatture_config):
    """Aggiorna la configurazione fatture"""
    if config_manager:
        config_manager.update_fatture_config(fatture_config)
        logger.info("Fatture configuration updated in external file") 