#!/usr/bin/env python3
"""
Script completo per build e packaging di DBLogiX
Automatizza tutto il processo: PyInstaller + InnoSetup + Packaging
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

def banner():
    """Mostra il banner dell'applicazione"""
    print("=" * 60)
    print("DBLogiX - Complete Build & Package Script")
    print("=" * 60)
    print("* Compila e crea installer per DBLogiX")
    print("* Configurazione HTTPS automatica")
    print("* Servizio Windows integrato")
    print("* Packaging completo per distribuzione")
    print("* Supporto Python Embeddable")
    print("=" * 60)

def check_system_requirements():
    """Controlla che tutti i requisiti di sistema siano soddisfatti"""
    print("\n🔍 Controllo requisiti di sistema...")
    
    requirements = {
        'python': True,
        'pyinstaller': False,
        'innosetup': False
    }
    
    # Controlla Python
    try:
        python_version = sys.version_info
        if python_version.major == 3 and python_version.minor >= 8:
            print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
            requirements['python'] = True
        else:
            print(f"❌ Python {python_version.major}.{python_version.minor} non supportato (richiesto >= 3.8)")
            requirements['python'] = False
    except Exception as e:
        print(f"❌ Errore nel controllo di Python: {e}")
        requirements['python'] = False
    
    # Controlla PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__}")
        requirements['pyinstaller'] = True
    except ImportError:
        print("❌ PyInstaller non trovato")
        requirements['pyinstaller'] = False
    
    # Controlla InnoSetup
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    
    inno_found = False
    for path in inno_paths:
        if Path(path).exists():
            print(f"✅ InnoSetup trovato in: {path}")
            requirements['innosetup'] = True
            inno_found = True
            break
    
    if not inno_found:
        print("❌ InnoSetup non trovato")
        print("   Installa InnoSetup da: https://jrsoftware.org/isdl.php")
        requirements['innosetup'] = False
    
    # Verifica dipendenze Python
    missing_deps = []
    required_modules = [
        'flask', 'sqlalchemy', 'pymysql', 'cryptography', 
        'wtforms', 'jinja2', 'reportlab'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} mancante")
            missing_deps.append(module)
    
    if missing_deps:
        print(f"\n⚠️ Dipendenze mancanti: {', '.join(missing_deps)}")
        print("   Esegui: pip install -r requirements.txt")
        return False
    
    # Controlla file necessari
    required_files = [
        'main_service.py', 'app.py', 'models.py', 'config.py',
        'dblogix.spec', 'dblogix_installer.iss', 'generate_certs.py'
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
    
    return all(requirements.values()) and not missing_deps and not missing_files

def clean_previous_builds():
    """Pulisce build precedenti"""
    print("\n🧹 Pulizia build precedenti...")
    
    dirs_to_clean = [
        'build', 'dist', '__pycache__', 'installer_output',
        'release_package'
    ]
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"✅ Rimossa directory: {dir_name}")
    
    # Rimuovi file temporanei
    temp_files = ['build_key.key', '*.pyc']
    for pattern in temp_files:
        for file in Path('.').glob(pattern):
            if file.is_file():
                file.unlink()
                print(f"✅ Rimosso file: {file}")

def build_with_pyinstaller():
    """Compila l'applicazione con PyInstaller"""
    print("\n🏗️ Compilazione con PyInstaller...")
    
    try:
        # Verifica che il file .spec esista
        spec_file = Path('dblogix.spec')
        if not spec_file.exists():
            print(f"❌ File {spec_file} non trovato")
            return False
        
        print("✅ File .spec trovato")
        
        # Esegui PyInstaller
        cmd = ['pyinstaller', '--clean', '--noconfirm', 'dblogix.spec']
        print(f"⚙️ Esecuzione: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Compilazione PyInstaller completata!")
            return True
        else:
            print(f"❌ Errore PyInstaller:\n{result.stderr}")
            if result.stdout:
                print(f"📋 Output PyInstaller:\n{result.stdout}")
            return False
    
    except Exception as e:
        print(f"❌ Errore durante la compilazione: {e}")
        return False

def prepare_distribution():
    """Prepara la distribuzione copiando file aggiuntivi"""
    print("\n📁 Preparazione distribuzione...")
    
    dist_dir = Path('dist/DBLogiX')
    if not dist_dir.exists():
        print("❌ Directory dist/DBLogiX non trovata")
        return False
    
    # File aggiuntivi da copiare
    additional_files = [
        ('dblogix_service.py', 'dblogix_service.py'),
        ('README.md', 'README.md'),
        ('requirements.txt', 'requirements.txt'),
    ]
    
    for src, dst in additional_files:
        src_path = Path(src)
        if src_path.exists():
            shutil.copy2(src_path, dist_dir / dst)
            print(f"✅ Copiato: {src} -> {dst}")
    
    # Crea directory necessarie
    (dist_dir / 'logs').mkdir(exist_ok=True)
    (dist_dir / 'UPLOADS').mkdir(exist_ok=True)
    (dist_dir / 'Fatture').mkdir(exist_ok=True)
    
    print("✅ Directory di lavoro create")
    
    # Crea file di installazione
    install_content = """
# DBLogiX - Guida Installazione

## Installazione Rapida

1. **Apri il prompt dei comandi come Amministratore**
2. **Naviga nella directory di installazione:**
   ```
   cd "C:\\Program Files\\DBLogiX"
   ```
3. **Installa il servizio:**
   ```
   python dblogix_service.py install
   ```
4. **Avvia il servizio:**
   ```
   python dblogix_service.py start
   ```

## Accesso

🌐 **URL:** https://localhost:5000

⚠️ **IMPORTANTE:** Utilizzare sempre HTTPS

## Gestione Servizio

- **Stato:** `python dblogix_service.py status`
- **Ferma:** `python dblogix_service.py stop` 
- **Riavvia:** `python dblogix_service.py restart`
- **Disinstalla:** `python dblogix_service.py uninstall`

## Configurazione

Modifica `config.py` per la connessione al database.

## Log

I log sono disponibili nella directory `logs/`.

---
DBLogiX © 2024
"""
    
    with open(dist_dir / 'INSTALL.md', 'w', encoding='utf-8') as f:
        f.write(install_content)
    
    print("✅ File INSTALL.md creato")
    return True



def create_portable_package():
    """Crea un pacchetto portable ZIP"""
    print("\n📦 Creazione pacchetto portable...")
    
    dist_dir = Path('dist/DBLogiX')
    if not dist_dir.exists():
        print("❌ Directory dist/DBLogiX non trovata")
        return False
    
    # Crea directory package
    package_dir = Path('release_package')
    package_dir.mkdir(exist_ok=True)
    
    # Nome del file ZIP
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = package_dir / f'DBLogiX_Portable_{timestamp}.zip'
    
    print(f"📦 Creazione archivio: {zip_filename}")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(dist_dir)
                    zipf.write(file_path, arcname)
                    
        print(f"✅ Pacchetto portable creato: {zip_filename}")
        print(f"📊 Dimensione: {zip_filename.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    
    except Exception as e:
        print(f"❌ Errore nella creazione del pacchetto: {e}")
        return False

def create_build_info():
    """Crea file con informazioni di build"""
    build_info = {
        'build_date': datetime.now().isoformat(),
        'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        'platform': sys.platform,
        'encrypted': True,
        'https_enabled': True,
        'service_enabled': True,
        'version': '1.0.0'
    }
    
    build_file = Path('dist/DBLogiX/build_info.json')
    with open(build_file, 'w', encoding='utf-8') as f:
        json.dump(build_info, f, indent=2)
    
    print("✅ Informazioni di build salvate")

def download_python_embedded():
    """Scarica Python Embeddable se necessario"""
    print("\n🐍 Controllo Python Embeddable...")
    
    python_dir = Path('python_embedded/python')
    if python_dir.exists():
        print("✅ Python Embeddable già disponibile")
        return True
    
    print("📥 Download Python Embeddable...")
    try:
        # Esegui lo script di download
        import subprocess
        result = subprocess.run([sys.executable, 'download_python_embedded.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Python Embeddable scaricato con successo")
            return True
        else:
            print(f"⚠️ Errore nel download Python Embeddable: {result.stderr}")
            print("🔄 Continuo con la build senza Python Embeddable")
            return False
    except Exception as e:
        print(f"⚠️ Errore nel download Python Embeddable: {e}")
        print("🔄 Continuo con la build senza Python Embeddable")
        return False

def create_installer_with_python():
    """Crea installer con Python Embeddable se disponibile"""
    print("\n📦 Creazione installer...")
    
    python_embedded_available = Path('python_embedded/python').exists()
    
    if python_embedded_available:
        print("🐍 Creazione installer con Python Embeddable incluso...")
        iss_file = 'dblogix_installer_with_python.iss'
    else:
        print("⚠️ Creazione installer standard (Python richiesto separatamente)...")
        iss_file = 'dblogix_installer.iss'
    
    # Trova InnoSetup
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    
    iscc_path = None
    for path in inno_paths:
        if Path(path).exists():
            iscc_path = path
            break
    
    if not iscc_path:
        print("❌ InnoSetup Compiler non trovato")
        return False
    
    # Verifica che il file .iss esista
    if not Path(iss_file).exists():
        print(f"❌ File {iss_file} non trovato")
        return False
    
    # Crea directory output
    output_dir = Path('installer_output')
    output_dir.mkdir(exist_ok=True)
    
    # Esegui InnoSetup
    cmd = [iscc_path, str(iss_file)]
    print(f"⚙️ Esecuzione: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Installer creato con successo!")
            
            # Trova il file creato
            for exe_file in output_dir.glob('*.exe'):
                print(f"📦 Installer disponibile: {exe_file}")
            
            return True
        else:
            print(f"❌ Errore InnoSetup:\n{result.stderr}")
            return False
    
    except Exception as e:
        print(f"❌ Errore durante la creazione dell'installer: {e}")
        return False

def main():
    """Funzione principale"""
    banner()
    
    try:
        # Controllo requisiti
        if not check_system_requirements():
            print("\n❌ Requisiti non soddisfatti. Build interrotto.")
            return 1
        
        # Pulizia
        clean_previous_builds()
        
        # Download Python Embeddable (opzionale)
        python_embedded_available = download_python_embedded()
        
        # Build con PyInstaller
        if not build_with_pyinstaller():
            print("\n❌ Build PyInstaller fallito")
            return 1
        
        # Preparazione distribuzione
        if not prepare_distribution():
            print("\n❌ Preparazione distribuzione fallita")
            return 1
        
        # Informazioni di build
        create_build_info()
        
        # Installer InnoSetup (con o senza Python)
        installer_created = create_installer_with_python()
        
        # Pacchetto portable
        portable_created = create_portable_package()
        
        # Riepilogo finale
        print("\n" + "=" * 60)
        print("🎉 BUILD COMPLETATO!")
        print("=" * 60)
        
        print("📁 File generati:")
        print(f"   📂 Directory distribuzione: dist/DBLogiX/")
        
        if installer_created:
            print(f"   💾 Installer Windows: installer_output/")
        
        if portable_created:
            print(f"   📦 Pacchetto portable: release_package/")
        
        print("\n🔐 Caratteristiche:")
        print("   ✅ Servizio Windows automatico")
        print("   ✅ HTTPS configurato")
        print("   ✅ Firewall configurato automaticamente")
        print("   ✅ Certificati SSL auto-generati")
        
        if python_embedded_available:
            print("   🐍 Python Embeddable incluso (installazione autonoma)")
        else:
            print("   ⚠️ Python richiesto separatamente")
        
        print("\n🌐 Dopo l'installazione:")
        print("   📍 URL: https://localhost:5000")
        print("   🔧 Gestione: python dblogix_service.py <comando>")
        print("   📋 Log: directory logs/")
        
        return 0
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Build interrotto dall'utente")
        return 1
    
    except Exception as e:
        print(f"\n❌ Errore durante il build: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 