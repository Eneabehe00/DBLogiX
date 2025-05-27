#!/usr/bin/env python3
"""
DBLogiX Windows Service Wrapper
Questo file gestisce l'esecuzione di DBLogiX come servizio Windows
"""

import sys
import os
import subprocess
import time
import logging
from pathlib import Path

# Configurazione del servizio
SERVICE_NAME = "DBLogiX"
SERVICE_DISPLAY_NAME = "DBLogiX - Database Management System"
SERVICE_DESCRIPTION = "Sistema di gestione database e scanner barcode per magazzino"

def get_service_path():
    """Ottiene il path dell'eseguibile del servizio"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent / "DBLogiX.exe"
    else:
        # Running as Python script
        return Path(__file__).parent / "main_service.py"

def install_service():
    """Installa il servizio Windows"""
    service_path = get_service_path()
    
    if not service_path.exists():
        print(f"ERRORE: File del servizio non trovato: {service_path}")
        return False
    
    print(f"Installazione servizio {SERVICE_NAME}...")
    
    # Comando per creare il servizio
    cmd = [
        "sc", "create", SERVICE_NAME,
        f"binPath= \"{service_path}\"",
        f"DisplayName= \"{SERVICE_DISPLAY_NAME}\"",
        "start= auto",
        "type= own"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Servizio {SERVICE_NAME} installato con successo")
            
            # Configura la descrizione del servizio
            desc_cmd = ["sc", "description", SERVICE_NAME, SERVICE_DESCRIPTION]
            subprocess.run(desc_cmd, shell=True)
            
            # Configura il recovery del servizio (riavvio automatico in caso di errore)
            recovery_cmd = [
                "sc", "failure", SERVICE_NAME,
                "reset= 30", "actions= restart/5000/restart/10000/restart/30000"
            ]
            subprocess.run(recovery_cmd, shell=True)
            
            return True
        else:
            print(f"❌ Errore nell'installazione del servizio: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Errore durante l'installazione: {e}")
        return False

def uninstall_service():
    """Disinstalla il servizio Windows"""
    print(f"Disinstallazione servizio {SERVICE_NAME}...")
    
    # Prima ferma il servizio se in esecuzione
    stop_service()
    
    cmd = ["sc", "delete", SERVICE_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Servizio {SERVICE_NAME} disinstallato con successo")
            return True
        else:
            print(f"❌ Errore nella disinstallazione del servizio: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Errore durante la disinstallazione: {e}")
        return False

def start_service():
    """Avvia il servizio Windows"""
    print(f"Avvio servizio {SERVICE_NAME}...")
    
    cmd = ["sc", "start", SERVICE_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Servizio {SERVICE_NAME} avviato con successo")
            return True
        else:
            print(f"❌ Errore nell'avvio del servizio: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Errore durante l'avvio: {e}")
        return False

def stop_service():
    """Ferma il servizio Windows"""
    print(f"Arresto servizio {SERVICE_NAME}...")
    
    cmd = ["sc", "stop", SERVICE_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Servizio {SERVICE_NAME} arrestato con successo")
            return True
        else:
            # Il servizio potrebbe essere già fermo
            if "1062" in result.stderr:  # Service not running
                print(f"ℹ️ Servizio {SERVICE_NAME} non era in esecuzione")
                return True
            print(f"❌ Errore nell'arresto del servizio: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Errore durante l'arresto: {e}")
        return False

def get_service_status():
    """Ottiene lo stato del servizio Windows"""
    cmd = ["sc", "query", SERVICE_NAME]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            output = result.stdout
            if "RUNNING" in output:
                return "RUNNING"
            elif "STOPPED" in output:
                return "STOPPED"
            elif "PENDING" in output:
                return "PENDING"
            else:
                return "UNKNOWN"
        else:
            return "NOT_INSTALLED"
    except Exception as e:
        print(f"❌ Errore nel controllo dello stato: {e}")
        return "ERROR"

def configure_firewall():
    """Configura il firewall di Windows per permettere le connessioni"""
    print("Configurazione firewall Windows...")
    
    # Rimuovi regole esistenti se presenti
    subprocess.run([
        "netsh", "advfirewall", "firewall", "delete", "rule", 
        "name=DBLogiX HTTPS"
    ], capture_output=True, shell=True)
    
    # Aggiungi regola per porta 5000 HTTPS
    cmd = [
        "netsh", "advfirewall", "firewall", "add", "rule",
        "name=DBLogiX HTTPS",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        "localport=5000",
        "description=DBLogiX Database Management System HTTPS"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print("✅ Regola firewall creata con successo")
            return True
        else:
            print(f"❌ Errore nella configurazione del firewall: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Errore nella configurazione del firewall: {e}")
        return False

def check_admin_privileges():
    """Controlla se lo script è eseguito con privilegi di amministratore"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    """Funzione principale per la gestione del servizio"""
    if len(sys.argv) < 2:
        print(f"""
Gestione Servizio {SERVICE_NAME}

Utilizzo: {sys.argv[0]} <comando>

Comandi disponibili:
  install     - Installa il servizio Windows
  uninstall   - Disinstalla il servizio Windows
  start       - Avvia il servizio
  stop        - Ferma il servizio
  restart     - Riavvia il servizio
  status      - Mostra lo stato del servizio
  firewall    - Configura il firewall

Esempi:
  {sys.argv[0]} install
  {sys.argv[0]} start
  {sys.argv[0]} status
""")
        return 1
    
    command = sys.argv[1].lower()
    
    # Controlla i privilegi di amministratore per alcuni comandi
    admin_commands = ['install', 'uninstall', 'start', 'stop', 'restart', 'firewall']
    if command in admin_commands and not check_admin_privileges():
        print("❌ ERRORE: Questo comando richiede privilegi di amministratore.")
        print("   Esegui il prompt dei comandi come amministratore e riprova.")
        return 1
    
    if command == "install":
        success = install_service()
        if success:
            print("\n🔥 Configurazione firewall...")
            configure_firewall()
            print(f"\n🚀 Per avviare il servizio: {sys.argv[0]} start")
            print(f"📊 Per controllare lo stato: {sys.argv[0]} status")
            print(f"🌐 Accesso web: https://localhost:5000")
        return 0 if success else 1
    
    elif command == "uninstall":
        return 0 if uninstall_service() else 1
    
    elif command == "start":
        return 0 if start_service() else 1
    
    elif command == "stop":
        return 0 if stop_service() else 1
    
    elif command == "restart":
        print("Riavvio del servizio...")
        stop_service()
        time.sleep(2)
        return 0 if start_service() else 1
    
    elif command == "status":
        status = get_service_status()
        print(f"Stato servizio {SERVICE_NAME}: {status}")
        
        if status == "RUNNING":
            print("🌐 Il servizio è accessibile su: https://localhost:5000")
        elif status == "NOT_INSTALLED":
            print(f"💡 Per installare il servizio: {sys.argv[0]} install")
        
        return 0
    
    elif command == "firewall":
        return 0 if configure_firewall() else 1
    
    else:
        print(f"❌ Comando sconosciuto: {command}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 