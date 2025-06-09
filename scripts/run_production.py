# run_production.py
#!/usr/bin/env python3
"""
DBLogiX Production Server
Avvia l'applicazione in modalità produzione con Waitress WSGI server
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from waitress import serve
import socket

# Funzione di logging

def setup_production_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler = RotatingFileHandler(
        'logs/dblogix_production.log', maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return root_logger

# Determinazione cartella base (bundle vs dev)

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

# Creazione app Flask con template/static gestiti

def create_production_app():
    base = get_base_path()
    from app import create_app as _create_app
    app = _create_app(
        template_folder=os.path.join(base, 'templates'),
        static_folder=os.path.join(base,    'static')
    )
    from production_config import ProductionConfig
    from app.config import REMOTE_DB_CONFIG
    app.config.from_object(ProductionConfig)
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@"
        f"{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
    )
    return app

# Funzione principale

def main():
    logger = setup_production_logging()
    try:
        logger.info("AVVIO DBLogiX in modalità produzione...")
        app = create_production_app()
        local_ip = "127.0.0.1"
        port = 5000
        logger.info(f"APPLICAZIONE ACCESSIBILE SU: http://127.0.0.1:{port}")
        serve(app, host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"ERRORE durante l'avvio: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()