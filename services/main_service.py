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
        # Running in development - se siamo nella cartella services, vai alla parent
        current_path = Path(__file__).parent
        if current_path.name == 'services':
            # Siamo nella cartella services, la parent contiene app.py
            base_path = current_path.parent
        else:
            base_path = current_path
    
    # Aggiungi il path base al sys.path se non presente
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))
    
    # Cambia la directory di lavoro alla base del progetto
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
    # Setup logger locale se non definito
    local_logger = logging.getLogger(__name__) if 'logger' not in globals() else logger
    
    cert_file = BASE_PATH / 'cert.pem'
    key_file = BASE_PATH / 'key.pem'
    
    if not (cert_file.exists() and key_file.exists()):
        local_logger.info("Generazione certificati SSL...")
        try:
            # Import da generate_certs che è nella stessa directory
            import generate_certs
            success = generate_certs.generate_ssl_certificates()
            if success:
                local_logger.info("Certificati SSL generati con successo")
            else:
                local_logger.error("Errore nella generazione dei certificati SSL")
                return False
        except Exception as e:
            local_logger.error(f"Errore durante la generazione dei certificati: {e}")
            return False
    else:
        local_logger.info("Certificati SSL esistenti trovati")
    
    return True

def create_flask_app():
    """Crea e configura l'applicazione Flask"""
    local_logger = logging.getLogger(__name__) if 'logger' not in globals() else logger
    
    try:
        # Assicurati che il path includa la directory parent per trovare app.py
        parent_dir = BASE_PATH.parent if BASE_PATH.name == 'services' else BASE_PATH
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        
        local_logger.info(f"Added to sys.path: {parent_dir}")
        local_logger.info(f"Current working directory: {os.getcwd()}")
        local_logger.info(f"BASE_PATH: {BASE_PATH}")
        
        # Import dell'applicazione Flask dalla directory parent
        import app
        from app.models import db
        
        local_logger.info("Successfully imported app module")
        
        flask_app = app.create_app()
        local_logger.info("Flask app created successfully")
        
        # Crea le tabelle del database se necessario
        with flask_app.app_context():
            try:
                db.create_all()
                local_logger.info('Database tables created (if they did not exist)')
            except Exception as e:
                local_logger.error(f'Error creating database tables: {str(e)}')
        
        return flask_app
    except Exception as e:
        local_logger.error(f"Errore nella creazione dell'app Flask: {e}")
        local_logger.error(f"Current sys.path: {sys.path[:5]}")  # Mostra primi 5 elementi
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
        # Setup logger locale
        local_logger = logging.getLogger(__name__) if 'logger' not in globals() else logger
        local_logger.info("Avvio del servizio DBLogiX...")
        
        # Genera certificati SSL se necessario
        if not generate_ssl_certificates():
            local_logger.error("Impossibile generare i certificati SSL")
            return False
        
        # Crea l'applicazione Flask
        try:
            self.app = create_flask_app()
        except Exception as e:
            local_logger.error(f"Errore nella creazione dell'applicazione: {e}")
            return False
        
        # Avvia il server in un thread separato
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        
        local_logger.info("Servizio DBLogiX avviato con successo")
        return True
    
    def stop(self):
        """Ferma il servizio"""
        local_logger = logging.getLogger(__name__) if 'logger' not in globals() else logger
        local_logger.info("Arresto del servizio DBLogiX...")
        self.running = False
        self.shutdown_event.set()
        
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=10)
        
        local_logger.info("Servizio DBLogiX arrestato")
    
    def _run_server(self):
        """Esegue il server Flask"""
        local_logger = logging.getLogger(__name__) if 'logger' not in globals() else logger
        try:
            host = os.environ.get('FLASK_HOST', '0.0.0.0')
            port = int(os.environ.get('FLASK_PORT', 5000))
            
            cert_file = BASE_PATH / 'cert.pem'
            key_file = BASE_PATH / 'key.pem'
            
            local_logger.info(f"Avvio server HTTPS su {host}:{port}")
            
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
            local_logger.error(f"Errore nell'avvio del server: {e}")
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
    
    # Controllo se eseguito direttamente o come servizio
    is_service_mode = '--service' in sys.argv or getattr(sys, 'frozen', False)
    is_direct_execution = not is_service_mode and (len(sys.argv) == 1 or '--direct' in sys.argv)
    
    if is_direct_execution:
        logger.info("Esecuzione diretta rilevata - modalità interattiva")
        print("[INFO] Avvio DBLogiX in modalità diretta...")
        print("[INFO] Apri il browser su: https://localhost:5000")
        print("[WARNING] Accetta il certificato self-signed del browser")
        print("[INFO] Premi Ctrl+C per terminare\n")
    
    # Configura i gestori di segnali
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Crea e avvia il servizio
    service = DBLogiXService()
    
    try:
        if service.start():
            if is_direct_execution:
                print("[OK] DBLogiX avviato correttamente!")
                print("[INFO] URL: https://localhost:5000")
                print("[INFO] Log: logs/dblogix_service.log")
                print("-" * 50)
            logger.info("Servizio in esecuzione. Premi Ctrl+C per terminare.")
            
            # Mantieni il servizio in vita
            try:
                while service.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interruzione da tastiera ricevuta")
                if is_direct_execution:
                    print("\n[INFO] Arresto in corso...")
        else:
            logger.error("Impossibile avviare il servizio")
            if is_direct_execution and sys.stdin and sys.stdin.isatty():
                print("[ERROR] Errore nell'avvio del servizio. Controlla i log.")
                input("Premi INVIO per chiudere...")
            elif is_direct_execution:
                print("[ERROR] Errore nell'avvio del servizio. Controlla i log.")
                time.sleep(3)  # Pausa per permettere di leggere il messaggio
            return 1
    
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione del servizio: {e}")
        if is_direct_execution and sys.stdin and sys.stdin.isatty():
            print(f"[ERROR] Errore: {e}")
            print("[INFO] Controlla i log per dettagli: logs/dblogix_service.log")
            input("Premi INVIO per chiudere...")
        elif is_direct_execution:
            print(f"[ERROR] Errore: {e}")
            print("[INFO] Controlla i log per dettagli: logs/dblogix_service.log")
            time.sleep(3)
        return 1
    
    finally:
        service.stop()
        if is_direct_execution:
            print("[OK] DBLogiX arrestato correttamente")
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 