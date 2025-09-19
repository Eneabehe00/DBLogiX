"""
DBLogiX - Configurazione Moduli
Gestisce quali moduli sono abilitati nell'installazione corrente
"""

import os
import json
from pathlib import Path

# Definizione dei moduli disponibili
AVAILABLE_MODULES = {
    # Moduli base (sempre abilitati)
    'warehouse': {
        'name': 'Gestione Magazzino',
        'description': 'Prodotti, sezioni, ticket',
        'essential': True,
        'blueprint': 'warehouse_bp',
        'import_path': 'modules.warehouse',
        'menu_items': ['home', 'prodotti', 'ticket']
    },
    'admin': {
        'name': 'Amministrazione',
        'description': 'Pannello amministrativo e configurazioni',
        'essential': True,
        'blueprint': 'admin_bp',
        'import_path': 'modules.admin',
        'menu_items': ['amministrazione']
    },
    'auth': {
        'name': 'Autenticazione',
        'description': 'Sistema di login e gestione utenti',
        'essential': True,
        'blueprint': 'auth_bp', 
        'import_path': 'app.auth',
        'menu_items': []
    },
    'articles': {
        'name': 'Gestione Articoli',
        'description': 'Catalogo prodotti avanzato',
        'essential': True,
        'blueprint': 'articles_bp',
        'import_path': 'modules.articles',
        'menu_items': ['prodotti']
    },
    'sections': {
        'name': 'Gestione Sezioni',
        'description': 'Organizzazione magazzino per sezioni',
        'essential': True,
        'blueprint': 'sections_bp',
        'import_path': 'modules.sections',
        'menu_items': ['prodotti']
    },
    
    # Moduli opzionali (abilitabili durante installazione)
    'clients': {
        'name': 'Gestione Clienti',
        'description': 'Anagrafica clienti e gestione contatti',
        'essential': False,
        'blueprint': 'clients_bp',
        'import_path': 'modules.clients',
        'menu_items': ['clienti'],
        'price_tier': 'standard'
    },
    'listini': {
        'name': 'Listini Prezzi',
        'description': 'Gestione listini personalizzati per clienti',
        'essential': False,
        'blueprint': 'listini_bp',
        'import_path': 'modules.listini',
        'menu_items': ['listini'],
        'price_tier': 'standard'
    },

    'ddt': {
        'name': 'DDT - Documenti di Trasporto',
        'description': 'Creazione e gestione DDT',
        'essential': False,
        'blueprint': 'ddt_bp',
        'import_path': 'modules.ddt',
        'menu_items': ['ddt'],
        'price_tier': 'standard'
    },
    'tasks': {
        'name': 'Gestione Task',
        'description': 'Sistema di task e workflow',
        'essential': False,
        'blueprint': 'tasks_bp',
        'import_path': 'modules.tasks',
        'menu_items': ['task'],
        'price_tier': 'professional'
    },
    'chat': {
        'name': 'Chat Globale',
        'description': 'Sistema di messaggistica e comunicazione tra utenti',
        'essential': False,
        'blueprint': 'chat_bp',
        'import_path': 'modules.chat',
        'menu_items': ['chat'],
        'price_tier': 'standard'
    },
    'fattura_pa': {
        'name': 'Fatture Elettroniche PA',
        'description': 'Fatturazione elettronica PA',
        'essential': False,
        'blueprint': 'fattura_pa_bp',
        'import_path': 'modules.fattura_pa',
        'menu_items': ['fatture'],
        'price_tier': 'professional'
    },
    'scanner': {
        'name': 'Scanner Codici',
        'description': 'Scansione codici a barre e QR',
        'essential': False,
        'blueprint': 'warehouse_bp',  # Usa lo stesso blueprint del warehouse
        'import_path': 'modules.warehouse',
        'menu_items': ['scanner'],
        'price_tier': 'standard'
    },
    'ingredients': {
        'name': 'Gestione Ingredienti',
        'description': 'Gestione ingredienti, fornitori e calcolo food cost',
        'essential': False,
        'blueprint': 'ingredients_bp',
        'import_path': 'modules.ingredients',
        'menu_items': ['ingredienti'],
        'price_tier': 'professional'
    }
}

# Configurazioni predefinite per diversi tier di prezzo
PRICING_TIERS = {
    'basic': {
        'name': 'DBLogiX Basic',
        'description': 'Gestione base magazzino',
        'modules': ['warehouse', 'admin', 'auth', 'articles', 'sections']
    },
    'standard': {
        'name': 'DBLogiX Standard', 
        'description': 'Include gestione clienti, listini, DDT, chat e scanner',
        'modules': ['warehouse', 'admin', 'auth', 'articles', 'sections', 'clients', 'listini', 'ddt', 'chat', 'scanner']
    },
    'professional': {
        'name': 'DBLogiX Professional',
        'description': 'Versione completa con task, fatturazione, chat, scanner e ingredienti',
        'modules': ['warehouse', 'admin', 'auth', 'articles', 'sections', 'clients', 'listini', 'ddt', 'chat', 'scanner', 'tasks', 'fattura_pa', 'ingredients']
    }
}


class ModulesManager:
    """Gestore della configurazione moduli"""
    
    def __init__(self):
        self.config_file = Path('app/enabled_modules.json')
        self._enabled_modules = None
    
    def get_enabled_modules(self):
        """Ottiene la lista dei moduli abilitati"""
        if self._enabled_modules is None:
            self._load_config()
        return self._enabled_modules
    
    def _load_config(self):
        """Carica la configurazione dai file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._enabled_modules = config.get('enabled_modules', [])
            else:
                # Default: tutti i moduli essenziali
                self._enabled_modules = [
                    name for name, info in AVAILABLE_MODULES.items() 
                    if info.get('essential', False)
                ]
                self._save_config()
        except Exception as e:
            print(f"Errore caricamento configurazione moduli: {e}")
            # Fallback: moduli essenziali
            self._enabled_modules = [
                name for name, info in AVAILABLE_MODULES.items() 
                if info.get('essential', False)
            ]
    
    def _save_config(self):
        """Salva la configurazione"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            config = {
                'enabled_modules': self._enabled_modules,
                'installation_date': str(Path(__file__).stat().st_ctime),
                'version': '2.0.0'
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Errore salvataggio configurazione moduli: {e}")
    
    def is_module_enabled(self, module_name):
        """Verifica se un modulo è abilitato"""
        return module_name in self.get_enabled_modules()
    
    def enable_modules(self, modules_list):
        """Abilita una lista di moduli"""
        # Assicurati che i moduli essenziali siano sempre abilitati
        essential_modules = [
            name for name, info in AVAILABLE_MODULES.items() 
            if info.get('essential', False)
        ]
        
        self._enabled_modules = list(set(essential_modules + modules_list))
        self._save_config()
    
    def set_tier_configuration(self, tier):
        """Imposta la configurazione per un tier specifico"""
        if tier in PRICING_TIERS:
            self.enable_modules(PRICING_TIERS[tier]['modules'])
            return True
        return False
    
    def get_available_modules_info(self):
        """Ottiene informazioni su tutti i moduli disponibili"""
        return AVAILABLE_MODULES
    
    def get_enabled_modules_info(self):
        """Ottiene informazioni sui moduli abilitati"""
        enabled = self.get_enabled_modules()
        return {name: info for name, info in AVAILABLE_MODULES.items() if name in enabled}


# Istanza globale del manager
modules_manager = ModulesManager() 