import os
from datetime import timedelta
import pymysql.cursors

# Flask application configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-for-dblogix'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    # Enable debug mode if environment variable is set
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

# Remote database configuration (Bilancia)
REMOTE_DB_CONFIG = {
    'host': '192.168.1.32',
    'user': 'user',
    'password': 'dibal',
    'database': 'sys_datos',
    'port': 3306,
    'connect_timeout': 10,
    'read_timeout': 30,
    'write_timeout': 30,
    'charset': 'utf8',
    'use_unicode': True,
    'ssl_disabled': True,
    'cursorclass': 'pymysql.cursors.DictCursor',
}

# SQLAlchemy URI for the local database
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://user:dibal@192.168.1.32:3306/sys_datos"

# Optional easier-to-use configuration without SQLAlchemy for direct connections
def get_direct_connection_config():
    """Returns a dictionary for direct connection to MySQL without SQLAlchemy"""
    return {
    'host': '192.168.1.22',
        'user': REMOTE_DB_CONFIG['user'],
        'password': REMOTE_DB_CONFIG['password'],
        'database': REMOTE_DB_CONFIG['database'],
        'port': REMOTE_DB_CONFIG['port'],
        'charset': REMOTE_DB_CONFIG['charset'],
        'cursorclass': REMOTE_DB_CONFIG['cursorclass'],
        'ssl_disabled': REMOTE_DB_CONFIG.get('ssl_disabled', True)
    } 