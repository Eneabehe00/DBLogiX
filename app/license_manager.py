"""
DBLogiX License Manager
Sistema di gestione delle licenze per la sicurezza dei moduli
"""

import os
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

class LicenseManager:
    """Gestore delle licenze per i moduli"""
    
    def __init__(self):
        self.license_file = Path('app/licenses.json')
        self.valid_keys = self._load_valid_keys()
    
    def _load_valid_keys(self):
        """Carica le chiavi valide dal file di licenza"""
        try:
            if self.license_file.exists():
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('valid_keys', [])
            else:
                # Crea chiave predefinita se non esiste il file
                default_keys = [
                    {
                        'key': 'DBLogiX-ADMIN-2024',
                        'description': 'Chiave amministratore predefinita',
                        'created_at': datetime.now().isoformat(),
                        'expires_at': None,
                        'modules_allowed': ['all']
                    }
                ]
                self._save_keys(default_keys)
                return default_keys
        except Exception as e:
            print(f"Errore caricamento licenze: {e}")
            return []
    
    def _save_keys(self, keys):
        """Salva le chiavi nel file di licenza"""
        try:
            self.license_file.parent.mkdir(exist_ok=True)
            data = {
                'valid_keys': keys,
                'last_updated': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Errore salvataggio licenze: {e}")
    
    def validate_license_key(self, key):
        """Valida una chiave di licenza"""
        if not key:
            return False
        
        for license_info in self.valid_keys:
            if license_info['key'] == key:
                # Controlla scadenza
                if license_info.get('expires_at'):
                    expiry_date = datetime.fromisoformat(license_info['expires_at'])
                    if datetime.now() > expiry_date:
                        return False
                return True
        
        return False
    
    def get_license_info(self, key):
        """Ottiene informazioni su una licenza"""
        for license_info in self.valid_keys:
            if license_info['key'] == key:
                return license_info
        return None
    
    def generate_license_key(self, description="", modules_allowed=None, expires_days=None):
        """Genera una nuova chiave di licenza"""
        if modules_allowed is None:
            modules_allowed = ['all']
        
        # Genera chiave basata su timestamp e hash
        timestamp = datetime.now().isoformat()
        hash_input = f"{timestamp}_{description}_{len(self.valid_keys)}"
        key_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        key = f"DBLogiX-{key_hash.upper()}"
        
        # Calcola scadenza
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        license_info = {
            'key': key,
            'description': description,
            'created_at': timestamp,
            'expires_at': expires_at,
            'modules_allowed': modules_allowed
        }
        
        self.valid_keys.append(license_info)
        self._save_keys(self.valid_keys)
        
        return key
    
    def revoke_license_key(self, key):
        """Revoca una chiave di licenza"""
        self.valid_keys = [lic for lic in self.valid_keys if lic['key'] != key]
        self._save_keys(self.valid_keys)
        return True
    
    def list_licenses(self):
        """Lista tutte le licenze"""
        return self.valid_keys
    
    def check_module_access(self, key, module_name):
        """Controlla se una licenza permette l'accesso a un modulo specifico"""
        license_info = self.get_license_info(key)
        if not license_info:
            return False
        
        modules_allowed = license_info.get('modules_allowed', [])
        return 'all' in modules_allowed or module_name in modules_allowed


# Istanza globale del gestore licenze
license_manager = LicenseManager() 