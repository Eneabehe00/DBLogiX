#!/usr/bin/env python3
"""
Debug script per diagnosticare problemi del servizio DBLogiX
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

def setup_logging():
    """Setup logging per debug"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug_service.log')
        ]
    )
    return logging.getLogger(__name__)

def check_python_environment():
    """Controlla l'ambiente Python"""
    logger.info("=== Controllo Ambiente Python ===")
    
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Python path: {sys.path[:3]}...")
    
    # Controlla moduli chiave
    required_modules = [
        'flask', 'sqlalchemy', 'pymysql', 'cryptography', 
        'win32serviceutil', 'win32service', 'win32event'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} OK")
        except ImportError as e:
            logger.error(f"❌ {module} MISSING: {e}")

def check_service_files():
    """Controlla i file del servizio"""
    logger.info("=== Controllo File Servizio ===")
    
    base_path = Path(__file__).parent.parent
    
    required_files = [
        'services/main_service.py',
        'services/dblogix_service.py', 
        'services/windows_service_wrapper.py',
        'app.py',
        'requirements.txt',
        'DBLogix.exe.config'
    ]
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            logger.info(f"✅ {file_path} OK")
        else:
            logger.error(f"❌ {file_path} MISSING")

def test_direct_execution():
    """Testa l'esecuzione diretta del servizio"""
    logger.info("=== Test Esecuzione Diretta ===")
    
    try:
        # Cambia nella directory dei servizi
        services_dir = Path(__file__).parent.parent / 'services'
        os.chdir(services_dir)
        
        # Prova a importare e avviare il servizio
        sys.path.insert(0, str(services_dir))
        
        logger.info("Importing main_service...")
        import main_service
        
        logger.info("Creando istanza del servizio...")
        service = main_service.DBLogiXService()
        
        logger.info("Tentativo di avvio del servizio...")
        if service.start():
            logger.info("✅ Servizio avviato con successo!")
            logger.info("Attendo 10 secondi per verificare la stabilità...")
            time.sleep(10)
            
            if service.running:
                logger.info("✅ Servizio ancora in esecuzione dopo 10 secondi")
            else:
                logger.error("❌ Servizio si è fermato")
            
            logger.info("Fermando il servizio...")
            service.stop()
            logger.info("✅ Servizio fermato")
            return True
        else:
            logger.error("❌ Impossibile avviare il servizio")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore durante il test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_ssl_certificates():
    """Testa la generazione dei certificati SSL"""
    logger.info("=== Test Certificati SSL ===")
    
    try:
        base_path = Path(__file__).parent.parent
        cert_file = base_path / 'cert.pem'
        key_file = base_path / 'key.pem'
        
        # Rimuovi certificati esistenti per test
        if cert_file.exists():
            cert_file.unlink()
            logger.info("Rimosso cert.pem esistente")
        if key_file.exists():
            key_file.unlink()
            logger.info("Rimosso key.pem esistente")
        
        # Prova a generare i certificati
        os.chdir(base_path)
        sys.path.insert(0, str(base_path / 'scripts'))
        
        import generate_certs
        if generate_certs.generate_ssl_certificates():
            logger.info("✅ Certificati SSL generati con successo")
            logger.info(f"cert.pem size: {cert_file.stat().st_size} bytes")
            logger.info(f"key.pem size: {key_file.stat().st_size} bytes")
            return True
        else:
            logger.error("❌ Errore nella generazione dei certificati")
            return False
            
    except Exception as e:
        logger.error(f"❌ Errore durante la generazione certificati: {e}")
        return False

def test_service_commands():
    """Testa i comandi del servizio"""
    logger.info("=== Test Comandi Servizio ===")
    
    try:
        services_dir = Path(__file__).parent.parent / 'services'
        os.chdir(services_dir)
        
        # Test comandi base
        commands = ['status', 'stop', 'uninstall']
        
        for cmd in commands:
            logger.info(f"Testando comando: {cmd}")
            result = subprocess.run([
                sys.executable, 'dblogix_service.py', cmd
            ], capture_output=True, text=True, timeout=30)
            
            logger.info(f"Return code: {result.returncode}")
            if result.stdout:
                logger.info(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.error(f"STDERR: {result.stderr}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore durante test comandi: {e}")
        return False

def test_windows_service_wrapper():
    """Testa il wrapper del servizio Windows"""
    logger.info("=== Test Windows Service Wrapper ===")
    
    try:
        services_dir = Path(__file__).parent.parent / 'services'
        os.chdir(services_dir)
        sys.path.insert(0, str(services_dir))
        
        logger.info("Importing windows_service_wrapper...")
        import windows_service_wrapper
        
        logger.info("Creando istanza DBLogiXWindowsService...")
        service_class = windows_service_wrapper.DBLogiXWindowsService
        logger.info(f"Service name: {service_class._svc_name_}")
        logger.info(f"Service display name: {service_class._svc_display_name_}")
        logger.info(f"Service description: {service_class._svc_description_}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore durante test wrapper: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Funzione principale di debug"""
    global logger
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("DBLogiX Service Debug Tool")
    logger.info("=" * 60)
    
    tests = [
        ("Ambiente Python", check_python_environment),
        ("File Servizio", check_service_files),
        ("Certificati SSL", test_ssl_certificates),
        ("Comandi Servizio", test_service_commands),
        ("Windows Service Wrapper", test_windows_service_wrapper),
        ("Esecuzione Diretta", test_direct_execution)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Esecuzione test: {test_name}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test {test_name} fallito con eccezione: {e}")
            results[test_name] = False
    
    # Riepilogo
    logger.info("\n" + "=" * 60)
    logger.info("RIEPILOGO TEST")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    logger.info(f"\nRisultato finale: {passed}/{total} test passati")
    
    if passed == total:
        logger.info("🎉 Tutti i test sono passati!")
    else:
        logger.warning("⚠️ Alcuni test sono falliti. Controlla i log sopra.")
    
    logger.info(f"\nLog completo salvato in: debug_service.log")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main()) 