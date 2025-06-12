#!/usr/bin/env python3
"""
Windows Service Wrapper per DBLogiX
Questo file gestisce l'esecuzione di DBLogiX come servizio Windows usando win32serviceutil
"""

import sys
import os
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import logging
from pathlib import Path

# Setup del path
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    BASE_PATH = Path(sys.executable).parent
else:
    # Running as Python script  
    BASE_PATH = Path(__file__).parent

os.chdir(BASE_PATH)
sys.path.insert(0, str(BASE_PATH))

class DBLogiXWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DBLogiX"
    _svc_display_name_ = "DBLogiX - Database Management System"
    _svc_description_ = "Sistema di gestione database e scanner barcode per magazzino"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.service_instance = None
        
        # Setup logging per il servizio Windows
        self.setup_logging()

    def setup_logging(self):
        """Setup logging per il servizio Windows"""
        logs_dir = BASE_PATH / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(logs_dir / 'windows_service.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('DBLogiXService')

    def SvcStop(self):
        """Ferma il servizio"""
        self.logger.info("Arresto servizio Windows richiesto")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        if self.service_instance:
            try:
                self.service_instance.stop()
            except Exception as e:
                self.logger.error(f"Errore durante l'arresto: {e}")
        
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """Avvia il servizio"""
        self.logger.info("Avvio servizio Windows DBLogiX")
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        try:
            # Import del servizio principale
            from main_service import DBLogiXService
            
            self.service_instance = DBLogiXService()
            
            # Avvia il servizio
            if self.service_instance.start():
                self.logger.info("Servizio avviato con successo")
                
                # Attendi il segnale di stop
                win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
                
            else:
                self.logger.error("Impossibile avviare il servizio")
                
        except Exception as e:
            self.logger.error(f"Errore durante l'esecuzione del servizio: {e}")
            servicemanager.LogErrorMsg(f"Errore DBLogiX Service: {e}")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(DBLogiXWindowsService) 