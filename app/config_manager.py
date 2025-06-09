import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestisce la lettura e scrittura del file di configurazione XML"""
    
    def __init__(self, config_file_path: str = "DBLogix.exe.config"):
        self.config_file_path = config_file_path
        self.config_data = {}
        self.connection_strings = {}
        self._load_config()
    
    def _load_config(self):
        """Carica il file di configurazione XML"""
        try:
            if not os.path.exists(self.config_file_path):
                logger.warning(f"Config file {self.config_file_path} not found. Using default values.")
                return
            
            tree = ET.parse(self.config_file_path)
            root = tree.getroot()
            
            # Carica le impostazioni dell'applicazione
            app_settings = root.find('appSettings')
            if app_settings is not None:
                for setting in app_settings.findall('add'):
                    key = setting.get('key')
                    value = setting.get('value')
                    if key and value is not None:
                        self.config_data[key] = self._convert_value(value)
            
            # Carica le stringhe di connessione
            connection_strings = root.find('connectionStrings')
            if connection_strings is not None:
                for conn in connection_strings.findall('add'):
                    name = conn.get('name')
                    conn_string = conn.get('connectionString')
                    if name and conn_string:
                        self.connection_strings[name] = self._parse_connection_string(conn_string)
            
            logger.info(f"Configuration loaded from {self.config_file_path}")
            logger.info(f"Database host: {self.get_db_config().get('host', 'NOT SET')}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
    
    def _convert_value(self, value: str) -> Any:
        """Converte i valori stringa nei tipi appropriati"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        try:
            # Prova a convertire in intero
            return int(value)
        except ValueError:
            try:
                # Prova a convertire in float
                return float(value)
            except ValueError:
                # Ritorna come stringa
                return value
    
    def _parse_connection_string(self, conn_string: str) -> Dict[str, str]:
        """Analizza una stringa di connessione e restituisce un dizionario"""
        parts = {}
        for part in conn_string.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                parts[key.strip().lower()] = value.strip()
        return parts
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Ottiene un'impostazione dal file di configurazione"""
        return self.config_data.get(key, default)
    
    def get_company_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione dell'azienda"""
        return {
            'nombre_empresa': self.get_setting('COMPANY_NAME', ''),
            'cif_vat': self.get_setting('COMPANY_CIF_VAT', ''),
            'telefono': self.get_setting('COMPANY_PHONE', ''),
            'direccion': self.get_setting('COMPANY_ADDRESS', ''),
            'cod_postal': self.get_setting('COMPANY_POSTAL_CODE', ''),
            'poblacion': self.get_setting('COMPANY_CITY', ''),
            'provincia': self.get_setting('COMPANY_PROVINCE', ''),
            'logo_path': self.get_setting('COMPANY_LOGO_PATH', '')
        }
    
    def get_system_config(self) -> Dict[str, Any]:
        """Ottiene tutte le configurazioni del sistema"""
        return {
            # Basic system
            'expiry_warning_days': self.get_setting('EXPIRY_WARNING_DAYS', 7),
            'articles_per_package': self.get_setting('ARTICLES_PER_PACKAGE', 5),
            'timezone': self.get_setting('TIMEZONE', 'Europe/Rome'),
            'date_format': self.get_setting('DATE_FORMAT', '%d/%m/%Y'),
            
            # Email
            'smtp_server': self.get_setting('SMTP_SERVER', ''),
            'smtp_port': self.get_setting('SMTP_PORT', 587),
            'smtp_username': self.get_setting('SMTP_USERNAME', ''),
            'smtp_password': self.get_setting('SMTP_PASSWORD', ''),
            'smtp_use_tls': self.get_setting('SMTP_USE_TLS', True),
            'admin_email': self.get_setting('ADMIN_EMAIL', ''),
            'enable_email_notifications': self.get_setting('ENABLE_EMAIL_NOTIFICATIONS', False),
            
            # Backup
            'backup_frequency_hours': self.get_setting('BACKUP_FREQUENCY_HOURS', 24),
            'backup_retention_days': self.get_setting('BACKUP_RETENTION_DAYS', 7),
            'backup_path': self.get_setting('BACKUP_PATH', 'backups'),
            
            # Database timeouts
            'db_connect_timeout': self.get_setting('DB_CONNECT_TIMEOUT', 10),
            'db_read_timeout': self.get_setting('DB_READ_TIMEOUT', 30),
            'db_write_timeout': self.get_setting('DB_WRITE_TIMEOUT', 30),
            
            # Alerts
            'enable_stock_alerts': self.get_setting('ENABLE_STOCK_ALERTS', True),
            'stock_alert_threshold': self.get_setting('STOCK_ALERT_THRESHOLD', 10),
            'expiry_check_frequency_hours': self.get_setting('EXPIRY_CHECK_FREQUENCY_HOURS', 6),
            
            # Logging
            'log_level': self.get_setting('LOG_LEVEL', 'INFO'),
            'log_max_size_mb': self.get_setting('LOG_MAX_SIZE_MB', 10),
            
            # Session
            'session_timeout_hours': self.get_setting('SESSION_TIMEOUT_HOURS', 2),
            'session_inactivity_minutes': self.get_setting('SESSION_INACTIVITY_MINUTES', 30),
        }
    
    def get_chat_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione chat"""
        return {
            'enable_chat_auto_cleanup': self.get_setting('ENABLE_CHAT_AUTO_CLEANUP', False),
            'chat_cleanup_frequency_days': self.get_setting('CHAT_CLEANUP_FREQUENCY_DAYS', 7),
            'enable_chat_auto_backup': self.get_setting('ENABLE_CHAT_AUTO_BACKUP', True),
            'chat_backup_retention_days': self.get_setting('CHAT_BACKUP_RETENTION_DAYS', 30),
            'chat_backup_path': self.get_setting('CHAT_BACKUP_PATH', 'Backup/Chat')
        }
    
    def get_clienti_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione clienti"""
        return {
            'enable_clienti_auto_backup': self.get_setting('ENABLE_CLIENTI_AUTO_BACKUP', True),
            'clienti_backup_frequency_days': self.get_setting('CLIENTI_BACKUP_FREQUENCY_DAYS', 7),
            'clienti_backup_retention_days': self.get_setting('CLIENTI_BACKUP_RETENTION_DAYS', 30),
            'clienti_backup_path': self.get_setting('CLIENTI_BACKUP_PATH', 'Backup/Clienti')
        }
    
    def get_ddt_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione DDT"""
        return {
            'enable_ddt_auto_backup': self.get_setting('ENABLE_DDT_AUTO_BACKUP', True),
            'ddt_backup_frequency_days': self.get_setting('DDT_BACKUP_FREQUENCY_DAYS', 7),
            'ddt_backup_retention_days': self.get_setting('DDT_BACKUP_RETENTION_DAYS', 30),
            'ddt_backup_path': self.get_setting('DDT_BACKUP_PATH', 'Backup/DDT')
        }
    
    def get_fatture_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione fatture"""
        return {
            'enable_fatture_auto_backup': self.get_setting('ENABLE_FATTURE_AUTO_BACKUP', True),
            'fatture_backup_frequency_days': self.get_setting('FATTURE_BACKUP_FREQUENCY_DAYS', 7),
            'fatture_backup_retention_days': self.get_setting('FATTURE_BACKUP_RETENTION_DAYS', 30),
            'fatture_backup_path': self.get_setting('FATTURE_BACKUP_PATH', 'Backup/Fatture')
        }
    
    def get_db_config(self) -> Dict[str, Any]:
        """Ottiene la configurazione del database"""
        # Prima prova con la stringa di connessione
        if 'RemoteDatabase' in self.connection_strings:
            conn_data = self.connection_strings['RemoteDatabase']
            return {
                'host': conn_data.get('server', self.get_setting('DB_HOST', '192.168.1.32')),
                'port': int(conn_data.get('port', self.get_setting('DB_PORT', 3306))),
                'user': conn_data.get('uid', self.get_setting('DB_USER', 'user')),
                'password': conn_data.get('pwd', self.get_setting('DB_PASSWORD', 'dibal')),
                'database': conn_data.get('database', self.get_setting('DB_DATABASE', 'sys_datos')),
                'charset': conn_data.get('charset', self.get_setting('DB_CHARSET', 'utf8')),
                'connect_timeout': self.get_setting('DB_CONNECT_TIMEOUT', 10),
                'read_timeout': self.get_setting('DB_READ_TIMEOUT', 30),
                'write_timeout': self.get_setting('DB_WRITE_TIMEOUT', 30),
                'use_unicode': True,
                'ssl_disabled': True,
                'cursorclass': 'pymysql.cursors.DictCursor'
            }
        
        # Fallback alle impostazioni individuali
        return {
            'host': self.get_setting('DB_HOST', '192.168.1.32'),
            'port': self.get_setting('DB_PORT', 3306),
            'user': self.get_setting('DB_USER', 'user'),
            'password': self.get_setting('DB_PASSWORD', 'dibal'),
            'database': self.get_setting('DB_DATABASE', 'sys_datos'),
            'charset': self.get_setting('DB_CHARSET', 'utf8'),
            'connect_timeout': self.get_setting('DB_CONNECT_TIMEOUT', 10),
            'read_timeout': self.get_setting('DB_READ_TIMEOUT', 30),
            'write_timeout': self.get_setting('DB_WRITE_TIMEOUT', 30),
            'use_unicode': True,
            'ssl_disabled': True,
            'cursorclass': 'pymysql.cursors.DictCursor'
        }
    
    def update_setting(self, key: str, value: Any):
        """Aggiorna un'impostazione nel file di configurazione"""
        try:
            if not os.path.exists(self.config_file_path):
                self._create_default_config()
            
            tree = ET.parse(self.config_file_path)
            root = tree.getroot()
            
            app_settings = root.find('appSettings')
            if app_settings is None:
                app_settings = ET.SubElement(root, 'appSettings')
            
            # Trova l'impostazione esistente o creane una nuova
            setting = None
            for setting_elem in app_settings.findall('add'):
                if setting_elem.get('key') == key:
                    setting = setting_elem
                    break
            
            if setting is None:
                setting = ET.SubElement(app_settings, 'add')
                setting.set('key', key)
            
            setting.set('value', str(value))
            
            # Salva il file
            tree.write(self.config_file_path, encoding='utf-8', xml_declaration=True)
            
            # Aggiorna anche la cache locale
            self.config_data[key] = self._convert_value(str(value))
            
            logger.info(f"Updated setting {key} = {value}")
            
        except Exception as e:
            logger.error(f"Error updating setting {key}: {str(e)}")
            raise
    
    def update_db_config(self, db_config: Dict[str, Any]):
        """Aggiorna la configurazione del database"""
        try:
            # Aggiorna le impostazioni individuali
            self.update_setting('DB_HOST', db_config.get('host', '192.168.1.32'))
            self.update_setting('DB_PORT', db_config.get('port', 3306))
            self.update_setting('DB_USER', db_config.get('user', 'user'))
            self.update_setting('DB_PASSWORD', db_config.get('password', 'dibal'))
            self.update_setting('DB_DATABASE', db_config.get('database', 'sys_datos'))
            self.update_setting('DB_CHARSET', db_config.get('charset', 'utf8'))
            self.update_setting('DB_CONNECT_TIMEOUT', db_config.get('connect_timeout', 10))
            self.update_setting('DB_READ_TIMEOUT', db_config.get('read_timeout', 30))
            self.update_setting('DB_WRITE_TIMEOUT', db_config.get('write_timeout', 30))
            
            # Aggiorna anche la stringa di connessione
            self._update_connection_string('RemoteDatabase', db_config)
            
            # Ricarica la configurazione per assicurarsi che sia aggiornata
            self._load_config()
            
            logger.info(f"Database configuration updated: {db_config['host']}:{db_config['port']}/{db_config['database']}")
            
        except Exception as e:
            logger.error(f"Error updating database configuration: {str(e)}")
            raise
    
    def update_company_config(self, company_config: Dict[str, Any]):
        """Aggiorna la configurazione dell'azienda"""
        try:
            self.update_setting('COMPANY_NAME', company_config.get('nombre_empresa', ''))
            self.update_setting('COMPANY_CIF_VAT', company_config.get('cif_vat', ''))
            self.update_setting('COMPANY_PHONE', company_config.get('telefono', ''))
            self.update_setting('COMPANY_ADDRESS', company_config.get('direccion', ''))
            self.update_setting('COMPANY_POSTAL_CODE', company_config.get('cod_postal', ''))
            self.update_setting('COMPANY_CITY', company_config.get('poblacion', ''))
            self.update_setting('COMPANY_PROVINCE', company_config.get('provincia', ''))
            if 'logo_path' in company_config:
                self.update_setting('COMPANY_LOGO_PATH', company_config.get('logo_path', ''))
            
            logger.info("Company configuration updated")
        except Exception as e:
            logger.error(f"Error updating company configuration: {str(e)}")
            raise
    
    def update_system_config(self, system_config: Dict[str, Any]):
        """Aggiorna le configurazioni del sistema"""
        try:
            # Basic system settings
            if 'expiry_warning_days' in system_config:
                self.update_setting('EXPIRY_WARNING_DAYS', system_config['expiry_warning_days'])
            if 'articles_per_package' in system_config:
                self.update_setting('ARTICLES_PER_PACKAGE', system_config['articles_per_package'])
            if 'timezone' in system_config:
                self.update_setting('TIMEZONE', system_config['timezone'])
            if 'date_format' in system_config:
                self.update_setting('DATE_FORMAT', system_config['date_format'])
            
            # Email settings
            if 'smtp_server' in system_config:
                self.update_setting('SMTP_SERVER', system_config['smtp_server'])
            if 'smtp_port' in system_config:
                self.update_setting('SMTP_PORT', system_config['smtp_port'])
            if 'smtp_username' in system_config:
                self.update_setting('SMTP_USERNAME', system_config['smtp_username'])
            if 'smtp_password' in system_config:
                self.update_setting('SMTP_PASSWORD', system_config['smtp_password'])
            if 'smtp_use_tls' in system_config:
                self.update_setting('SMTP_USE_TLS', system_config['smtp_use_tls'])
            if 'admin_email' in system_config:
                self.update_setting('ADMIN_EMAIL', system_config['admin_email'])
            if 'enable_email_notifications' in system_config:
                self.update_setting('ENABLE_EMAIL_NOTIFICATIONS', system_config['enable_email_notifications'])
            
            # Backup settings
            if 'backup_frequency_hours' in system_config:
                self.update_setting('BACKUP_FREQUENCY_HOURS', system_config['backup_frequency_hours'])
            if 'backup_retention_days' in system_config:
                self.update_setting('BACKUP_RETENTION_DAYS', system_config['backup_retention_days'])
            if 'backup_path' in system_config:
                self.update_setting('BACKUP_PATH', system_config['backup_path'])
            
            # Database timeouts
            if 'db_connect_timeout' in system_config:
                self.update_setting('DB_CONNECT_TIMEOUT', system_config['db_connect_timeout'])
            if 'db_read_timeout' in system_config:
                self.update_setting('DB_READ_TIMEOUT', system_config['db_read_timeout'])
            if 'db_write_timeout' in system_config:
                self.update_setting('DB_WRITE_TIMEOUT', system_config['db_write_timeout'])
            
            # Alert settings
            if 'enable_stock_alerts' in system_config:
                self.update_setting('ENABLE_STOCK_ALERTS', system_config['enable_stock_alerts'])
            if 'stock_alert_threshold' in system_config:
                self.update_setting('STOCK_ALERT_THRESHOLD', system_config['stock_alert_threshold'])
            if 'expiry_check_frequency_hours' in system_config:
                self.update_setting('EXPIRY_CHECK_FREQUENCY_HOURS', system_config['expiry_check_frequency_hours'])
            
            # Logging settings
            if 'log_level' in system_config:
                self.update_setting('LOG_LEVEL', system_config['log_level'])
            if 'log_max_size_mb' in system_config:
                self.update_setting('LOG_MAX_SIZE_MB', system_config['log_max_size_mb'])
            
            # Session settings
            if 'session_timeout_hours' in system_config:
                self.update_setting('SESSION_TIMEOUT_HOURS', system_config['session_timeout_hours'])
            if 'session_inactivity_minutes' in system_config:
                self.update_setting('SESSION_INACTIVITY_MINUTES', system_config['session_inactivity_minutes'])
            
            logger.info("System configuration updated")
        except Exception as e:
            logger.error(f"Error updating system configuration: {str(e)}")
            raise
    
    def update_chat_config(self, chat_config: Dict[str, Any]):
        """Aggiorna la configurazione chat"""
        try:
            if 'enable_chat_auto_cleanup' in chat_config:
                self.update_setting('ENABLE_CHAT_AUTO_CLEANUP', chat_config['enable_chat_auto_cleanup'])
            if 'chat_cleanup_frequency_days' in chat_config:
                self.update_setting('CHAT_CLEANUP_FREQUENCY_DAYS', chat_config['chat_cleanup_frequency_days'])
            if 'enable_chat_auto_backup' in chat_config:
                self.update_setting('ENABLE_CHAT_AUTO_BACKUP', chat_config['enable_chat_auto_backup'])
            if 'chat_backup_retention_days' in chat_config:
                self.update_setting('CHAT_BACKUP_RETENTION_DAYS', chat_config['chat_backup_retention_days'])
            if 'chat_backup_path' in chat_config:
                self.update_setting('CHAT_BACKUP_PATH', chat_config['chat_backup_path'])
            
            logger.info("Chat configuration updated")
        except Exception as e:
            logger.error(f"Error updating chat configuration: {str(e)}")
            raise
    
    def update_clienti_config(self, clienti_config: Dict[str, Any]):
        """Aggiorna la configurazione clienti"""
        try:
            if 'enable_clienti_auto_backup' in clienti_config:
                self.update_setting('ENABLE_CLIENTI_AUTO_BACKUP', clienti_config['enable_clienti_auto_backup'])
            if 'clienti_backup_frequency_days' in clienti_config:
                self.update_setting('CLIENTI_BACKUP_FREQUENCY_DAYS', clienti_config['clienti_backup_frequency_days'])
            if 'clienti_backup_retention_days' in clienti_config:
                self.update_setting('CLIENTI_BACKUP_RETENTION_DAYS', clienti_config['clienti_backup_retention_days'])
            if 'clienti_backup_path' in clienti_config:
                self.update_setting('CLIENTI_BACKUP_PATH', clienti_config['clienti_backup_path'])
            
            logger.info("Clienti configuration updated")
        except Exception as e:
            logger.error(f"Error updating clienti configuration: {str(e)}")
            raise
    
    def update_ddt_config(self, ddt_config: Dict[str, Any]):
        """Aggiorna la configurazione DDT"""
        try:
            if 'enable_ddt_auto_backup' in ddt_config:
                self.update_setting('ENABLE_DDT_AUTO_BACKUP', ddt_config['enable_ddt_auto_backup'])
            if 'ddt_backup_frequency_days' in ddt_config:
                self.update_setting('DDT_BACKUP_FREQUENCY_DAYS', ddt_config['ddt_backup_frequency_days'])
            if 'ddt_backup_retention_days' in ddt_config:
                self.update_setting('DDT_BACKUP_RETENTION_DAYS', ddt_config['ddt_backup_retention_days'])
            if 'ddt_backup_path' in ddt_config:
                self.update_setting('DDT_BACKUP_PATH', ddt_config['ddt_backup_path'])
            
            logger.info("DDT configuration updated")
        except Exception as e:
            logger.error(f"Error updating DDT configuration: {str(e)}")
            raise
    
    def update_fatture_config(self, fatture_config: Dict[str, Any]):
        """Aggiorna la configurazione fatture"""
        try:
            if 'enable_fatture_auto_backup' in fatture_config:
                self.update_setting('ENABLE_FATTURE_AUTO_BACKUP', fatture_config['enable_fatture_auto_backup'])
            if 'fatture_backup_frequency_days' in fatture_config:
                self.update_setting('FATTURE_BACKUP_FREQUENCY_DAYS', fatture_config['fatture_backup_frequency_days'])
            if 'fatture_backup_retention_days' in fatture_config:
                self.update_setting('FATTURE_BACKUP_RETENTION_DAYS', fatture_config['fatture_backup_retention_days'])
            if 'fatture_backup_path' in fatture_config:
                self.update_setting('FATTURE_BACKUP_PATH', fatture_config['fatture_backup_path'])
            
            logger.info("Fatture configuration updated")
        except Exception as e:
            logger.error(f"Error updating fatture configuration: {str(e)}")
            raise
    
    def _update_connection_string(self, name: str, db_config: Dict[str, Any]):
        """Aggiorna la stringa di connessione nel file XML"""
        try:
            tree = ET.parse(self.config_file_path)
            root = tree.getroot()
            
            connection_strings = root.find('connectionStrings')
            if connection_strings is None:
                connection_strings = ET.SubElement(root, 'connectionStrings')
            
            # Trova la connessione esistente o creane una nuova
            conn = None
            for conn_elem in connection_strings.findall('add'):
                if conn_elem.get('name') == name:
                    conn = conn_elem
                    break
            
            if conn is None:
                conn = ET.SubElement(connection_strings, 'add')
                conn.set('name', name)
            
            # Costruisci la stringa di connessione
            conn_string = f"Server={db_config['host']};Port={db_config['port']};Database={db_config['database']};Uid={db_config['user']};Pwd={db_config['password']};Charset={db_config['charset']};"
            conn.set('connectionString', conn_string)
            
            # Salva il file
            tree.write(self.config_file_path, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            logger.error(f"Error updating connection string: {str(e)}")
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


# Istanza globale del config manager
config_manager = None

def get_config_manager() -> ConfigManager:
    """Ottiene l'istanza globale del config manager"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager()
    return config_manager

def reload_config():
    """Ricarica la configurazione"""
    global config_manager
    config_manager = ConfigManager()
    return config_manager 