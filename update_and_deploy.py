#!/usr/bin/env python3
"""
DBLogiX - Update & Deploy Script (Python Embedded)
Aggiorna rapidamente il codice dell'applicazione senza reinstallare tutto
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import json
from datetime import datetime

def banner():
    """Mostra il banner dell'applicazione"""
    print("=" * 70)
    print("DBLogiX - Update & Deploy Script (Python Embedded)")
    print("=" * 70)
    print("* 🔄 Aggiornamento rapido codice applicazione")
    print("* 🛑 Stop servizio automatico")
    print("* 📋 Copia file aggiornati")
    print("* 🚀 Riavvio servizio automatico")
    print("* 🧪 Test funzionamento")
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

def check_installation():
    """Controlla che DBLogiX sia installato"""
    print("\n🔍 Controllo installazione esistente...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    
    if not install_dir.exists():
        print("❌ DBLogiX non installato!")
        print("   Esegui prima build_and_package.py per installazione completa")
        return False
    
    required_files = [
        "python/python.exe",
        "DBLogiX_Launcher.py",
        "DBLogiX_Service.py",
        "app"
    ]
    
    missing_files = []
    for file in required_files:
        if not (install_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ File installazione mancanti: {', '.join(missing_files)}")
        return False
    
    print("✅ Installazione DBLogiX trovata")
    return True

def create_backup():
    """Crea backup della versione attuale"""
    print("\n💾 Creazione backup...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    backup_dir = install_dir / "backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup dell'app
    app_dir = install_dir / "app"
    if app_dir.exists():
        shutil.copytree(app_dir, backup_dir / "app")
        print("✅ Backup app creato")
    
    # Backup configurazioni
    config_files = ["config", "certs"]
    for config in config_files:
        config_path = install_dir / config
        if config_path.exists():
            if config_path.is_dir():
                shutil.copytree(config_path, backup_dir / config)
            else:
                shutil.copy2(config_path, backup_dir / config)
            print(f"✅ Backup {config}")
    
    print(f"✅ Backup completo in: {backup_dir}")
    return backup_dir

def stop_service():
    """Ferma il servizio DBLogiX"""
    print("\n🛑 Stop servizio...")
    
    try:
        result = subprocess.run(['net', 'stop', 'DBLogiXEmbedded'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servizio fermato")
            return True
        else:
            print(f"⚠️ Warning stopping service: {result.stderr}")
            return True  # Continua comunque
    except Exception as e:
        print(f"❌ Error stopping service: {e}")
        return False

def update_application_code():
    """Aggiorna il codice dell'applicazione"""
    print("\n📋 Aggiornamento codice applicazione...")
    
    source_dir = Path(__file__).parent  # Directory root del progetto
    install_dir = Path("C:/Program Files/DBLogiX")
    app_dir = install_dir / "app"
    
    print(f"📂 Da: {source_dir}")
    print(f"📂 A: {app_dir}")
    
    # Directories da aggiornare
    dirs_to_update = [
        "app",
        "modules", 
        "services",
        "templates",
        "static",
        "migrations"
    ]
    
    # Files da aggiornare
    files_to_update = [
        "main.py",
        "requirements.txt"
    ]
    
    # Aggiorna directories
    for dir_name in dirs_to_update:
        source_path = source_dir / dir_name
        dest_path = app_dir / dir_name
        
        if source_path.exists():
            if dest_path.exists():
                shutil.rmtree(dest_path)
            shutil.copytree(source_path, dest_path)
            print(f"✅ {dir_name}")
        else:
            print(f"⚠️ Directory non trovata: {source_path}")
    
    # Aggiorna files
    for file_name in files_to_update:
        source_path = source_dir / file_name
        dest_path = app_dir / file_name
        
        if source_path.exists():
            shutil.copy2(source_path, dest_path)
            print(f"✅ {file_name}")
        else:
            print(f"⚠️ File non trovato: {source_path}")
    
    # Aggiorna configurazione se esiste
    source_config = source_dir / "DBLogix.exe.config"
    dest_config = install_dir / "config" / "DBLogix.exe.config"
    
    if source_config.exists():
        shutil.copy2(source_config, dest_config)
        print("✅ Configurazione aggiornata")
    
    print("✅ Codice applicazione aggiornato")

def start_service():
    """Avvia il servizio DBLogiX"""
    print("\n🚀 Avvio servizio...")
    
    try:
        result = subprocess.run(['net', 'start', 'DBLogiXEmbedded'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Servizio avviato")
            return True
        else:
            print(f"⚠️ Warning starting service: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error starting service: {e}")
        return False

def test_application():
    """Testa l'applicazione aggiornata"""
    print("\n🧪 Test applicazione...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    python_exe = install_dir / "python" / "python.exe"
    
    # Test import Flask
    try:
        result = subprocess.run([str(python_exe), "-c", "import flask; print('Flask OK')"], 
                               capture_output=True, text=True, cwd=str(install_dir))
        if result.returncode == 0:
            print("✅ Flask import OK")
        else:
            print(f"❌ Flask import failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Flask test error: {e}")
        return False
    
    # Test servizio
    try:
        result = subprocess.run(['sc', 'query', 'DBLogiXEmbedded'], 
                               capture_output=True, text=True)
        if "RUNNING" in result.stdout:
            print("✅ Servizio in esecuzione")
        else:
            print("⚠️ Servizio non in esecuzione")
    except:
        print("⚠️ Impossibile verificare stato servizio")
    
    return True

def update_build_info():
    """Aggiorna le informazioni di build"""
    print("\n📋 Aggiornamento build info...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    build_info_file = install_dir / "build_info.json"
    
    # Leggi build info esistente
    build_info = {}
    if build_info_file.exists():
        try:
            with open(build_info_file, 'r') as f:
                build_info = json.load(f)
        except:
            pass
    
    # Aggiorna informazioni
    build_info.update({
        "last_update": datetime.now().isoformat(),
        "update_type": "Code Update",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    })
    
    with open(build_info_file, 'w') as f:
        json.dump(build_info, f, indent=2)
    
    print("✅ Build info aggiornata")

def update_installer_package():
    """Aggiorna il package installer"""
    print("\n📦 Aggiornamento package installer...")
    
    install_dir = Path("C:/Program Files/DBLogiX")
    installer_output = Path("installer_output")
    
    # Crea directory output se non esiste
    installer_output.mkdir(exist_ok=True)
    
    # Aggiorna il package
    package_dir = installer_output / "DBLogiX"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    shutil.copytree(install_dir, package_dir)
    print("✅ Package installer aggiornato")

def main():
    """Funzione principale"""
    banner()
    
    try:
        # Controlli preliminari
        if not check_admin_privileges():
            print("\n❌ Privilegi amministratore richiesti!")
            print("   Esegui questo script come amministratore")
            return False
        
        if not check_installation():
            print("\n❌ Installazione DBLogiX non trovata!")
            return False
        
        # Processo di aggiornamento
        backup_dir = create_backup()
        
        if not stop_service():
            print("⚠️ Warning: Could not stop service, continuing anyway")
        
        update_application_code()
        update_build_info()
        
        if not start_service():
            print("❌ Error starting service!")
            print(f"💡 Ripristina dal backup: {backup_dir}")
            return False
        
        if not test_application():
            print("⚠️ Warning: Some tests failed")
        
        # Aggiorna package per distribuzione
        update_installer_package()
        
        # Risultato finale
        print("\n" + "="*70)
        print("✅ DBLogiX AGGIORNAMENTO COMPLETATO!")
        print("="*70)
        print(f"📂 Installazione: C:/Program Files/DBLogiX")
        print(f"💾 Backup: {backup_dir}")
        print(f"📦 Package installer: installer_output/")
        print(f"🌐 Accesso web: https://localhost:5000")
        print(f"📝 Log: C:/Program Files/DBLogiX/logs/")
        print(f"🛠️ Servizio: DBLogiXEmbedded")
        print("")
        print("Comandi utili:")
        print("  net restart DBLogiXEmbedded  # Riavvia servizio")
        print("  net stop DBLogiXEmbedded     # Ferma servizio") 
        print("  net start DBLogiXEmbedded    # Avvia servizio")
        print("")
        print("🎉 Aggiornamento completato!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Errore durante l'aggiornamento: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 Per supporto, controlla i log e considera il ripristino dal backup")
        sys.exit(1)
    sys.exit(0) 