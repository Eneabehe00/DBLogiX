#!/usr/bin/env python3
"""
Test script per verificare l'installazione automatica del servizio DBLogiX
Simula quello che fa l'installer InnoSetup
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

def setup_logging():
    """Setup logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_service_installation():
    """Testa l'installazione automatica del servizio"""
    logger = setup_logging()
    
    logger.info("=== Test Installazione Servizio DBLogiX ===")
    
    # Percorso della distribuzione compilata
    dist_path = Path("../dist/DBLogiX")
    if not dist_path.exists():
        logger.error("Directory di distribuzione non trovata. Esegui prima il build.")
        return False
    
    logger.info(f"Directory di distribuzione: {dist_path.absolute()}")
    
    # Cambia nella directory di distribuzione
    old_cwd = os.getcwd()
    os.chdir(dist_path)
    
    try:
        # Step 1: Genera certificati SSL
        logger.info("Step 1: Generazione certificati SSL...")
        result = subprocess.run([
            sys.executable, "generate_certs.py"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✓ Certificati SSL generati")
        else:
            logger.error(f"✗ Errore generazione certificati: {result.stderr}")
            return False
        
        # Step 2: Configura firewall
        logger.info("Step 2: Configurazione firewall...")
        result = subprocess.run([
            "netsh", "advfirewall", "firewall", "add", "rule",
            "name=DBLogiX HTTPS Test", "dir=in", "action=allow", 
            "protocol=TCP", "localport=5000"
        ], capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            logger.info("✓ Firewall configurato")
        else:
            logger.warning(f"⚠ Firewall: {result.stderr}")
        
        # Step 3: Installa servizio
        logger.info("Step 3: Installazione servizio...")
        result = subprocess.run([
            sys.executable, "dblogix_service.py", "install"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✓ Servizio installato")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"✗ Errore installazione servizio: {result.stderr}")
            return False
        
        # Step 4: Avvia servizio
        logger.info("Step 4: Avvio servizio...")
        result = subprocess.run([
            sys.executable, "dblogix_service.py", "start"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✓ Servizio avviato")
            logger.info(f"Output: {result.stdout}")
        else:
            logger.error(f"✗ Errore avvio servizio: {result.stderr}")
            return False
        
        # Step 5: Verifica stato
        logger.info("Step 5: Verifica stato...")
        time.sleep(5)  # Attendi che il servizio si stabilizzi
        
        result = subprocess.run([
            sys.executable, "dblogix_service.py", "status"
        ], capture_output=True, text=True, timeout=15)
        
        logger.info(f"Stato servizio: {result.stdout}")
        
        if "RUNNING" in result.stdout:
            logger.info("✓ Servizio in esecuzione!")
            logger.info("✓ Test COMPLETATO con successo!")
            logger.info("🌐 DBLogiX è accessibile su: https://localhost:5000")
            
            # Test connessione
            logger.info("Step 6: Test connessione...")
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.get("https://localhost:5000", 
                                      verify=False, timeout=10)
                if response.status_code == 200:
                    logger.info("✓ Connessione HTTPS funzionante!")
                else:
                    logger.warning(f"⚠ Risposta HTTP: {response.status_code}")
            except Exception as e:
                logger.warning(f"⚠ Test connessione fallito: {e}")
            
            return True
        else:
            logger.error("✗ Servizio non in esecuzione")
            return False
    
    except Exception as e:
        logger.error(f"✗ Errore durante il test: {e}")
        return False
    
    finally:
        os.chdir(old_cwd)

def cleanup_test():
    """Pulisce il test rimuovendo il servizio"""
    logger = setup_logging()
    
    logger.info("=== Pulizia Test ===")
    
    dist_path = Path("../dist/DBLogiX")
    if not dist_path.exists():
        return
    
    old_cwd = os.getcwd()
    os.chdir(dist_path)
    
    try:
        # Ferma servizio
        logger.info("Arresto servizio...")
        subprocess.run([
            sys.executable, "dblogix_service.py", "stop"
        ], capture_output=True, text=True, timeout=15)
        
        # Rimuovi servizio
        logger.info("Rimozione servizio...")
        subprocess.run([
            sys.executable, "dblogix_service.py", "uninstall"
        ], capture_output=True, text=True, timeout=15)
        
        # Rimuovi regola firewall
        logger.info("Rimozione regola firewall...")
        subprocess.run([
            "netsh", "advfirewall", "firewall", "delete", "rule", 
            "name=DBLogiX HTTPS Test"
        ], capture_output=True, text=True, shell=True)
        
        logger.info("✓ Pulizia completata")
        
    except Exception as e:
        logger.error(f"✗ Errore durante pulizia: {e}")
    
    finally:
        os.chdir(old_cwd)

def main():
    """Funzione principale"""
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_test()
        return 0
    
    logger = setup_logging()
    
    logger.info("DBLogiX Service Installation Test")
    logger.info("=" * 50)
    
    # Controlla privilegi amministratore
    try:
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.error("✗ Richiesti privilegi di amministratore!")
            logger.info("Esegui come amministratore e riprova.")
            return 1
    except:
        logger.warning("⚠ Impossibile verificare privilegi amministratore")
    
    # Esegui test
    success = test_service_installation()
    
    if success:
        logger.info("\n🎉 TEST PASSATO!")
        logger.info("Il servizio si installa e avvia correttamente.")
        logger.info("L'installer dovrebbe funzionare perfettamente!")
        
        # Chiedi se pulire
        try:
            choice = input("\nVuoi rimuovere il servizio di test? (s/n): ")
            if choice.lower() == 's':
                cleanup_test()
        except:
            pass
        
        return 0
    else:
        logger.error("\n❌ TEST FALLITO!")
        logger.error("Ci sono problemi con l'installazione del servizio.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 