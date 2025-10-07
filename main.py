import os
import logging
import sys
import socket
import subprocess
import platform

# Check Python version
if sys.version_info.major == 3 and sys.version_info.minor >= 12:
    print("Warning: This application has been tested with Python 3.8-3.11.")
    print("You are using Python {}.{}, which may cause compatibility issues.".format(
        sys.version_info.major, sys.version_info.minor))
    print("If you encounter errors, consider using an earlier Python version or updating dependencies.")

# Optional loading of environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Take environment variables from .env if present
except ImportError:
    pass

# Set up logging
if not os.path.exists('logs'):
    os.mkdir('logs')
    
# Configure basic logging - Using only StreamHandler to avoid permission issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console logging only - no file rotation issues
    ]
)

logger = logging.getLogger(__name__)
logger.info('Starting DBLogiX application')

def get_zerotier_ip():
    """
    Rileva se ZeroTier è installato e attivo, e restituisce l'IP della scheda di rete ZeroTier.
    Restituisce None se ZeroTier non è disponibile o non è connesso.
    """
    try:
        system = platform.system().lower()
        
        if system == "windows":
            # Su Windows, usa ipconfig per trovare interfacce ZeroTier
            try:
                result = subprocess.run(['ipconfig', '/all'],
                                      capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
                output = result.stdout

                # Verifica che l'output non sia None
                if output is None:
                    logger.warning("Output di ipconfig è None")
                    return None

                # Cerca interfacce che contengono "ZeroTier" nel nome
                lines = output.split('\n')
                zerotier_section = False
                
                for i, line in enumerate(lines):
                    # Identifica sezioni ZeroTier
                    if 'zerotier' in line.lower() and 'adapter' in line.lower():
                        zerotier_section = True
                        logger.info(f"Trovata interfaccia ZeroTier: {line.strip()}")
                        continue
                    
                    # Se siamo in una sezione ZeroTier, cerca l'IP
                    if zerotier_section and 'IPv4 Address' in line:
                        # Estrai l'IP dalla riga
                        ip_part = line.split(':')[-1].strip()
                        # Rimuovi eventuali suffissi come "(Preferred)"
                        ip = ip_part.split('(')[0].strip()
                        
                        # Verifica che sia un IP valido
                        try:
                            socket.inet_aton(ip)
                            logger.info(f"IP ZeroTier trovato: {ip}")
                            return ip
                        except socket.error:
                            continue
                    
                    # Reset se troviamo una nuova sezione adapter
                    elif 'adapter' in line.lower() and 'zerotier' not in line.lower():
                        zerotier_section = False
                        
            except subprocess.TimeoutExpired:
                logger.warning("Timeout durante l'esecuzione di ipconfig")
            except Exception as e:
                logger.warning(f"Errore nell'esecuzione di ipconfig: {e}")
        
        elif system == "linux" or system == "darwin":  # Linux o macOS
            try:
                # Usa ip addr show per Linux o ifconfig per macOS
                if system == "linux":
                    result = subprocess.run(['ip', 'addr', 'show'],
                                          capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
                else:  # macOS
                    result = subprocess.run(['ifconfig'],
                                          capture_output=True, text=True, timeout=10, encoding='utf-8', errors='replace')
                
                output = result.stdout

                # Verifica che l'output non sia None
                if output is None:
                    logger.warning("Output del comando di rete è None")
                    return None

                # Cerca interfacce ZeroTier (di solito iniziano con zt)
                lines = output.split('\n')
                current_interface = None
                
                for line in lines:
                    # Identifica interfacce che iniziano con zt
                    if line.startswith('zt') or 'zt' in line:
                        current_interface = line.split(':')[0] if ':' in line else line.split()[0]
                        logger.info(f"Trovata interfaccia ZeroTier: {current_interface}")
                        continue
                    
                    # Se siamo su un'interfaccia ZeroTier, cerca l'IP
                    if current_interface and ('inet ' in line or 'inet addr:' in line):
                        # Estrai l'IP
                        if 'inet addr:' in line:  # Formato ifconfig vecchio
                            ip = line.split('inet addr:')[1].split()[0]
                        else:  # Formato ip addr show
                            ip = line.split('inet ')[1].split('/')[0].split()[0]
                        
                        # Verifica che sia un IP valido e non localhost
                        try:
                            socket.inet_aton(ip)
                            if not ip.startswith('127.'):
                                logger.info(f"IP ZeroTier trovato: {ip}")
                                return ip
                        except socket.error:
                            continue
                    
                    # Reset se troviamo una nuova interfaccia
                    elif line and not line.startswith(' ') and not line.startswith('\t'):
                        current_interface = None
                        
            except subprocess.TimeoutExpired:
                logger.warning("Timeout durante l'esecuzione del comando di rete")
            except Exception as e:
                logger.warning(f"Errore nell'esecuzione del comando di rete: {e}")
        
        # Metodo alternativo: cerca interfacce di rete Python
        try:
            import psutil
            
            # Ottieni tutte le interfacce di rete
            interfaces = psutil.net_if_addrs()
            
            for interface_name, addresses in interfaces.items():
                # Cerca interfacce che potrebbero essere ZeroTier
                if ('zt' in interface_name.lower() or 
                    'zerotier' in interface_name.lower() or
                    interface_name.lower().startswith('zt')):
                    
                    logger.info(f"Interfaccia ZeroTier trovata (psutil): {interface_name}")
                    
                    # Cerca indirizzi IPv4
                    for addr in addresses:
                        if addr.family == socket.AF_INET:  # IPv4
                            ip = addr.address
                            if not ip.startswith('127.'):  # Non localhost
                                logger.info(f"IP ZeroTier trovato (psutil): {ip}")
                                return ip
                                
        except ImportError:
            logger.debug("psutil non disponibile, usando solo metodi di sistema")
        except Exception as e:
            logger.warning(f"Errore con psutil: {e}")
        
        logger.info("Nessuna interfaccia ZeroTier attiva trovata")
        return None
        
    except Exception as e:
        logger.error(f"Errore nella rilevazione ZeroTier: {e}")
        return None

try:
    # Import Flask application creation function
    from app import create_app
    
    # Create the Flask application instance
    app = create_app()
    
    # Import db directly from models now for database operations
    from app.models import db
    
    # Create tables if they don't exist
    with app.app_context():
        try:
            db.create_all()
            logger.info('Database tables created (if they did not exist)')
        except Exception as e:
            logger.error(f'Error creating database tables: {str(e)}')
            print(f"Database Error: {str(e)}")
            print("Please check your database configuration in config.py")
            print("You may need to create the database tables manually or fix connection settings.")
    
    # Run the application
    if __name__ == '__main__':
        # Controlla se ZeroTier è disponibile
        zerotier_ip = get_zerotier_ip()
        
        if zerotier_ip:
            # Se ZeroTier è disponibile, usa il suo IP
            host = zerotier_ip
            logger.info(f'ZeroTier rilevato - Server avviato su IP ZeroTier: {host}')
        else:
            # Altrimenti usa la configurazione standard (localhost o variabile d'ambiente)
            host = os.environ.get('FLASK_HOST', '127.0.0.1')  # Cambiato da 0.0.0.0 a 127.0.0.1 per localhost
            logger.info(f'ZeroTier non rilevato - Server avviato su localhost: {host}')
        
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
        
        logger.info(f'Running application on {host}:{port} (debug={debug})')
        app.run(host=host, port=port, debug=debug, use_reloader=False)
        
except ImportError as e:
    logger.critical(f"Failed to import application modules: {str(e)}")
    print(f"ERROR: {str(e)}")
    print("\nPossible solutions:")
    print("1. Ensure all dependencies are installed: pip install -r requirements.txt")
    print("2. If using Python 3.12+, try with Python 3.8-3.11 or update incompatible packages")
    print("3. Check for syntax errors in your application files")
    sys.exit(1)
except Exception as e:
    logger.critical(f"Application failed to start: {str(e)}")
    print(f"ERROR: {str(e)}")
    sys.exit(1) 