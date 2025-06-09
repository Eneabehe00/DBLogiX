#!/usr/bin/env python3
"""
DBLogiX Service - Main entry point for Windows Service
Questo file è ottimizzato per essere compilato con PyInstaller e funzionare come servizio Windows
"""

import os
import sys
import logging
import signal
import threading
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path


# Configura il path per l'esecuzione
def setup_paths():
    """Setup paths for PyInstaller bundle or development environment"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        application_path = Path(sys.executable).parent
        base_path = application_path
    else:
        # Running in development
        application_path = Path(__file__).parent
        base_path = application_path
    
    # Aggiungi il path base al sys.path se non presente
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))
    
    # Cambia la directory di lavoro
    os.chdir(base_path)
    
    return base_path

# Setup paths prima di qualsiasi import
BASE_PATH = setup_paths()

# Configura le variabili d'ambiente per la produzione
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('FLASK_DEBUG', 'False')
os.environ.setdefault('FLASK_HOST', '0.0.0.0')
os.environ.setdefault('FLASK_PORT', '5000')

def setup_logging():
    """Setup logging per il servizio"""
    logs_dir = BASE_PATH / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Configura il logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                logs_dir / 'dblogix_service.log', 
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def generate_ssl_certificates():
    """Genera certificati SSL se non esistono"""
    cert_file = BASE_PATH / 'cert.pem'
    key_file = BASE_PATH / 'key.pem'
    
    if not (cert_file.exists() and key_file.exists()):
        logger.info("Generazione certificati SSL...")
        try:
            from scripts.generate_certs import generate_ssl_certificates as gen_certs
            success = gen_certs()
            if success:
                logger.info("Certificati SSL generati con successo")
            else:
                logger.error("Errore nella generazione dei certificati SSL")
                return False
        except Exception as e:
            logger.error(f"Errore durante la generazione dei certificati: {e}")
            return False
    else:
        logger.info("Certificati SSL esistenti trovati")
    
    return True

def create_flask_app():
    """Crea e configura l'applicazione Flask"""
    try:
        # Import dell'applicazione Flask
        from app import create_app
        from app.models import db
        
        app = create_app()
        
        # Crea le tabelle del database se necessario
        with app.app_context():
            try:
                db.create_all()
                logger.info('Database tables created (if they did not exist)')
            except Exception as e:
                logger.error(f'Error creating database tables: {str(e)}')
        
        return app
    except Exception as e:
        logger.error(f"Errore nella creazione dell'app Flask: {e}")
        raise

class DBLogiXService:
    """Classe principale del servizio DBLogiX"""
    
    def __init__(self):
        self.app = None
        self.server_thread = None
        self.running = False
        self.shutdown_event = threading.Event()
    
    def start(self):
        """Avvia il servizio"""
        logger.info("Avvio del servizio DBLogiX...")
        
        # Genera certificati SSL se necessario
        if not generate_ssl_certificates():
            logger.error("Impossibile generare i certificati SSL")
            return False
        
        # Crea l'applicazione Flask
        try:
            self.app = create_flask_app()
        except Exception as e:
            logger.error(f"Errore nella creazione dell'applicazione: {e}")
            return False
        
        # Avvia il server in un thread separato
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        logger.info("Servizio DBLogiX avviato con successo")
        return True
    
    def stop(self):
        """Ferma il servizio"""
        logger.info("Arresto del servizio DBLogiX...")
        self.running = False
        self.shutdown_event.set()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=10)
        
        logger.info("Servizio DBLogiX arrestato")
    
    def _run_server(self):
        """Esegue il server Flask"""
        try:
            host = os.environ.get('FLASK_HOST', '0.0.0.0')
            port = int(os.environ.get('FLASK_PORT', 5000))
            
            cert_file = BASE_PATH / 'cert.pem'
            key_file = BASE_PATH / 'key.pem'
            
            logger.info(f"Avvio server HTTPS su {host}:{port}")
            
            # Avvia il server con SSL
            self.app.run(
                host=host,
                port=port,
                debug=False,
                ssl_context=(str(cert_file), str(key_file)),
                threaded=True,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Errore nell'avvio del server: {e}")
            self.running = False

def signal_handler(signum, frame):
    """Gestisce i segnali di terminazione"""
    logger.info(f"Ricevuto segnale {signum}, arresto del servizio...")
    if 'service' in globals():
        service.stop()
    sys.exit(0)

def main():
    """Funzione principale del servizio"""
    global logger, service
    
    # Setup logging
    logger = setup_logging()
    logger.info("=== Avvio DBLogiX Service ===")
    
    # Configura i gestori di segnali
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crea e avvia il servizio
    service = DBLogiXService()
    
    try:
        if service.start():
            logger.info("Servizio in esecuzione. Premi Ctrl+C per terminare.")
            
            # Mantieni il servizio in vita
            try:
                while service.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interruzione da tastiera ricevuta")
        else:
            logger.error("Impossibile avviare il servizio")
            return 1
    
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del servizio: {e}")
        return 1
    
    finally:
        service.stop()
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 