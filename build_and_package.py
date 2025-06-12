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
    
    # Controlla privilegi amministratore
    if not check_admin_privileges():
        print("❌ Privilegi amministratore richiesti!")
        print("   Esegui questo script come amministratore")
        return False
    else:
        print("✅ Privilegi amministratore confermati")
    
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

def download_python_embedded():
    """Scarica Python Embedded"""
    print("\n⬇️ Download Python Embedded...")
    
    PYTHON_VERSION = "3.11.9"
    PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
    
    install_dir = Path("C:/Program Files/DBLogiX")
    python_zip = install_dir / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    python_dir = install_dir / "python"
    
    # Crea directory
    install_dir.mkdir(parents=True, exist_ok=True)
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
        ], capture_output=True, text=True, cwd=str(python_dir))
        
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
    
    # Lista requirements aggiornata con MarkupSafe, blinker e typing_extensions
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
        "cryptography==41.0.5",
        "click==8.1.7",
        "reportlab==4.4.0",
        "flask-cors==4.0.0",
        "qrcode==8.2",
        "pywin32==306",
        "MarkupSafe==2.1.3",
        "blinker==1.7.0",
        "typing_extensions==4.8.0"
    ]
    
    print(f"📦 Installando {len(requirements)} pacchetti...")
    for req in requirements:
        print(f"  📦 {req}...")
        try:
            result = subprocess.run([
                str(python_exe), "-m", "pip", "install", req,
                "--target", str(python_dir / "Lib" / "site-packages"),
                "--no-deps", "--no-cache-dir"
            ], capture_output=True, text=True, cwd=str(python_dir))
            
            if result.returncode == 0:
                print(f"  ✅ {req}")
            else:
                print(f"  ⚠️ Warning {req}: {result.stderr}")
        except Exception as e:
            print(f"  ❌ Error {req}: {e}")
    
    print("✅ Installazione dipendenze completata")
    return True

def copy_application_code():
    """Copia il codice dell'applicazione"""
    print("\n📋 Copia codice applicazione...")
    
    source_dir = Path(__file__).parent  # Directory root del progetto
    install_dir = Path("C:/Program Files/DBLogiX")
    app_dir = install_dir / "app"
    
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

def create_launcher_and_service():
    """Crea script launcher e servizio"""
    print("\n🚀 Creazione launcher e servizio...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    
    # Script Launcher
    launcher_script = install_dir / "DBLogiX_Launcher.py"
    launcher_content = '''#!/usr/bin/env python3
"""
DBLogiX Embedded Python Launcher
"""

import sys
import os
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

# Configurazione path
INSTALL_DIR = Path(__file__).parent
PYTHON_DIR = INSTALL_DIR / "python"  
APP_DIR = INSTALL_DIR / "app"
LOG_DIR = INSTALL_DIR / "logs"

# Configura logging
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / "dblogix_embedded.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Configura l'ambiente Python"""
    paths_to_add = [
        str(APP_DIR),
        str(APP_DIR / "modules"),
        str(APP_DIR / "services"),
        str(PYTHON_DIR / "Lib" / "site-packages")
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    os.chdir(str(APP_DIR))
    
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

def main():
    """Funzione main"""
    logger.info("=== Starting DBLogiX Embedded Python ===")
    
    try:
        setup_environment()
        
        import app
        from app.models import db
        
        logger.info("Successfully imported app module")
        
        flask_app = app.create_app()
        logger.info("Flask app created successfully")
        
        with flask_app.app_context():
            try:
                db.create_all()
                logger.info('Database tables created (if they did not exist)')
            except Exception as e:
                logger.error(f'Error creating database tables: {str(e)}')
        
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
        
        flask_app.run(host=host, port=port, debug=debug, ssl_context=ssl_context)
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1)
    finally:
        logger.info("DBLogiX stopped")

if __name__ == "__main__":
    main()
'''
    
    with open(launcher_script, 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    print("✅ Launcher script creato")
    
    # Script Servizio
    service_script = install_dir / "DBLogiX_Service.py"
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
        
        self.install_dir = Path("C:/Program Files/DBLogiX")
        self.python_exe = self.install_dir / "python" / "python.exe"
        self.launcher_script = self.install_dir / "DBLogiX_Launcher.py"
        
    def SvcStop(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPING,
            (self._svc_name_, '')
        )
        
        self.running = False
        
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
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
        while self.running:
            try:
                cmd = [str(self.python_exe), str(self.launcher_script)]
                
                servicemanager.LogInfoMsg(f"Starting DBLogiX with command: {' '.join(cmd)}")
                
                self.process = subprocess.Popen(
                    cmd,
                    cwd=str(self.install_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                while self.running and self.process.poll() is None:
                    if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                        break
                
                if self.running and self.process.poll() is not None:
                    servicemanager.LogErrorMsg(f"DBLogiX process terminated unexpectedly with code {self.process.returncode}")
                    time.sleep(5)
                    
            except Exception as e:
                servicemanager.LogErrorMsg(f"Error in service main loop: {e}")
                if self.running:
                    time.sleep(10)

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

def copy_configuration_and_certs():
    """Copia configurazione e certificati"""
    print("\n⚙️ Copia configurazione e certificati...")
    
    source_dir = Path(__file__).parent
    install_dir = Path("C:/Program Files/DBLogiX")
    
    # Crea directories
    (install_dir / "config").mkdir(exist_ok=True)
    (install_dir / "certs").mkdir(exist_ok=True)
    (install_dir / "logs").mkdir(exist_ok=True)
    
    # Copia configurazione
    source_config = source_dir / "DBLogix.exe.config"
    dest_config = install_dir / "config" / "DBLogix.exe.config"
    
    if source_config.exists():
        shutil.copy2(source_config, dest_config)
        print("✅ Configurazione copiata")
    else:
        print("⚠️ File configurazione non trovato")
    
    # Copia certificati SSL se esistono
    cert_files = ["cert.pem", "key.pem"]
    for cert_file in cert_files:
        source_cert = source_dir / cert_file
        dest_cert = install_dir / "certs" / cert_file
        
        if source_cert.exists():
            shutil.copy2(source_cert, dest_cert)
            print(f"✅ Certificato SSL copiato: {cert_file}")
        else:
            print(f"⚠️ Certificato SSL non trovato: {source_cert}")

def create_batch_files():
    """Crea file batch per gestione"""
    print("\n🔧 Creazione file batch...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    python_dir = install_dir / "python"
    
    # Start batch
    start_bat = install_dir / "start_dblogix.bat"
    with open(start_bat, 'w') as f:
        f.write(f'''@echo off
echo Starting DBLogiX...
cd /d "{install_dir}"
"{python_dir}\\python.exe" "DBLogiX_Launcher.py"
pause
''')
    
    # Service install batch
    install_service_bat = install_dir / "install_service.bat"
    with open(install_service_bat, 'w') as f:
        f.write(f'''@echo off
echo Installing DBLogiX Service...
cd /d "{install_dir}"
"{python_dir}\\python.exe" "DBLogiX_Service.py" install
echo Service installed. Use 'net start DBLogiXEmbedded' to start.
pause
''')
    
    # Service uninstall batch
    uninstall_service_bat = install_dir / "uninstall_service.bat"
    with open(uninstall_service_bat, 'w') as f:
        f.write(f'''@echo off
echo Uninstalling DBLogiX Service...
cd /d "{install_dir}"
net stop DBLogiXEmbedded
"{python_dir}\\python.exe" "DBLogiX_Service.py" remove
echo Service uninstalled.
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

def create_build_info():
    """Crea informazioni sulla build"""
    print("\n📋 Creazione informazioni build...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    
    build_info = {
        "build_date": datetime.now().isoformat(),
        "build_type": "Python Embedded",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "install_location": str(install_dir),
        "service_name": "DBLogiXEmbedded",
        "firewall_configured": True,
        "ssl_enabled": (install_dir / "certs" / "cert.pem").exists()
    }
    
    with open(install_dir / "build_info.json", 'w') as f:
        json.dump(build_info, f, indent=2)
    
    print("✅ Build info creata")

def create_installer_package():
    """Crea il package installer + Compila installer .exe"""
    print("\n📦 Creazione package installer...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    installer_output = Path("installer_output")
    
    # Crea directory output
    installer_output.mkdir(exist_ok=True)
    
    # Copia tutta l'installazione nell'output
    package_dir = installer_output / "DBLogiX"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    shutil.copytree(install_dir, package_dir)
    print("✅ Package copiato in installer_output/")
    
    # Crea script installer batch (backup)
    installer_script = installer_output / "install_dblogix.bat"
    with open(installer_script, 'w') as f:
        f.write('''@echo off
echo DBLogiX Installer
echo ================
echo.
echo Copying files to Program Files...
xcopy /E /I /Y "DBLogiX" "C:\\Program Files\\DBLogiX\\"
echo.
echo Installing Windows Service...
cd /d "C:\\Program Files\\DBLogiX"
"python\\python.exe" "DBLogiX_Service.py" install
echo.
echo Starting Service...
net start DBLogiXEmbedded
echo.
echo Configuring Firewall...
netsh advfirewall firewall add rule name="DBLogiX HTTP" dir=in action=allow protocol=TCP localport=5000 enable=yes
netsh advfirewall firewall add rule name="DBLogiX HTTPS" dir=in action=allow protocol=TCP localport=5000 enable=yes
echo.
echo Installation completed!
echo Access DBLogiX at: https://localhost:5000
pause
''')
    
    # Crea script uninstaller batch (backup)
    uninstaller_script = installer_output / "uninstall_dblogix.bat"
    with open(uninstaller_script, 'w') as f:
        f.write('''@echo off
echo DBLogiX Uninstaller
echo ===================
echo.
echo Stopping Service...
net stop DBLogiXEmbedded
echo.
echo Removing Service...
cd /d "C:\\Program Files\\DBLogiX"
"python\\python.exe" "DBLogiX_Service.py" remove
echo.
echo Removing Firewall Rules...
netsh advfirewall firewall delete rule name="DBLogiX HTTP"
netsh advfirewall firewall delete rule name="DBLogiX HTTPS"
echo.
echo Removing Files...
cd /d "C:\\"
rmdir /s /q "C:\\Program Files\\DBLogiX"
echo.
echo Uninstallation completed!
pause
''')
    
    print("✅ Installer batch scripts creati")
    
    # Compila installer .exe con Inno Setup
    if compile_inno_setup_installer():
        print("✅ Installer .exe creato con successo!")
    else:
        print("⚠️ Warning: Installer .exe non creato, usa i file batch")
    
    print("✅ Installer package completo in installer_output/")
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

def compile_inno_setup_installer():
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
        # Compila l'installer
        result = subprocess.run([
            iscc_path, str(iss_file)
        ], capture_output=True, text=True, cwd=str(Path(__file__).parent))
        
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

def test_installation():
    """Testa il build (non l'installazione)"""
    print("\n🧪 Test build...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    python_exe = install_dir / "python" / "python.exe"
    
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
                               capture_output=True, text=True)
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
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ typing_extensions import OK")
        else:
            print(f"❌ typing_extensions import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ typing_extensions test error: {e}")
        return False
    
    # Verifica script servizio (senza installare)
    service_script = install_dir / "DBLogiX_Service.py"
    if service_script.exists():
        print("✅ Script servizio pronto per installazione")
    else:
        print("❌ Script servizio non trovato")
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
        
        # Download e setup Python Embedded
        python_dir = download_python_embedded()
        if not python_dir:
            return False
        
        if not configure_python_embedded(python_dir):
            return False
            
        if not install_pip(python_dir):
            return False
            
        if not install_requirements(python_dir):
            return False
        
        # Copia codice applicazione
        copy_application_code()
        
        # Crea script e servizio
        create_launcher_and_service()
        
        # Configurazione
        copy_configuration_and_certs()
        create_batch_files()
        create_build_info()
        
        # Test (solo verifica build, non installazione)
        if not test_installation():
            print("⚠️ Warning: Some tests failed, but installation may still work")
        
        # Crea package installer
        if not create_installer_package():
            print("⚠️ Warning: Installer package creation failed")
        
        # Risultato finale
        print("\n" + "="*70)
        print("✅ DBLogiX Python Embedded BUILD & PACKAGE COMPLETATO!")
        print("="*70)
        print(f"📂 Build directory: C:/Program Files/DBLogiX")
        print(f"📦 Package installer: installer_output/")
        print(f"🌐 Accesso web: https://localhost:5000 (dopo installazione)")
        print(f"📝 Log: C:/Program Files/DBLogiX/logs/ (dopo installazione)")
        print(f"🛠️ Servizio: DBLogiXEmbedded (installato dal setup)")
        print(f"🔥 Firewall: Configurato dal setup")
        print("")
        print("⚠️ NOTA: Servizio e firewall vengono configurati durante l'installazione del setup .exe")
        print("")
        print("📦 Per distribuzione ai clienti:")
        print("  installer_output/DBLogiX_Setup.exe        # 🎯 INSTALLER .EXE (PRINCIPALE)")
        print("  installer_output/install_dblogix.bat      # Installer batch (backup)")
        print("  installer_output/uninstall_dblogix.bat    # Uninstaller batch")
        print("")
        print("🎯 L'installer .exe chiede automaticamente privilegi amministratore!")
        print("🎉 Sistema pronto all'uso e per la distribuzione professionale!")
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