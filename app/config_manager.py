import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import logging

# Configurazione del logger
logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestisce la configurazione esterna di DBLogiX"""
    
    def __init__(self):
        self.config_file_path = self._find_config_file()
        self.config = None
        self._load_config()
    
    def _find_config_file(self):
        """Trova il file di configurazione in base all'ambiente"""
        # Possibili percorsi del file di configurazione
        possible_paths = [
            # Per ambiente di sviluppo
            Path(__file__).parent.parent / "DBLogix.exe.config",
            
            # Per PyInstaller
            Path(sys.executable).parent / "DBLogix.exe.config",
            
            # Per Python Embedded
            Path(__file__).parent.parent.parent / "config" / "DBLogix.exe.config",
            
            # Percorso assoluto per Python Embedded
            Path("C:/Program Files/DBLogiX/config/DBLogix.exe.config"),
            
            # Percorso nella directory di installazione locale
            Path("C:/Users") / os.getenv('USERNAME', 'Default') / "AppData/Local/Programs/DBLogiX/DBLogix.exe.config"
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Configuration file found: {path}")
                return path
        
        # Se nessun file è trovato, usa il primo percorso come default
        default_path = possible_paths[0]
        logger.warning(f"Configuration file not found, using default: {default_path}")
        return default_path
    
    def _load_config(self):
        """Carica la configurazione dal file XML"""
        try:
            if not self.config_file_path.exists():
                logger.warning(f"Configuration file not found: {self.config_file_path}")
                self._create_default_config()
            
            tree = ET.parse(self.config_file_path)
            self.config = tree.getroot()
            logger.info(f"Configuration loaded from {self.config_file_path}")
            
        except ET.ParseError as e:
            logger.error(f"Error parsing configuration file: {e}")
            self._create_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._create_default_config()
    
    def get_setting(self, key, default=None):
        """Ottiene un'impostazione dalla configurazione"""
        if self.config is None:
            return default
        
        try:
            # Cerca in appSettings
            app_settings = self.config.find('appSettings')
            if app_settings is not None:
                for setting in app_settings.findall('add'):
                    if setting.get('key') == key:
                        value = setting.get('value')
                        logger.debug(f"Setting {key} = {value}")
                        return value
            
            logger.debug(f"Setting {key} not found, using default: {default}")
            return default
            
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    def get_db_config(self):
        """Ottiene la configurazione del database"""
        try:
            config = {
                'host': self.get_setting('DB_HOST', '192.168.1.32'),
                'port': int(self.get_setting('DB_PORT', 3306)),
                'user': self.get_setting('DB_USER', 'user'),
                'password': self.get_setting('DB_PASSWORD', 'dibal'),
                'database': self.get_setting('DB_DATABASE', 'sys_datos'),
                'charset': self.get_setting('DB_CHARSET', 'utf8'),
                'connect_timeout': int(self.get_setting('DB_CONNECT_TIMEOUT', 10)),
                'read_timeout': int(self.get_setting('DB_READ_TIMEOUT', 30)),
                'write_timeout': int(self.get_setting('DB_WRITE_TIMEOUT', 30)),
                'ssl_disabled': True,
                'use_unicode': True,
                'cursorclass': None  # Sarà impostato in runtime
            }
            
            # Importa pymysql solo quando necessario
            try:
                import pymysql.cursors
                config['cursorclass'] = pymysql.cursors.DictCursor
            except ImportError:
                logger.warning("PyMySQL not available, using default cursor")
            
            logger.info(f"Database host: {config['host']}")
            return config
            
        except Exception as e:
            logger.error(f"Error getting database configuration: {e}")
            raise
    
    def get_company_config(self):
        """Ottiene la configurazione dell'azienda"""
        return {
            'name': self.get_setting('COMPANY_NAME', 'DBLogiX Company'),
            'cif_vat': self.get_setting('COMPANY_CIF_VAT', ''),
            'phone': self.get_setting('COMPANY_PHONE', ''),
            'address': self.get_setting('COMPANY_ADDRESS', ''),
            'postal_code': self.get_setting('COMPANY_POSTAL_CODE', ''),
            'city': self.get_setting('COMPANY_CITY', ''),
            'province': self.get_setting('COMPANY_PROVINCE', ''),
            'logo_path': self.get_setting('COMPANY_LOGO_PATH', '')
        }
    
    def get_system_config(self):
        """Ottiene le configurazioni di sistema"""
        return {
            'expiry_warning_days': int(self.get_setting('EXPIRY_WARNING_DAYS', 7)),
            'articles_per_package': int(self.get_setting('ARTICLES_PER_PACKAGE', 5)),
            'timezone': self.get_setting('TIMEZONE', 'Europe/Rome'),
            'date_format': self.get_setting('DATE_FORMAT', '%d/%m/%Y'),
            'backup_frequency_hours': int(self.get_setting('BACKUP_FREQUENCY_HOURS', 24)),
            'backup_retention_days': int(self.get_setting('BACKUP_RETENTION_DAYS', 7))
        }
    
    def get_email_config(self):
        """Ottiene la configurazione email"""
        return {
            'smtp_server': self.get_setting('SMTP_SERVER', ''),
            'smtp_port': int(self.get_setting('SMTP_PORT', 587)),
            'smtp_username': self.get_setting('SMTP_USERNAME', ''),
            'smtp_password': self.get_setting('SMTP_PASSWORD', ''),
            'smtp_use_tls': self.get_setting('SMTP_USE_TLS', 'True').lower() == 'true',
            'admin_email': self.get_setting('ADMIN_EMAIL', ''),
            'enable_notifications': self.get_setting('ENABLE_EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
        }
    
    def get_chat_config(self):
        """Ottiene la configurazione chat"""
        return {
            'enabled': self.get_setting('CHAT_ENABLED', 'True').lower() == 'true',
            'max_messages': int(self.get_setting('CHAT_MAX_MESSAGES', 100)),
            'auto_delete_days': int(self.get_setting('CHAT_AUTO_DELETE_DAYS', 30))
        }
    
    def get_clienti_config(self):
        """Ottiene la configurazione clienti"""
        return {
            'enable_loyalty_points': self.get_setting('CLIENTI_ENABLE_LOYALTY_POINTS', 'True').lower() == 'true',
            'default_discount': float(self.get_setting('CLIENTI_DEFAULT_DISCOUNT', 0.0)),
            'require_email': self.get_setting('CLIENTI_REQUIRE_EMAIL', 'False').lower() == 'true'
        }
    
    def get_ddt_config(self):
        """Ottiene la configurazione DDT"""
        return {
            'auto_number': self.get_setting('DDT_AUTO_NUMBER', 'True').lower() == 'true',
            'default_payment_terms': int(self.get_setting('DDT_DEFAULT_PAYMENT_TERMS', 30)),
            'include_prices': self.get_setting('DDT_INCLUDE_PRICES', 'True').lower() == 'true'
        }
    
    def get_fatture_config(self):
        """Ottiene la configurazione fatture"""
        return {
            'auto_number': self.get_setting('FATTURE_AUTO_NUMBER', 'True').lower() == 'true',
            'default_payment_terms': int(self.get_setting('FATTURE_DEFAULT_PAYMENT_TERMS', 30)),
            'include_discount': self.get_setting('FATTURE_INCLUDE_DISCOUNT', 'True').lower() == 'true'
        }
    
    def update_setting(self, key, value):
        """Aggiorna un'impostazione"""
        try:
            if self.config is None:
                return False
            
            # Trova appSettings
            app_settings = self.config.find('appSettings')
            if app_settings is None:
                app_settings = ET.SubElement(self.config, 'appSettings')
            
            # Cerca l'impostazione esistente
            for setting in app_settings.findall('add'):
                if setting.get('key') == key:
                    setting.set('value', str(value))
                    break
            else:
                # Crea nuova impostazione
                new_setting = ET.SubElement(app_settings, 'add')
                new_setting.set('key', key)
                new_setting.set('value', str(value))
            
            # Salva il file
            self._save_config()
            logger.info(f"Setting updated: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            return False
    
    def update_db_config(self, db_config):
        """Aggiorna la configurazione del database"""
        try:
            settings_to_update = {
                'DB_HOST': db_config.get('host'),
                'DB_PORT': str(db_config.get('port')),
                'DB_USER': db_config.get('user'),
                'DB_PASSWORD': db_config.get('password'),
                'DB_DATABASE': db_config.get('database'),
                'DB_CHARSET': db_config.get('charset', 'utf8')
            }
            
            for key, value in settings_to_update.items():
                if value is not None:
                    self.update_setting(key, value)
            
            # Aggiorna anche la connection string
            self._update_connection_string(db_config)
            
            logger.info("Database configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating database configuration: {e}")
            return False
    
    def update_company_config(self, company_config):
        """Aggiorna la configurazione dell'azienda"""
        try:
            settings_map = {
                'name': 'COMPANY_NAME',
                'cif_vat': 'COMPANY_CIF_VAT',
                'phone': 'COMPANY_PHONE',
                'address': 'COMPANY_ADDRESS',
                'postal_code': 'COMPANY_POSTAL_CODE',
                'city': 'COMPANY_CITY',
                'province': 'COMPANY_PROVINCE',
                'logo_path': 'COMPANY_LOGO_PATH'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in company_config:
                    self.update_setting(setting_key, company_config[config_key])
            
            logger.info("Company configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating company configuration: {e}")
            return False
    
    def update_system_config(self, system_config):
        """Aggiorna le configurazioni di sistema"""
        try:
            settings_map = {
                'expiry_warning_days': 'EXPIRY_WARNING_DAYS',
                'articles_per_package': 'ARTICLES_PER_PACKAGE',
                'timezone': 'TIMEZONE',
                'date_format': 'DATE_FORMAT',
                'backup_frequency_hours': 'BACKUP_FREQUENCY_HOURS',
                'backup_retention_days': 'BACKUP_RETENTION_DAYS'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in system_config:
                    self.update_setting(setting_key, system_config[config_key])
            
            logger.info("System configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating system configuration: {e}")
            return False
    
    def update_chat_config(self, chat_config):
        """Aggiorna la configurazione chat"""
        try:
            settings_map = {
                'enabled': 'CHAT_ENABLED',
                'max_messages': 'CHAT_MAX_MESSAGES',
                'auto_delete_days': 'CHAT_AUTO_DELETE_DAYS'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in chat_config:
                    value = chat_config[config_key]
                    if isinstance(value, bool):
                        value = 'True' if value else 'False'
                    self.update_setting(setting_key, value)
            
            logger.info("Chat configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating chat configuration: {e}")
            return False
    
    def update_clienti_config(self, clienti_config):
        """Aggiorna la configurazione clienti"""
        try:
            settings_map = {
                'enable_loyalty_points': 'CLIENTI_ENABLE_LOYALTY_POINTS',
                'default_discount': 'CLIENTI_DEFAULT_DISCOUNT',
                'require_email': 'CLIENTI_REQUIRE_EMAIL'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in clienti_config:
                    value = clienti_config[config_key]
                    if isinstance(value, bool):
                        value = 'True' if value else 'False'
                    self.update_setting(setting_key, value)
            
            logger.info("Clienti configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating clienti configuration: {e}")
            return False
    
    def update_ddt_config(self, ddt_config):
        """Aggiorna la configurazione DDT"""
        try:
            settings_map = {
                'auto_number': 'DDT_AUTO_NUMBER',
                'default_payment_terms': 'DDT_DEFAULT_PAYMENT_TERMS',
                'include_prices': 'DDT_INCLUDE_PRICES'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in ddt_config:
                    value = ddt_config[config_key]
                    if isinstance(value, bool):
                        value = 'True' if value else 'False'
                    self.update_setting(setting_key, value)
            
            logger.info("DDT configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating DDT configuration: {e}")
            return False
    
    def update_fatture_config(self, fatture_config):
        """Aggiorna la configurazione fatture"""
        try:
            settings_map = {
                'auto_number': 'FATTURE_AUTO_NUMBER',
                'default_payment_terms': 'FATTURE_DEFAULT_PAYMENT_TERMS',
                'include_discount': 'FATTURE_INCLUDE_DISCOUNT'
            }
            
            for config_key, setting_key in settings_map.items():
                if config_key in fatture_config:
                    value = fatture_config[config_key]
                    if isinstance(value, bool):
                        value = 'True' if value else 'False'
                    self.update_setting(setting_key, value)
            
            logger.info("Fatture configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating fatture configuration: {e}")
            return False
    
    def _update_connection_string(self, db_config):
        """Aggiorna la connection string nel file di configurazione"""
        try:
            # Trova connectionStrings
            conn_strings = self.config.find('connectionStrings')
            if conn_strings is None:
                conn_strings = ET.SubElement(self.config, 'connectionStrings')
            
            # Cerca la connection string esistente
            for conn in conn_strings.findall('add'):
                if conn.get('name') == 'RemoteDatabase':
                    # Aggiorna la connection string esistente
                    new_conn_str = (f"Server={db_config.get('host')};"
                                   f"Port={db_config.get('port')};"
                                   f"Database={db_config.get('database')};"
                                   f"Uid={db_config.get('user')};"
                                   f"Pwd={db_config.get('password')};"
                                   f"Charset={db_config.get('charset', 'utf8')};")
                    conn.set('connectionString', new_conn_str)
                    break
            else:
                # Crea nuova connection string
                new_conn = ET.SubElement(conn_strings, 'add')
                new_conn.set('name', 'RemoteDatabase')
                new_conn_str = (f"Server={db_config.get('host')};"
                               f"Port={db_config.get('port')};"
                               f"Database={db_config.get('database')};"
                               f"Uid={db_config.get('user')};"
                               f"Pwd={db_config.get('password')};"
                               f"Charset={db_config.get('charset', 'utf8')};")
                new_conn.set('connectionString', new_conn_str)
            
        except Exception as e:
            logger.error(f"Error updating connection string: {e}")
    
    def _save_config(self):
        """Salva la configurazione nel file"""
        try:
            # Assicurati che la directory parent esista
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            tree = ET.ElementTree(self.config)
            tree.write(self.config_file_path, encoding='utf-8', xml_declaration=True)
            logger.info(f"Configuration saved to {self.config_file_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def _create_default_config(self):
        """Crea un file di configurazione predefinito"""
        root = ET.Element('configuration')
        
        # Aggiungi connectionStrings
        conn_strings = ET.SubElement(root, 'connectionStrings')
        conn = ET.SubElement(conn_strings, 'add')
        conn.set('name', 'RemoteDatabase')
        conn.set('connectionString', 'Server=192.168.1.32;Port=3306;Database=sys_datos;Uid=user;Pwd=dibal;Charset=utf8;')
        
        # Aggiungi appSettings
        app_settings = ET.SubElement(root, 'appSettings')
        
        default_settings = {
            'DB_HOST': '192.168.1.32',
            'DB_PORT': '3306',
            'DB_USER': 'user',
            'DB_PASSWORD': 'dibal',
            'DB_DATABASE': 'sys_datos',
            'DB_CHARSET': 'utf8',
            'SECRET_KEY': 'dev-key-for-dblogix',
            'FLASK_DEBUG': 'False'
        }
        
        for key, value in default_settings.items():
            setting = ET.SubElement(app_settings, 'add')
            setting.set('key', key)
            setting.set('value', value)
        
        tree = ET.ElementTree(root)
        tree.write(self.config_file_path, encoding='utf-8', xml_declaration=True)
        
        self.config = root
        logger.info(f"Default configuration created: {self.config_file_path}")

# Singleton pattern per il config manager
_config_manager = None

def get_config_manager():
    """Ottiene l'istanza singleton del config manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def reload_config():
    """Ricarica la configurazione"""
    global _config_manager
    _config_manager = ConfigManager()
    return _config_manager 