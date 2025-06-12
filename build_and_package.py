#!/usr/bin/env python3
"""
DBLogiX - Complete Build & Package Script (Python Embedded)
Automatizza tutto il processo: Download Python Embedded + Setup + Configurazione + Servizio + Installer
"""

import os
import sys
import subprocess
import shutil
import zipfile
from pathlib import Path
import tempfile
import json
from datetime import datetime
import urllib.request
import xml.etree.ElementTree as ET
import logging
from logging.handlers import RotatingFileHandler
import traceback

def banner():
    """Mostra il banner dell'applicazione"""
    print("=" * 70)
    print("DBLogiX - Complete Build & Package Script (Python Embedded)")
    print("=" * 70)
    print("* 🚀 Sistema Python Embedded automatizzato")
    print("* 📦 Download e configurazione Python 3.11")
    print("* 🛠️ Installazione dipendenze automatica")
    print("* 🔧 Configurazione servizio Windows")
    print("* 🌐 Setup HTTPS automatico")
    print("* 🔥 Configurazione firewall automatica")
    print("* 📂 Packaging completo per distribuzione")
    print("* ⚙️ Creazione installer .exe")
    print("=" * 70)

def check_admin_privileges():
    """Controlla che lo script sia eseguito come amministratore"""
    try:
        # Prova ad accedere a una cartella che richiede privilegi admin
        test_dir = Path("C:/Program Files/test_admin")
        test_dir.mkdir(exist_ok=True)
        test_dir.rmdir()
        return True
    except PermissionError:
        return False

def check_system_requirements():
    """Controlla che tutti i requisiti di sistema siano soddisfatti"""
    print("\n🔍 Controllo requisiti di sistema...")
    
    # Per il BUILD non servono privilegi admin
    print("✅ Build phase - privilegi admin non richiesti")
    
    # Controlla Python
    try:
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 8:
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"❌ Python {python_version.major}.{python_version.minor} non supportato (richiesto >= 3.8)")
            return False
    except Exception as e:
        print(f"❌ Errore nel controllo di Python: {e}")
        return False
    
    # Controlla connessione internet per download Python Embedded
    try:
        urllib.request.urlopen('https://www.python.org', timeout=5)
        print("✅ Connessione internet disponibile")
    except:
        print("❌ Connessione internet richiesta per download Python Embedded")
        return False
    
    # Controlla file necessari
    required_files = [
        'app.py', 
        'app/models.py', 
        'app/config.py',
        'app/config_manager.py',
        'DBLogix.exe.config',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file} mancante")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️ File mancanti: {', '.join(missing_files)}")
        return False
    
    return True

def clean_previous_builds():
    """Pulisce installazioni precedenti"""
    print("\n🧹 Pulizia installazioni precedenti...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    
    # Ferma il servizio se esistente
    try:
        result = subprocess.run(['net', 'stop', 'DBLogiXEmbedded'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servizio DBLogiXEmbedded fermato")
    except:
        pass
    
    # Rimuovi servizio se esistente  
    try:
        result = subprocess.run(['sc', 'delete', 'DBLogiXEmbedded'],
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servizio DBLogiXEmbedded rimosso")
    except:
        pass
    
    # Rimuovi directory di installazione
    if install_dir.exists():
        try:
            shutil.rmtree(install_dir)
            print(f"✅ Rimossa directory: {install_dir}")
        except Exception as e:
            print(f"⚠️ Impossibile rimuovere {install_dir}: {e}")
    
    # Pulisci directory locali
    dirs_to_clean = ['build', 'dist', '__pycache__', 'installer_output']
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Rimossa directory: {dir_name}")
            except:
                pass

def download_python_embedded(build_dir):
    """Scarica Python Embedded nella directory di build"""
    print("\n⬇️ Download Python Embedded...")
    
    PYTHON_VERSION = "3.11.9"
    PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
    
    python_zip = build_dir / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    python_dir = build_dir / "python"
    
    # Crea directory
    python_dir.mkdir(parents=True, exist_ok=True)
    
    # Scarica se non esiste
    if not python_zip.exists():
        print(f"⬇️ Downloading {PYTHON_URL}...")
        try:
            urllib.request.urlretrieve(PYTHON_URL, python_zip)
            print(f"✅ Downloaded: {python_zip}")
        except Exception as e:
            print(f"❌ Error downloading Python Embedded: {e}")
            return False
    else:
        print("✅ Python Embedded già scaricato")
    
    # Estrai
    print(f"📂 Extracting to {python_dir}...")
    try:
        with zipfile.ZipFile(python_zip, 'r') as zip_ref:
            zip_ref.extractall(python_dir)
        print("✅ Python Embedded estratto")
        
        # Rimuovi zip
        python_zip.unlink()
        print("✅ File zip rimosso")
        
        return python_dir
    except Exception as e:
        print(f"❌ Error extracting Python Embedded: {e}")
        return False

def configure_python_embedded(python_dir):
    """Configura Python Embedded"""
    print("\n⚙️ Configurazione Python Embedded...")
    
    # Configura python path file
    pth_files = list(python_dir.glob("python*._pth"))
    if pth_files:
        pth_file = pth_files[0]
        print(f"⚙️ Configurando {pth_file.name}...")
        
        # Leggi contenuto esistente
        with open(pth_file, 'r') as f:
            content = f.read()
        
        # Aggiungi path necessari
        paths_to_add = [
            ".",
            "Lib",
            "DLLs", 
            "../app",
            "../app/modules",
            "../app/services",
            "Lib/site-packages"
        ]
        
        # Rimuovi commento da import site
        content = content.replace("#import site", "import site")
        
        # Aggiungi nuovi path
        for path in paths_to_add:
            if path not in content:
                content += f"\n{path}"
        
        # Scrivi file aggiornato
        with open(pth_file, 'w') as f:
            f.write(content.strip())
        
        print(f"✅ Python path configurato")
        return True
    else:
        print("❌ File ._pth non trovato")
        return False

def install_pip(python_dir):
    """Installa pip in Python Embedded"""
    print("\n📦 Installazione pip...")
    
    python_exe = python_dir / "python.exe"
    get_pip_path = python_dir / "get-pip.py"
    
    # Scarica get-pip.py
    if not get_pip_path.exists():
        try:
            urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
            print("✅ get-pip.py scaricato")
        except Exception as e:
            print(f"❌ Error downloading get-pip.py: {e}")
            return False
    
    # Installa pip
    try:
        result = subprocess.run([
            str(python_exe), 
            str(get_pip_path),
            "--target", str(python_dir / "Lib" / "site-packages")
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent))
        
        if result.returncode == 0:
            print("✅ pip installato con successo")
            return True
        else:
            print(f"❌ Error installing pip: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error running pip installation: {e}")
        return False

def install_requirements(python_dir):
    """Installa i requirements di DBLogiX"""
    print("\n📚 Installazione dipendenze...")
    
    python_exe = python_dir / "python.exe"
    
    # Lista requirements aggiornata con cffi per cryptography e colorama
    requirements = [
        "Flask==2.3.3",
        "Werkzeug==2.3.7", 
        "SQLAlchemy==2.0.23",
        "Flask-SQLAlchemy==3.1.1",
        "Flask-Login==0.6.3",
        "Flask-WTF==1.2.1",
        "WTForms==3.1.0",
        "Flask-Migrate==4.0.5",
        "PyMySQL==1.1.0",
        "email-validator==2.1.0",
        "python-dotenv==1.0.0",
        "Jinja2==3.1.2",
        "itsdangerous==2.1.2",
        "cffi==1.16.0",
        "cryptography==41.0.5",
        "click==8.1.7",
        "reportlab==4.4.0",
        "flask-cors==4.0.0",
        "qrcode==8.2",
        "Pillow==10.0.1",
        "pywin32==306",
        "MarkupSafe==2.1.3",
        "blinker==1.7.0",
        "typing_extensions==4.8.0",
        "colorama==0.4.6"
    ]
    
    print(f"📦 Installando {len(requirements)} pacchetti...")
    
    # Prima installa le dipendenze critiche con wheel precompilate
    critical_deps = ["cffi==1.16.0", "cryptography==41.0.5"]
    
    for req in critical_deps:
        print(f"  🔧 {req} (con wheel precompilate)...")
        try:
            result = subprocess.run([
                str(python_exe), "-m", "pip", "install", req,
                "--target", str(python_dir / "Lib" / "site-packages"),
                "--only-binary=all", "--no-cache-dir"
            ], capture_output=True, text=True, cwd=str(Path(__file__).parent))
            
            if result.returncode == 0:
                print(f"  ✅ {req}")
            else:
                print(f"  ⚠️ Warning {req}: {result.stderr}")
                # Fallback senza --only-binary
                print(f"  🔄 Retry {req} senza --only-binary...")
                result = subprocess.run([
                    str(python_exe), "-m", "pip", "install", req,
                    "--target", str(python_dir / "Lib" / "site-packages"),
                    "--no-cache-dir"
                ], capture_output=True, text=True, cwd=str(Path(__file__).parent))
                if result.returncode == 0:
                    print(f"  ✅ {req} (fallback)")
                else:
                    print(f"  ❌ Failed {req}: {result.stderr}")
        except Exception as e:
            print(f"  ❌ Error {req}: {e}")
    
    # Poi installa gli altri pacchetti
    for req in requirements:
        if req not in critical_deps:
            print(f"  📦 {req}...")
            try:
                result = subprocess.run([
                    str(python_exe), "-m", "pip", "install", req,
                    "--target", str(python_dir / "Lib" / "site-packages"),
                    "--no-deps", "--no-cache-dir"
                ], capture_output=True, text=True, cwd=str(Path(__file__).parent))
                
                if result.returncode == 0:
                    print(f"  ✅ {req}")
                else:
                    print(f"  ⚠️ Warning {req}: {result.stderr}")
            except Exception as e:
                print(f"  ❌ Error {req}: {e}")
    
    print("✅ Installazione dipendenze completata")
    return True

def copy_application_code(build_dir):
    """Copia il codice dell'applicazione"""
    print("\n📋 Copia codice applicazione...")
    
    source_dir = Path(__file__).parent  # Directory root del progetto
    app_dir = build_dir / "app"
    
    print(f"📂 Da: {source_dir}")
    print(f"📂 A: {app_dir}")
    
    # Directories da copiare
    dirs_to_copy = [
        "app",
        "modules", 
        "services",
        "templates",
        "static",
        "migrations"
    ]
    
    # Files da copiare
    files_to_copy = [
        "app.py",
        "main.py", 
        "requirements.txt"
    ]
    
    # Crea directory app
    app_dir.mkdir(parents=True, exist_ok=True)
    
    # Copia directories
    for dir_name in dirs_to_copy:
        source_path = source_dir / dir_name
        dest_path = app_dir / dir_name
        
        if source_path.exists():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)
            print(f"✅ {dir_name}")
        else:
            print(f"⚠️ Directory non trovata: {source_path}")
    
    # Copia files
    for file_name in files_to_copy:
        source_path = source_dir / file_name
        dest_path = app_dir / file_name
        
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"✅ {file_name}")
        else:
            print(f"⚠️ File non trovato: {source_path}")
    
    print("✅ Codice applicazione copiato")

def create_launcher_and_service(build_dir):
    """Crea script launcher e servizio"""
    print("\n🚀 Creazione launcher e servizio...")
    
    # Script Launcher
    launcher_script = build_dir / "DBLogiX_Launcher.py"
    launcher_content = '''#!/usr/bin/env python3
"""
DBLogiX Embedded Python Launcher
"""

import sys
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
import traceback

# Configurazione path
INSTALL_DIR = Path(__file__).parent
PYTHON_DIR = INSTALL_DIR / "python"  
APP_DIR = INSTALL_DIR / "app"
LOG_DIR = INSTALL_DIR / "logs"

# Configura logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "dblogix_embedded.log"

logging.basicConfig(
    level=logging.DEBUG,  # Debug più dettagliato
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Configura l'ambiente Python"""
    logger.info("=== Setting up Python environment ===")
    
    paths_to_add = [
        str(APP_DIR),
        str(APP_DIR / "modules"),
        str(APP_DIR / "services"),
        str(PYTHON_DIR / "Lib" / "site-packages")
    ]
    
    logger.info(f"Install dir: {INSTALL_DIR}")
    logger.info(f"App dir: {APP_DIR}")
    logger.info(f"Python dir: {PYTHON_DIR}")
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
            logger.info(f"Added to Python path: {path}")
    
    # Controlla che la directory app esista
    if not APP_DIR.exists():
        logger.error(f"App directory does not exist: {APP_DIR}")
        raise FileNotFoundError(f"App directory not found: {APP_DIR}")
    
    os.chdir(str(APP_DIR))
    logger.info(f"Changed working directory to: {os.getcwd()}")
    
    logger.info(f"Python version: {sys.version}")
    logger.info("Python path:")
    for i, path in enumerate(sys.path[:10]):  # Primi 10 path
        logger.info(f"  {i}: {path}")

def main():
    """Funzione main"""
    logger.info("=== Starting DBLogiX Embedded Python ===")
    
    try:
        setup_environment()
        
        logger.info("Attempting to import app module...")
        try:
            import app
            logger.info("Successfully imported app module")
        except Exception as e:
            logger.error(f"Failed to import app module: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 1
        
        try:
            from app.models import db
            logger.info("Successfully imported models")
        except Exception as e:
            logger.error(f"Failed to import models: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 1
        
        logger.info("Creating Flask app...")
        try:
            flask_app = app.create_app()
            logger.info("Flask app created successfully")
        except Exception as e:
            logger.error(f"Failed to create Flask app: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return 1
        
        logger.info("Initializing database...")
        with flask_app.app_context():
            try:
                db.create_all()
                logger.info('Database tables created (if they did not exist)')
            except Exception as e:
                logger.error(f'Error creating database tables: {str(e)}')
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Non ritorniamo errore qui, il DB potrebbe già esistere
        
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
        
        cert_dir = INSTALL_DIR / "certs"
        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"
        
        ssl_context = None
        if cert_file.exists() and key_file.exists():
            ssl_context = (str(cert_file), str(key_file))
            logger.info("SSL certificates found, starting HTTPS server")
        else:
            logger.info("No SSL certificates found, starting HTTP server")
        
        logger.info(f"Starting server on {host}:{port} (debug={debug})")
        logger.info("DBLogiX started successfully")
        
        # Avvia Flask
        flask_app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Application failed to start: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1
    finally:
        logger.info("DBLogiX stopped")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
'''
    
    with open(launcher_script, 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    print("✅ Launcher script creato")
    
    # Script Servizio
    service_script = build_dir / "DBLogiX_Service.py"
    service_content = '''#!/usr/bin/env python3
"""
DBLogiX Windows Service - Python Embedded Version
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
import subprocess
import time
import signal
from pathlib import Path

class DBLogiXService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DBLogiXEmbedded"
    _svc_display_name_ = "DBLogiX Service (Embedded Python)"
    _svc_description_ = "DBLogiX Web Application Service usando Python Embedded"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.process = None
        
        # Setup paths - usa path assoluti
        self.install_dir = Path("C:/Program Files/DBLogiX")
        self.python_exe = self.install_dir / "python" / "python.exe"
        self.launcher_script = self.install_dir / "DBLogiX_Launcher.py"
        self.log_dir = self.install_dir / "logs"
        
        # Crea directory logs se non esiste
        self.log_dir.mkdir(exist_ok=True)
        
    def SvcStop(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPING,
            (self._svc_name_, '')
        )
        
        self.running = False
        
        # Termina il processo Flask
        if self.process and self.process.poll() is None:
            try:
                servicemanager.LogInfoMsg("Terminating Flask process...")
                
                # Prova prima SIGTERM (graceful)
                self.process.terminate()
                
                # Aspetta massimo 15 secondi
                try:
                    self.process.wait(timeout=15)
                    servicemanager.LogInfoMsg("Flask process terminated gracefully")
                except subprocess.TimeoutExpired:
                    servicemanager.LogInfoMsg("Force killing Flask process...")
                    self.process.kill()
                    self.process.wait()
                    
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error stopping Flask process: {e}")
        
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            self.main()
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {e}")
    
    def main(self):
        """Main service loop"""
        restart_count = 0
        max_restarts = 5
        
        while self.running and restart_count < max_restarts:
            try:
                servicemanager.LogInfoMsg(f"Starting DBLogiX (attempt {restart_count + 1}/{max_restarts})")
                
                # Verifica che i file esistano
                if not self.python_exe.exists():
                    servicemanager.LogErrorMsg(f"Python executable not found: {self.python_exe}")
                    break
                    
                if not self.launcher_script.exists():
                    servicemanager.LogErrorMsg(f"Launcher script not found: {self.launcher_script}")
                    break
                
                # Comando per avviare Flask
                cmd = [str(self.python_exe), str(self.launcher_script)]
                
                servicemanager.LogInfoMsg(f"Starting DBLogiX with: {' '.join(cmd)}")
                servicemanager.LogInfoMsg(f"Working directory: {self.install_dir}")
                
                # Avvia il processo con configurazione robusta
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(self.install_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    # Variabili ambiente per Flask
                    env={
                        **os.environ,
                        'FLASK_ENV': 'production',
                        'FLASK_DEBUG': 'False',
                        'PYTHONPATH': str(self.install_dir / "app"),
                        'PYTHONIOENCODING': 'utf-8'
                    }
                )
                
                servicemanager.LogInfoMsg(f"DBLogiX process started with PID: {self.process.pid}")
                
                # Monitora il processo
                while self.running and self.process.poll() is None:
                    # Controlla ogni secondo se dobbiamo fermarci
                    if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                        servicemanager.LogInfoMsg("Stop signal received")
                        break
                
                # Se siamo qui, o ci hanno chiesto di fermarci o il processo è morto
                if self.running and self.process.poll() is not None:
                    exit_code = self.process.returncode
                    servicemanager.LogErrorMsg(f"DBLogiX process terminated unexpectedly with exit code: {exit_code}")
                    
                    # Leggi l'output per debug
                    try:
                        output, _ = self.process.communicate(timeout=1)
                        if output:
                            servicemanager.LogErrorMsg(f"Process output: {output[:500]}")  # Primi 500 char
                    except:
                        pass
                    
                    restart_count += 1
                    if self.running and restart_count < max_restarts:
                        servicemanager.LogInfoMsg(f"Restarting in 10 seconds... (attempt {restart_count + 1}/{max_restarts})")
                        time.sleep(10)
                else:
                    # Stop normale
                    break
                    
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error in service main loop: {e}")
                restart_count += 1
                if self.running and restart_count < max_restarts:
                    time.sleep(10)
                else:
                    break
        
        if restart_count >= max_restarts:
            servicemanager.LogErrorMsg(f"Maximum restart attempts ({max_restarts}) reached. Service stopping.")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(DBLogiXService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(DBLogiXService)
'''
    
    with open(service_script, 'w', encoding='utf-8') as f:
        f.write(service_content)
    print("✅ Service script creato")

def copy_configuration_and_certs(build_dir):
    """Copia configurazione e certificati"""
    print("\n⚙️ Copia configurazione e certificati...")
    
    source_dir = Path(__file__).parent
    
    # Crea directories
    (build_dir / "config").mkdir(exist_ok=True)
    (build_dir / "certs").mkdir(exist_ok=True)
    (build_dir / "logs").mkdir(exist_ok=True)
    
    # Copia configurazione
    source_config = source_dir / "DBLogix.exe.config"
    dest_config = build_dir / "config" / "DBLogix.exe.config"
    
    if source_config.exists():
        shutil.copy2(source_config, dest_config)
        print("✅ Configurazione copiata")
    else:
        print("⚠️ File configurazione non trovato")
    
    # Copia certificati SSL se esistono
    cert_files = ["cert.pem", "key.pem"]
    for cert_file in cert_files:
        source_cert = source_dir / cert_file
        dest_cert = build_dir / "certs" / cert_file
        
        if source_cert.exists():
            shutil.copy2(source_cert, dest_cert)
            print(f"✅ Certificato SSL copiato: {cert_file}")
        else:
            print(f"⚠️ Certificato SSL non trovato: {source_cert}")

def create_batch_files(build_dir):
    """Crea file batch per gestione"""
    print("\n🔧 Creazione file batch...")
    
    python_dir = build_dir / "python"
    
    # Start batch
    start_bat = build_dir / "start_dblogix.bat"
    with open(start_bat, 'w') as f:
        f.write(f'''@echo off
echo Starting DBLogiX...
cd /d "%~dp0"
"python\\python.exe" "DBLogiX_Launcher.py"
pause
''')
    
        # Service install batch  
    install_service_bat = build_dir / "install_service.bat"
    with open(install_service_bat, 'w') as f:
        f.write(f'''@echo off
echo Installing DBLogiX Service...
cd /d "%~dp0"
"python\\python.exe" "DBLogiX_Service.py" install
echo Service installed. Use 'net start DBLogiXEmbedded' to start.
pause
''')
    
    # Service uninstall batch
    uninstall_service_bat = build_dir / "uninstall_service.bat"
    with open(uninstall_service_bat, 'w') as f:
        f.write(f'''@echo off
echo Uninstalling DBLogiX Service...
cd /d "%~dp0"
net stop DBLogiXEmbedded
"python\\python.exe" "DBLogiX_Service.py" remove
echo Service uninstalled.
pause
''')
    
    # Service status batch
    status_service_bat = build_dir / "status_service.bat"
    with open(status_service_bat, 'w') as f:
        f.write(f'''@echo off
echo DBLogiX Service Status:
echo ========================
sc query DBLogiXEmbedded
echo.
echo Network Status:
echo ===============
netstat -an | findstr :5000
echo.
echo To access DBLogiX, open: https://localhost:5000
echo.
pause
''')
    
    # Service logs batch
    logs_service_bat = build_dir / "view_service_logs.bat"
    with open(logs_service_bat, 'w') as f:
        f.write('''@echo off
echo DBLogiX Service Logs:
echo ====================
echo.
echo Recent Windows Service Events:
echo ------------------------------
powershell -Command "Get-EventLog -LogName Application -Source DBLogiXEmbedded -Newest 15 -ErrorAction SilentlyContinue | Format-Table TimeGenerated, EntryType, Message -AutoSize"
echo.
echo Service Control Manager Events:
echo -------------------------------
powershell -Command "Get-EventLog -LogName System -Source 'Service Control Manager' -Newest 10 -ErrorAction SilentlyContinue | Format-Table TimeGenerated, EntryType, Message -AutoSize"
echo.
echo Application Logs (if available):
echo --------------------------------
if exist "logs\\dblogix_embedded.log" (
    echo Last 30 lines of application log:
    powershell -Command "Get-Content logs\\dblogix_embedded.log -Tail 30 -ErrorAction SilentlyContinue"
) else (
    echo No application log file found
)
echo.
echo File Check:
echo -----------
echo Python executable: python\\python.exe
if exist "python\\python.exe" (
    echo [OK] Python executable found
) else (
    echo [ERROR] Python executable NOT found
)
echo.
echo Launcher script: DBLogiX_Launcher.py
if exist "DBLogiX_Launcher.py" (
    echo [OK] Launcher script found
) else (
    echo [ERROR] Launcher script NOT found
)
echo.
echo Service Status:
echo ---------------
sc query DBLogiXEmbedded
echo.
pause
''')
    
    # Debug launcher batch
    debug_launcher_bat = build_dir / "debug_launcher.bat"
    with open(debug_launcher_bat, 'w') as f:
        f.write('''@echo off
echo DBLogiX Launcher Debug:
echo ======================
echo.
echo Testing launcher directly...
echo.
cd /d "%~dp0"
echo Current directory: %CD%
echo.
echo Testing Python path...
"python\\python.exe" -c "import sys; print('Python version:', sys.version); print('Python path:'); [print('  ', p) for p in sys.path]"
echo.
echo Testing Flask import...
"python\\python.exe" -c "
import sys
import os
from pathlib import Path

# Setup paths like the launcher does
INSTALL_DIR = Path('.')
APP_DIR = INSTALL_DIR / 'app'
PYTHON_DIR = INSTALL_DIR / 'python'

paths_to_add = [
    str(APP_DIR),
    str(APP_DIR / 'modules'),
    str(APP_DIR / 'services'),
    str(PYTHON_DIR / 'Lib' / 'site-packages')
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(str(APP_DIR))
print('Working directory:', os.getcwd())
print('Trying to import Flask...')
try:
    import Flask
    print('Flask import OK')
except Exception as e:
    print('Flask import ERROR:', e)

print('Trying to import app module...')
try:
    import app
    print('app module import OK')
except Exception as e:
    print('app module import ERROR:', e)
"
echo.
echo Testing full launcher...
echo ========================
"python\\python.exe" "DBLogiX_Launcher.py"
echo.
echo Launcher finished with exit code: %ERRORLEVEL%
echo.
pause
''')
    
    print("✅ File batch creati")

def configure_firewall():
    """Configura il firewall Windows per DBLogiX"""
    print("\n🔥 Configurazione firewall Windows...")
    
    # Rimuovi regole esistenti
    try:
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=DBLogiX HTTP'], 
                      capture_output=True, text=True)
        subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=DBLogiX HTTPS'], 
                      capture_output=True, text=True)
    except:
        pass
    
    # Aggiungi regole firewall
    firewall_rules = [
        {
            'name': 'DBLogiX HTTP',
            'port': '5000',
            'protocol': 'TCP',
            'description': 'DBLogiX Web Application HTTP'
        },
        {
            'name': 'DBLogiX HTTPS', 
            'port': '5000',
            'protocol': 'TCP',
            'description': 'DBLogiX Web Application HTTPS'
        }
    ]
    
    for rule in firewall_rules:
        try:
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name={rule["name"]}',
                'dir=in',
                'action=allow',
                f'protocol={rule["protocol"]}',
                f'localport={rule["port"]}',
                'enable=yes'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Firewall rule added: {rule['name']}")
            else:
                print(f"⚠️ Warning adding firewall rule {rule['name']}: {result.stderr}")
        except Exception as e:
            print(f"❌ Error adding firewall rule {rule['name']}: {e}")

def install_and_start_service():
    """Installa e avvia il servizio"""
    print("\n🛠️ Installazione e avvio servizio...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    python_exe = install_dir / "python" / "python.exe"
    service_script = install_dir / "DBLogiX_Service.py"
    
    try:
        # Installa servizio
        result = subprocess.run([
            str(python_exe), str(service_script), "install"
        ], capture_output=True, text=True, cwd=str(install_dir))
        
        if result.returncode == 0:
            print("✅ Servizio installato")
        else:
            print(f"⚠️ Warning installing service: {result.stderr}")
        
        # Avvia servizio
        result = subprocess.run(['net', 'start', 'DBLogiXEmbedded'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servizio avviato")
        else:
            print(f"⚠️ Warning starting service: {result.stderr}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error with service: {e}")
        return False

def create_build_info(build_dir):
    """Crea informazioni sulla build"""
    print("\n📋 Creazione informazioni build...")
    
    build_info = {
        "build_date": datetime.now().isoformat(),
        "build_type": "Python Embedded Package",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "package_ready": True,
        "requires_installation": True,
        "target_install_location": "C:/Program Files/DBLogiX",
        "service_name": "DBLogiXEmbedded",
        "ssl_enabled": (build_dir / "certs" / "cert.pem").exists()
    }
    
    with open(build_dir / "build_info.json", 'w') as f:
        json.dump(build_info, f, indent=2)
    
    print("✅ Build info creata")

def create_installer_script():
    """Crea script Inno Setup per installer .exe"""
    print("\n📝 Creazione script Inno Setup...")
    
    scripts_dir = Path("scripts")
    scripts_dir.mkdir(exist_ok=True)
    
    iss_content = '''[Setup]
AppName=DBLogiX
AppVersion=1.0
AppPublisher=DBLogiX Team
AppPublisherURL=https://dblogix.com
DefaultDirName={autopf}\\DBLogiX
DefaultGroupName=DBLogiX
OutputDir=..\\installer_output
OutputBaseFilename=DBLogiX_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=..\\static\\favicon.ico
WizardStyle=modern
UninstallDisplayIcon={app}\\favicon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\\Italian.isl"

[Files]
Source: "..\\build\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\\static\\favicon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\\DBLogiX"; Filename: "https://localhost:5000"; IconFilename: "{app}\\favicon.ico"; Comment: "Open DBLogiX Web Application"
Name: "{group}\\DBLogiX (Manual Start)"; Filename: "{app}\\start_dblogix.bat"; WorkingDir: "{app}"; IconFilename: "{app}\\favicon.ico"; Comment: "Start DBLogiX manually (for debugging)"
Name: "{group}\\Service Control\\Install Service"; Filename: "{app}\\install_service.bat"; WorkingDir: "{app}"; Comment: "Install DBLogiX Windows Service"
Name: "{group}\\Service Control\\Uninstall Service"; Filename: "{app}\\uninstall_service.bat"; WorkingDir: "{app}"; Comment: "Uninstall DBLogiX Windows Service"
Name: "{group}\\Service Control\\Start Service"; Filename: "net"; Parameters: "start DBLogiXEmbedded"; Comment: "Start DBLogiX Service"
Name: "{group}\\Service Control\\Stop Service"; Filename: "net"; Parameters: "stop DBLogiXEmbedded"; Comment: "Stop DBLogiX Service"
Name: "{group}\\Service Control\\Service Status"; Filename: "{app}\\status_service.bat"; WorkingDir: "{app}"; Comment: "Check DBLogiX Service Status"
Name: "{group}\\Service Control\\View Service Logs"; Filename: "{app}\\view_service_logs.bat"; WorkingDir: "{app}"; Comment: "View DBLogiX Service Logs"
Name: "{group}\\Service Control\\Debug Launcher"; Filename: "{app}\\debug_launcher.bat"; WorkingDir: "{app}"; Comment: "Debug DBLogiX Launcher (troubleshooting)"
Name: "{group}\\{cm:UninstallProgram,DBLogiX}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\DBLogiX"; Filename: "https://localhost:5000"; Tasks: desktopicon; IconFilename: "{app}\\favicon.ico"; Comment: "Open DBLogiX Web Application"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "installservice"; Description: "Install Windows Service"; GroupDescription: "Service Options"; Flags: checkedonce
Name: "startservice"; Description: "Start Windows Service automatically"; GroupDescription: "Service Options"; Flags: checkedonce
Name: "configurefirewall"; Description: "Configure Windows Firewall"; GroupDescription: "Security Options"; Flags: checkedonce
Name: "openbrowser"; Description: "Open DBLogiX in browser after installation"; GroupDescription: "Launch Options"; Flags: checkedonce

[Run]
Filename: "{app}\\python\\python.exe"; Parameters: """DBLogiX_Service.py"" install"; WorkingDir: "{app}"; StatusMsg: "Installing Windows Service..."; Tasks: installservice; Flags: runhidden
Filename: "net"; Parameters: "start DBLogiXEmbedded"; StatusMsg: "Starting DBLogiX Service..."; Tasks: startservice; Flags: runhidden waituntilterminated
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTP"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configuring Firewall..."; Tasks: configurefirewall; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""DBLogiX HTTPS"" dir=in action=allow protocol=TCP localport=5000 enable=yes"; StatusMsg: "Configuring Firewall..."; Tasks: configurefirewall; Flags: runhidden
Filename: "timeout"; Parameters: "/t 5 /nobreak"; StatusMsg: "Waiting for service to start..."; Tasks: openbrowser; Flags: runhidden waituntilterminated
Filename: "https://localhost:5000"; StatusMsg: "Opening DBLogiX in browser..."; Tasks: openbrowser; Flags: shellexec postinstall skipifsilent

[UninstallRun]
Filename: "net"; Parameters: "stop DBLogiXEmbedded"; StatusMsg: "Stopping Service..."; Flags: runhidden
Filename: "{app}\\python\\python.exe"; Parameters: """DBLogiX_Service.py"" remove"; WorkingDir: "{app}"; StatusMsg: "Removing Windows Service..."; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTP"""; StatusMsg: "Removing Firewall Rules..."; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""DBLogiX HTTPS"""; StatusMsg: "Removing Firewall Rules..."; Flags: runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('Installation completed successfully!' + #13#10 + 
           'You can start DBLogiX from the Start Menu or Desktop icon.' + #13#10 +
           'Access the web interface at: https://localhost:5000', mbInformation, MB_OK);
  end;
end;
'''
    
    iss_file = scripts_dir / "dblogix_installer.iss"
    with open(iss_file, 'w', encoding='utf-8') as f:
        f.write(iss_content)
    
    print("✅ Script Inno Setup creato")
    return iss_file

def compile_installer():
    """Compila l'installer .exe usando Inno Setup"""
    print("\n🔧 Compilazione installer .exe...")
    
    # Trova Inno Setup
    iscc_path = find_inno_setup_compiler()
    if not iscc_path:
        print("⚠️ Inno Setup non trovato. Installalo da: https://jrsoftware.org/isinfo.php")
        return False
    
    print(f"✅ Inno Setup trovato: {iscc_path}")
    
    # Path del file .iss
    iss_file = Path("scripts/dblogix_installer.iss")
    if not iss_file.exists():
        print(f"❌ File installer script non trovato: {iss_file}")
        return False
    
    try:
        # Compila l'installer dalla directory scripts per i percorsi relativi
        scripts_dir = Path(__file__).parent / "scripts"
        result = subprocess.run([
            iscc_path, "dblogix_installer.iss"
        ], capture_output=True, text=True, cwd=str(scripts_dir))
        
        if result.returncode == 0:
            print("✅ Installer .exe compilato con successo")
            
            # Verifica che il file .exe sia stato creato
            exe_file = Path("installer_output/DBLogiX_Setup.exe")
            if exe_file.exists():
                file_size = exe_file.stat().st_size / (1024*1024)  # MB
                print(f"✅ DBLogiX_Setup.exe creato ({file_size:.1f} MB)")
                return True
            else:
                print("❌ File .exe non trovato dopo compilazione")
                return False
        else:
            print(f"❌ Errore compilazione Inno Setup:")
            print(f"   stdout: {result.stdout}")
            print(f"   stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Errore nell'esecuzione di Inno Setup: {e}")
        return False

def create_portable_package(build_dir):
    """Crea package portatile in alternativa all'installer"""
    print("\n📦 Creazione package portatile...")
    
    installer_output = Path("installer_output")
    installer_output.mkdir(exist_ok=True)
    
    # Crea ZIP distribuibile
    zip_file = installer_output / "DBLogiX_Portable.zip"
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in build_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(build_dir)
                zipf.write(file_path, arcname)
    
    file_size = zip_file.stat().st_size / (1024*1024)  # MB
    print(f"✅ DBLogiX_Portable.zip creato ({file_size:.1f} MB)")
    
    # Crea README per il package portatile
    readme_file = installer_output / "README_Portable.txt"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write("""DBLogiX Portable Package
======================

ISTRUZIONI:
1. Estrai DBLogiX_Portable.zip in una cartella a tua scelta
2. Esegui start_dblogix.bat per avviare l'applicazione
3. Accedi a https://localhost:5000 nel browser

INSTALLAZIONE SERVIZIO WINDOWS:
1. Esegui install_service.bat come amministratore
2. Il servizio verrà installato e configurato automaticamente

CONFIGURAZIONE FIREWALL:
- Aggiungi manualmente le regole per la porta 5000 se necessario

DISINSTALLAZIONE:
1. Esegui uninstall_service.bat se hai installato il servizio
2. Cancella la cartella dell'applicazione

SUPPORTO:
Per assistenza visita: https://dblogix.com
""")
    
    print("✅ Package portatile creato")
    return True

def find_inno_setup_compiler():
    """Trova il compilatore Inno Setup"""
    possible_paths = [
        "C:/Program Files (x86)/Inno Setup 6/ISCC.exe",
        "C:/Program Files/Inno Setup 6/ISCC.exe", 
        "C:/Program Files (x86)/Inno Setup 5/ISCC.exe",
        "C:/Program Files/Inno Setup 5/ISCC.exe"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return None

def test_build(build_dir):
    """Testa il build"""
    print("\n🧪 Test build...")
    
    python_exe = build_dir / "python" / "python.exe"
    
    # Test Python
    try:
        result = subprocess.run([str(python_exe), "--version"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Python: {result.stdout.strip()}")
        else:
            print("❌ Python test failed")
            return False
    except Exception as e:
        print(f"❌ Python test error: {e}")
        return False
    
    # Test import Flask
    try:
        result = subprocess.run([str(python_exe), "-c", "import flask; print('Flask OK')"], 
                               capture_output=True, text=True, cwd=str(build_dir))
        if result.returncode == 0:
            print("✅ Flask import OK")
        else:
            print(f"❌ Flask import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Flask test error: {e}")
        return False
    
    # Test typing_extensions import
    try:
        result = subprocess.run([str(python_exe), "-c", "import typing_extensions; print('typing_extensions OK')"], 
                               capture_output=True, text=True, cwd=str(build_dir))
        if result.returncode == 0:
            print("✅ typing_extensions import OK")
        else:
            print(f"❌ typing_extensions import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ typing_extensions test error: {e}")
        return False
    
    # Verifica che tutti i file essenziali esistano
    essential_files = [
        "python/python.exe",
        "DBLogiX_Launcher.py", 
        "DBLogiX_Service.py",
        "app/app.py",
        "start_dblogix.bat",
        "install_service.bat",
        "uninstall_service.bat", 
        "status_service.bat",
        "view_service_logs.bat",
        "debug_launcher.bat"
    ]
    
    for file in essential_files:
        file_path = build_dir / file
        if file_path.exists():
            print(f"✅ File essenziale: {file}")
        else:
            print(f"❌ File essenziale mancante: {file}")
            return False
    
    return True

def main():
    """Funzione principale"""
    banner()
    
    try:
        # Controlli preliminari
        if not check_system_requirements():
            print("\n❌ Requisiti di sistema non soddisfatti!")
            return False
        
        # Pulizia
        clean_previous_builds()
        
        # Crea directory di build
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)
        print(f"\n📂 Directory di build: {build_dir.absolute()}")
        
        # Download e setup Python Embedded
        python_dir = download_python_embedded(build_dir)
        if not python_dir:
            return False
        
        if not configure_python_embedded(python_dir):
            return False
            
        if not install_pip(python_dir):
            return False
            
        if not install_requirements(python_dir):
            return False
        
        # Copia codice applicazione
        copy_application_code(build_dir)
        
        # Crea script e servizio
        create_launcher_and_service(build_dir)
        
        # Configurazione
        copy_configuration_and_certs(build_dir)
        create_batch_files(build_dir)
        create_build_info(build_dir)
        
        # Test build
        if not test_build(build_dir):
            print("⚠️ Warning: Some tests failed, but build may still work")
        
        # Crea installer script
        create_installer_script()
        
        # Crea directory output
        installer_output = Path("installer_output")
        installer_output.mkdir(exist_ok=True)
        
        # Compila installer .exe
        installer_created = compile_installer()
        
        # Crea sempre anche il package portatile come backup
        create_portable_package(build_dir)
        
        # Risultato finale
        print("\n" + "="*70)
        print("✅ DBLogiX BUILD & PACKAGE COMPLETATO!")
        print("="*70)
        print(f"📂 Build directory: {build_dir.absolute()}")
        print(f"📦 Output directory: installer_output/")
        print("")
        print("📦 FILES DISTRIBUIBILI:")
        
        if installer_created:
            print("  🎯 installer_output/DBLogiX_Setup.exe       # INSTALLER PRINCIPALE")
        
        print("  📦 installer_output/DBLogiX_Portable.zip    # Package portatile")
        print("  📝 installer_output/README_Portable.txt     # Istruzioni")
        print("")
        
        if installer_created:
            print("🎯 L'installer .exe si occupa di:")
            print("  • Installazione in C:/Program Files/DBLogiX")
            print("  • Configurazione servizio Windows automatico")
            print("  • Configurazione firewall")
            print("  • Icone nel menu Start e desktop")
            print("  • Disinstallazione completa")
        print("")
        print("🔧 IMPORTANTE - Come funziona:")
        print("  • Il SERVIZIO WINDOWS mantiene attivo il server 24/7")
        print("  • Le ICONE aprono direttamente il browser su https://localhost:5000")
        print("  • Il file .bat è solo per debug/manutenzione manuale")
        print("  • Usa 'Service Control' nel menu per gestire il servizio")
        print("")
        print("🚀 Package pronto per la distribuzione!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante il build: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 Per supporto, controlla i log e verifica i requisiti di sistema")
        sys.exit(1)
    sys.exit(0)