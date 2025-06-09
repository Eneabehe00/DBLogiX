#!/usr/bin/env python
"""
Script di setup per DBLogiX
Verifica l'ambiente e inizializza il database se necessario
"""
import os
import sys
import logging
import pymysql
import importlib.util

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("setup")

def check_python_version():
    """Verifica la versione di Python"""
    print("\n=== Verifica versione Python ===")
    python_version = sys.version.split()[0]
    print(f"Versione Python in uso: {python_version}")
    
    major, minor, *_ = map(int, python_version.split("."))
    if (major == 3 and minor >= 8 and minor <= 11):
        print("✓ Versione Python compatibile (3.8-3.11)")
        return True
    else:
        print("⚠ Versione Python non ottimale. Le versioni consigliate sono 3.8-3.11")
        if major == 3 and minor >= 12:
            print("  Potrebbero verificarsi problemi di compatibilità con alcune librerie.")
        return False

def check_dependencies():
    """Verifica che le dipendenze siano installate"""
    print("\n=== Verifica dipendenze ===")
    
    required_packages = [
        "flask", "flask_sqlalchemy", "flask_login", "flask_wtf", 
        "pymysql", "werkzeug", "flask_migrate", "email_validator"
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✓ {package} installato")
        except ImportError:
            print(f"✗ {package} non trovato. Esegui: pip install -r requirements.txt")
            all_installed = False
    
    return all_installed

def test_db_connection():
    """Testa la connessione al database"""
    print("\n=== Test connessione database ===")
    try:
        # Import config without importing the whole app
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from app.config import REMOTE_DB_CONFIG
        
        # Create connection
        conn = pymysql.connect(
            host=REMOTE_DB_CONFIG['host'],
            user=REMOTE_DB_CONFIG['user'],
            password=REMOTE_DB_CONFIG['password'],
            database=REMOTE_DB_CONFIG['database'],
            port=REMOTE_DB_CONFIG['port'],
            connect_timeout=10,
        )
        
        # Test query
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 as test")
            result = cursor.fetchone()
            
        conn.close()
        
        if result and 'test' in result and result['test'] == 1:
            print(f"✓ Connessione al database riuscita: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}")
            return True
        else:
            print("✗ Test query non riuscito")
            return False
    except Exception as e:
        print(f"✗ Errore connessione database: {str(e)}")
        print(f"  Controlla i parametri in config.py:")
        print(f"  - Host: {REMOTE_DB_CONFIG.get('host', 'NON IMPOSTATO')}")
        print(f"  - Database: {REMOTE_DB_CONFIG.get('database', 'NON IMPOSTATO')}")
        print(f"  - User: {REMOTE_DB_CONFIG.get('user', 'NON IMPOSTATO')}")
        return False

def initialize_database():
    """Inizializza il database se necessario"""
    print("\n=== Inizializzazione database ===")
    
    try:
        os.environ['FLASK_APP'] = 'app.py'
        
        # Importa app and db
        from app import app
        from app.models import db
        
        # Crea le tabelle se non esistono
        with app.app_context():
            print("Creazione tabelle...")
            db.create_all()
            print("✓ Tabelle create con successo")
            
            # Verifica esistenza utenti
            from app.models import User
            if User.query.count() == 0:
                print("! Nessun utente trovato. Il primo utente registrato sarà l'amministratore.")
            else:
                print(f"✓ Trovati {User.query.count()} utenti nel database")
                
        return True
    except Exception as e:
        print(f"✗ Errore durante l'inizializzazione del database: {str(e)}")
        return False

def main():
    """Funzione principale di setup"""
    print("\n🔧 DBLogiX - Setup e Verifica 🔧")
    print("================================")
    
    # Verifica tutti i componenti
    python_ok = check_python_version()
    deps_ok = check_dependencies()
    db_ok = test_db_connection()
    
    if python_ok and deps_ok and db_ok:
        db_init = initialize_database()
        if db_init:
            print("\n✅ Setup completato con successo! ✅")
            print("\nPer avviare l'applicazione esegui:")
            print("python main.py")
        else:
            print("\n⚠ Setup completato con errori nell'inizializzazione del database ⚠")
    else:
        print("\n⚠ Setup incompleto. Risolvi i problemi segnalati prima di procedere. ⚠")

if __name__ == "__main__":
    main() 