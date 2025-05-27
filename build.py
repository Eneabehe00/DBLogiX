#!/usr/bin/env python3
"""
Build Script per DBLogiX
Compila l'applicazione con PyInstaller usando crittografia per proteggere il codice
"""

import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

def check_requirements():
    """Controlla che tutti i requisiti siano soddisfatti"""
    print("🔍 Controllo dei requisiti...")
    
    # Controlla PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} trovato")
    except ImportError:
        print("❌ PyInstaller non trovato. Installalo con: pip install pyinstaller")
        return False
    
    # Controlla cryptography
    try:
        import cryptography
        print(f"✅ Cryptography {cryptography.__version__} trovato")
    except ImportError:
        print("❌ Cryptography non trovato. Installalo con: pip install cryptography")
        return False
    
    # Controlla che esistano i file necessari
    required_files = [
        'main_service.py',
        'app.py',
        'models.py',
        'config.py',
        'generate_certs.py',
        'templates',
        'static',
        'requirements.txt'
    ]
    
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ File/directory mancante: {file}")
            return False
        else:
            print(f"✅ {file} trovato")
    
    return True

def generate_cipher_key():
    """Genera una chiave di cifratura per PyInstaller"""
    print("🔐 Generazione chiave di cifratura...")
    
    # Genera una chiave casuale di 16 bytes
    import secrets
    key = secrets.token_bytes(16)
    
    # Salva la chiave in un file temporaneo
    key_file = Path('build_key.key')
    with open(key_file, 'wb') as f:
        f.write(key)
    
    print(f"✅ Chiave di cifratura generata: {key_file}")
    return key_file

def clean_build_dirs():
    """Pulisce le directory di build precedenti"""
    print("🧹 Pulizia directory di build...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"✅ Rimossa directory: {dir_name}")

def update_spec_file(key_file):
    """Aggiorna il file .spec con la chiave di cifratura"""
    spec_file = Path('dblogix.spec')
    
    # Leggi il contenuto attuale
    with open(spec_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Sostituisci la linea del cipher (usa forward slash per evitare problemi di escape)
    key_path = str(key_file.absolute()).replace('\\', '/')
    key_line = f"block_cipher = pyi_crypto.PyiBlockCipher(key='{key_path}')"
    
    # Aggiungi import per la crittografia all'inizio del file
    import_line = "from PyInstaller.utils import misc as pyi_crypto\n"
    
    if "from PyInstaller.utils import misc as pyi_crypto" not in content:
        content = import_line + content
    
    # Sostituisci la linea block_cipher = None
    content = content.replace('block_cipher = None', key_line)
    
    # Scrivi il file aggiornato
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ File .spec aggiornato con crittografia")

def build_application():
    """Compila l'applicazione con PyInstaller"""
    print("🏗️ Compilazione dell'applicazione...")
    
    # Comandi PyInstaller
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'dblogix.spec'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Compilazione completata con successo!")
            return True
        else:
            print(f"❌ Errore durante la compilazione:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"❌ Errore durante l'esecuzione di PyInstaller: {e}")
        return False

def copy_additional_files():
    """Copia file aggiuntivi necessari nella directory dist"""
    print("📁 Copia file aggiuntivi...")
    
    dist_dir = Path('dist/DBLogiX')
    if not dist_dir.exists():
        print("❌ Directory dist/DBLogiX non trovata")
        return False
    
    # File da copiare
    additional_files = [
        ('dblogix_service.py', 'dblogix_service.py'),
        ('README.md', 'README.md'),
        ('requirements.txt', 'requirements.txt'),
    ]
    
    for src, dst in additional_files:
        if Path(src).exists():
            shutil.copy2(src, dist_dir / dst)
            print(f"✅ Copiato: {src} -> {dst}")
    
    # Crea directory logs se non esiste
    logs_dir = dist_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    print("✅ Directory logs creata")
    
    return True

def create_installer_readme():
    """Crea un README per l'installer"""
    readme_content = """
# DBLogiX - Installazione e Configurazione

## Installazione Servizio Windows

1. **Estrai tutti i file** da questo archivio in una directory (es. C:\\DBLogiX)

2. **Apri il prompt dei comandi come Amministratore**

3. **Naviga nella directory di installazione:**
   ```
   cd C:\\DBLogiX
   ```

4. **Installa il servizio:**
   ```
   python dblogix_service.py install
   ```

5. **Avvia il servizio:**
   ```
   python dblogix_service.py start
   ```

## Accesso all'Applicazione

Una volta installato e avviato il servizio, l'applicazione sarà accessibile tramite:

🌐 **URL:** https://localhost:5000

⚠️ **IMPORTANTE:** L'applicazione funziona SOLO in HTTPS per garantire il corretto funzionamento dello scanner barcode.

## Gestione del Servizio

### Comandi disponibili:
- `python dblogix_service.py status` - Controlla lo stato del servizio
- `python dblogix_service.py stop` - Ferma il servizio
- `python dblogix_service.py restart` - Riavvia il servizio
- `python dblogix_service.py uninstall` - Disinstalla il servizio

### Firewall
Il servizio configura automaticamente il firewall di Windows per permettere le connessioni sulla porta 5000.

## Configurazione Database

Modifica il file `config.py` per configurare la connessione al database MySQL se necessario.

## Log

I log dell'applicazione sono salvati nella directory `logs/`:
- `dblogix_service.log` - Log del servizio principale
- `dblogix.log` - Log dell'applicazione Flask

## Supporto

Per problemi o assistenza, controlla i file di log nella directory `logs/`.

---

**DBLogiX** - Sistema di gestione database e scanner barcode
"""
    
    readme_file = Path('dist/DBLogiX/INSTALL.md')
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ File INSTALL.md creato")

def cleanup_build_artifacts():
    """Pulisce i file di build temporanei"""
    print("🧹 Pulizia file temporanei...")
    
    # Rimuovi la chiave di cifratura
    key_file = Path('build_key.key')
    if key_file.exists():
        key_file.unlink()
        print("✅ Chiave di cifratura rimossa")
    
    # Pulisci directory build
    if Path('build').exists():
        shutil.rmtree('build')
        print("✅ Directory build rimossa")

def main():
    """Funzione principale del build"""
    print("=" * 50)
    print("🚀 DBLogiX Build Script")
    print("=" * 50)
    
    # Controlla i requisiti
    if not check_requirements():
        print("❌ Requisiti non soddisfatti. Build interrotto.")
        return 1
    
    try:
        # Pulisci directory precedenti
        clean_build_dirs()
        
        # Genera chiave di cifratura
        key_file = generate_cipher_key()
        
        # Aggiorna il file .spec
        update_spec_file(key_file)
        
        # Compila l'applicazione
        if not build_application():
            print("❌ Build fallito")
            return 1
        
        # Copia file aggiuntivi
        if not copy_additional_files():
            print("❌ Errore nella copia dei file aggiuntivi")
            return 1
        
        # Crea README installer
        create_installer_readme()
        
        print("\n" + "=" * 50)
        print("✅ BUILD COMPLETATO CON SUCCESSO!")
        print("=" * 50)
        print(f"📁 File compilati disponibili in: dist/DBLogiX/")
        print("📄 Leggi INSTALL.md per le istruzioni di installazione")
        print("🔐 Codice Python protetto da crittografia")
        print("🌐 Applicazione configurata per HTTPS sulla porta 5000")
        
        return 0
    
    except Exception as e:
        print(f"❌ Errore durante il build: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Pulisci sempre i file temporanei
        cleanup_build_artifacts()

if __name__ == "__main__":
    sys.exit(main()) 