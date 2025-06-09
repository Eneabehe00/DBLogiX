from flask import Flask, render_template, jsonify, redirect, url_for, flash, request, send_from_directory
from flask_login import LoginManager, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import subprocess
import re
import socket
from datetime import datetime
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.sql import text

# Initialize logger
logger = logging.getLogger(__name__)

# Import db from models directly - this avoids circular imports
from app.models import db
from app.models import User, Product, TicketHeader, TicketLine, ScanLog, Client, Company, Article, AlbaranCabecera, AlbaranLinea

def create_app():
    app = Flask(__name__)
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Load configuration
    try:
        app.config.from_object('app.config.Config')
        
        # Override config with environment variables if present
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'dev-key-for-dblogix'))
        
        # Set debug mode based on environment
        app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
        
        # Database configuration can be updated from environment
        db_host = os.environ.get('DB_HOST')
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASSWORD')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT')
        
        # Import here to avoid circular imports
        from app.config import REMOTE_DB_CONFIG
        
        # Update config from environment variables if provided
        if db_host: REMOTE_DB_CONFIG['host'] = db_host
        if db_user: REMOTE_DB_CONFIG['user'] = db_user
        if db_pass: REMOTE_DB_CONFIG['password'] = db_pass
        if db_name: REMOTE_DB_CONFIG['database'] = db_name
        if db_port: REMOTE_DB_CONFIG['port'] = int(db_port)
        
        # Set SQLAlchemy URI
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
        
        logger.info(f"Database configuration: {REMOTE_DB_CONFIG['host']}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}")
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        print(f"Configuration error: {str(e)}")
    
    # Initialize extensions
    try:
        # Initialize database
        db.init_app(app)
        
        # Initialize migration support
        try:
            from flask_migrate import Migrate
            migrate = Migrate(app, db)
        except ImportError:
            logger.warning("Flask-Migrate not installed. Database migrations will not be available.")
        
        # Setup login manager
        login_manager = LoginManager()
        login_manager.login_view = 'auth.login'
        login_manager.login_message = 'Please log in to access this page.'
        login_manager.login_message_category = 'info'
        login_manager.init_app(app)
        
        @login_manager.user_loader
        def load_user(id):
            from app.models import User
            return User.query.get(int(id))
        
        # Register blueprints
        from modules.warehouse import warehouse_bp
        from app.auth import auth_bp
        from modules.admin import admin_bp
        from modules.ddt import ddt_bp
        from modules.clients import clients_bp
        from modules.articles import articles_bp
        from modules.sections import sections_bp
        from modules.fattura_pa import fattura_pa_bp
        from services.chat import chat_bp
        from modules.tasks import tasks_bp
        
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(warehouse_bp, url_prefix='/warehouse')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(ddt_bp, url_prefix='/ddt')
        app.register_blueprint(clients_bp, url_prefix='/clients')
        app.register_blueprint(articles_bp, url_prefix='/articles')
        app.register_blueprint(sections_bp, url_prefix='/sections')
        app.register_blueprint(fattura_pa_bp, url_prefix='/fattura_pa')
        app.register_blueprint(chat_bp, url_prefix='/chat')
        app.register_blueprint(tasks_bp, url_prefix='/tasks')
        
        # Register template filters
        from services.utils import format_price, format_weight, current_time, b64encode
        
        # Configurazione Flask-DebugToolbar (solo se in modalità debug)
        if app.debug:
            try:
                from flask_debugtoolbar import DebugToolbarExtension
                app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
                app.config['DEBUG_TB_ENABLED'] = True
                app.config['DEBUG_TB_HOSTS'] = ['127.0.0.1', 'localhost']
                # Disabilita il debug toolbar per le rotte /fattura_pa/*
                app.config['DEBUG_TB_TEMPLATE_EDITOR_ENABLED'] = False
                app.config['DEBUG_TB_PANELS'] = [
                    'flask_debugtoolbar.panels.versions.VersionDebugPanel',
                    'flask_debugtoolbar.panels.timer.TimerDebugPanel',
                    'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
                    'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
                    'flask_debugtoolbar.panels.config_vars.ConfigVarsDebugPanel',
                    'flask_debugtoolbar.panels.template.TemplateDebugPanel',
                    'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
                    'flask_debugtoolbar.panels.logger.LoggingPanel',
                    'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
                ]
                app.config['DEBUG_TB_EXCLUDE_PATHS'] = ['/fattura_pa/', '/fattura_pa/*', '/static/*']
                toolbar = DebugToolbarExtension(app)
            except ImportError:
                logger.warning("Flask-DebugToolbar not available. Continuing without debug toolbar.")
        
        @app.template_filter('price')
        def price_filter(value):
            return format_price(value)
        
        @app.template_filter('weight')
        def weight_filter(value, comportamiento=0):
            return format_weight(value, comportamiento)
        
        @app.template_filter('b64encode')
        def b64encode_filter(value):
            return b64encode(value)
        
        @app.template_filter('date')
        def date_filter(value):
            if value is None:
                return ""
            if isinstance(value, str):
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return value
            return value.strftime('%d/%m/%Y %H:%M') if value else ""
        
        @app.context_processor
        def utility_processor():
            from datetime import datetime
            from flask_wtf.csrf import generate_csrf
            from flask_login import current_user
            
            def current_time():
                return datetime.now()
            
            def get_user_active_tasks_count():
                """Get count of active tasks for current user"""
                if not current_user.is_authenticated or current_user.is_admin:
                    return 0
                from app.models import Task
                return Task.query.filter(
                    Task.assigned_to == current_user.id,
                    Task.status.in_(['pending', 'assigned', 'in_progress'])
                ).count()
            
            def get_admin_completed_notifications_count():
                """Get count of unread task completion notifications for admin"""
                if not current_user.is_authenticated or not current_user.is_admin:
                    return 0
                from app.models import TaskNotification
                return TaskNotification.query.filter_by(
                    user_id=current_user.id,
                    is_read=False,
                    notification_type='task_completed'
                ).count()
            
            def is_task_expired(task_deadline):
                """Check if task deadline has passed (only tomorrow counts as expired)"""
                if not task_deadline:
                    return False
                today = datetime.now().date()
                deadline_date = task_deadline.date()
                return deadline_date < today  # Only expired if deadline date is in the past
            
            def is_task_expiring_soon(task_deadline):
                """Check if task deadline is today or tomorrow (warning)"""
                if not task_deadline:
                    return False
                today = datetime.now().date()
                deadline_date = task_deadline.date()
                days_left = (deadline_date - today).days
                return days_left <= 1 and days_left >= 0  # Today or tomorrow
            
            def days_until_task_deadline(task_deadline):
                """Calculate days until task deadline"""
                if not task_deadline:
                    return None
                today = datetime.now().date()
                deadline_date = task_deadline.date()
                return (deadline_date - today).days
                
            return {
                'current_time': current_time,
                'now': lambda: datetime.now(),
                'csrf_token': generate_csrf,
                'user_active_tasks_count': get_user_active_tasks_count(),
                'get_admin_completed_notifications_count': get_admin_completed_notifications_count,
                'is_task_expired': is_task_expired,
                'is_task_expiring_soon': is_task_expiring_soon,
                'days_until_task_deadline': days_until_task_deadline
            }
        
        # Add root route that redirects to login
        @app.route('/')
        def index():
            return redirect(url_for('auth.login'))
            
        # Database connection error handler
        @app.errorhandler(OperationalError)
        def handle_db_connection_error(error):
            logger.error(f"Database connection error: {str(error)}")
            
            # Check if it's a table not found error (schema issue) rather than a connection issue
            if "doesn't exist" in str(error) or "Table" in str(error) or "Unknown table" in str(error):
                flash_message = ("ERRORE STRUTTURA DATABASE:<br>"
                               "- IL DISPOSITIVO CONNESSO HA UN DATABASE NON COMPATIBILE.<br>"
                               "- VERIFICARE DI AVER SELEZIONATO LA BILANCIA MASTER CORRETTA.")
                flash(flash_message, "error")
                return render_template('errors/db_structure_error.html', error=str(error)), 500
            else:
                # Connection error (standard case)
                flash_message = ("NON RIESCO A CONNETTERMI ALLA BILANCIA MASTER:<br>"
                               "- CONTROLLARE IL CAVO INTERNET LE LUCI LED SE SONO ACCESE.<br>"
                               "- CONTROLLARE SE LA BILANCIA E' ACCESA.")
                flash(flash_message, "error")
                return render_template('errors/db_connection_error.html'), 500
        
        @app.errorhandler(SQLAlchemyError)
        def handle_sqlalchemy_error(error):
            logger.error(f"SQLAlchemy error: {str(error)}")
            
            # Check if it's a schema/table issue
            if "doesn't exist" in str(error) or "Table" in str(error) or "Unknown table" in str(error):
                flash_message = ("ERRORE STRUTTURA DATABASE:<br>"
                               "- IL DISPOSITIVO CONNESSO HA UN DATABASE NON COMPATIBILE.<br>"
                               "- VERIFICARE DI AVER SELEZIONATO LA BILANCIA MASTER CORRETTA.")
                flash(flash_message, "error")
                return render_template('errors/db_structure_error.html', error=str(error)), 500
            else:
                flash_message = ("ERRORE DATABASE:<br>"
                               "- SI È VERIFICATO UN ERRORE DURANTE L'ACCESSO AL DATABASE.<br>"
                               "- VERIFICARE LA CONNESSIONE E LA COMPATIBILITÀ DEL DATABASE.")
                flash(flash_message, "error")
                return render_template('errors/db_error.html', error=str(error)), 500
        
        # Error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('errors/500.html'), 500
        
        @app.errorhandler(403)
        def forbidden_error(error):
            return render_template('errors/403.html'), 403
        
        # Setup logging
        if not app.debug and not os.environ.get('FLASK_DEBUG'):
            if not os.path.exists('logs'):
                os.mkdir('logs')
            try:
                # Utilizzo StreamHandler invece di RotatingFileHandler per evitare problemi di permessi
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                console_handler.setLevel(logging.INFO)
                app.logger.addHandler(console_handler)
                app.logger.setLevel(logging.INFO)
                app.logger.info('DBLogiX startup (console logging)')
            except Exception as e:
                print(f"Warning: Could not set up logging: {str(e)}")
                # Fall back to print
                print('DBLogiX startup - logging disabled due to error')
            
        # Enable CORS
        CORS(app)
        
    except Exception as e:
        logger.error(f"Error initializing application: {str(e)}")
        print(f"Application initialization error: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            traceback.print_tb(e.__traceback__)
    
    return app

# Create application instance
app = create_app()

@app.shell_context_processor
def make_shell_context():
    from app.models import User, Product, TicketHeader, TicketLine, ScanLog, Client, Company, Article, AlbaranCabecera, AlbaranLinea
    return {
        'db': db, 
        'User': User, 
        'Product': Product, 
        'TicketHeader': TicketHeader, 
        'TicketLine': TicketLine,
        'ScanLog': ScanLog,
        'Client': Client,
        'Company': Company,
        'Article': Article,
        'AlbaranCabecera': AlbaranCabecera,
        'AlbaranLinea': AlbaranLinea
    }

@app.route('/debug')
def debug_info():
    """Print debug info to help diagnose issues"""
    from flask import session, request
    import sys
    
    debug_info = {
        "Python Version": sys.version,
        "Flask Routes": [str(rule) for rule in app.url_map.iter_rules()],
        "Request Headers": dict(request.headers),
        "Session Data": dict(session) if session else "No session data",
        "Config": {k: str(v) for k, v in app.config.items() if k != 'SECRET_KEY'}
    }
    
    return jsonify(debug_info)

@app.route('/api/scan_network', methods=['GET'])
def scan_network():
    """Scan the local network for CS1200* devices"""
    try:
        # Get network prefix from query parameter, default to 192.168.1
        network_prefix = request.args.get('network_prefix', '192.168.1')
        
        logger.info(f"Starting scan of network {network_prefix}.* for CS1200* devices")
        
        # First check for responsive IPs on the network - simplified to reduce timeouts
        try:
            # First try a direct approach for most likely IP addresses
            most_likely_ips = [
                f"{network_prefix}.{suffix}" for suffix in [21, 22, 23, 24, 25, 100, 101, 200, 201, 250]
            ]
            
            responsive_ips = []
            for ip in most_likely_ips:
                try:
                    # Fast check for responsive IP using socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.3)  # Very short timeout
                    result = sock.connect_ex((ip, 3306))  # Try MySQL port first
                    sock.close()
                    
                    # Add responsive IP
                    if result == 0:
                        responsive_ips.append(ip)
                        logger.info(f"Found responsive MySQL server at {ip}")
                        
                    # If we didn't find a MySQL port, try a quick ping
                    else:
                        cmd = f"ping -n 1 -w 100 {ip}"
                        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        stdout, stderr = proc.communicate(timeout=1)
                        
                        if "Reply from" in stdout:
                            responsive_ips.append(ip)
                            logger.info(f"Found responsive device via ping at {ip}")
                except:
                    # Ignore errors and move on
                    pass
                
            # If we didn't find any IPs, scan more extensively but with constraints
            if not responsive_ips:
                # Try a more comprehensive scan only if the initial approach didn't work
                responsive_ips = get_responsive_ips(network_prefix)
                
            logger.info(f"Found {len(responsive_ips)} responsive IPs: {responsive_ips}")
            
            # Convert responsive IPs to CS1200 devices
            cs1200_devices = find_cs1200_devices(responsive_ips)
            logger.info(f"Found {len(cs1200_devices)} potential CS1200 devices")
            
            # Return devices found
            return jsonify({
                'success': True, 
                'devices': cs1200_devices,
                'network_prefix': network_prefix,
                'scanned_ips': len(responsive_ips)
            })
            
        except Exception as scan_error:
            logger.error(f"Error during network scan: {str(scan_error)}")
            # In caso di errore, ritorniamo un dispositivo fittizio per consentire test
            fallback_devices = [
                {'hostname': f"CS1200-{suffix}", 'ip': f"{network_prefix}.{suffix}"} 
                for suffix in [22, 23, 25]
            ]
            return jsonify({
                'success': True,
                'devices': fallback_devices,
                'network_prefix': network_prefix,
                'scanned_ips': 3,
                'message': 'Usando dispositivi predefiniti a causa di un errore di scansione'
            })
            
    except Exception as e:
        logger.error(f"Critical error in scan_network: {str(e)}")
        # Return a minimal response with error info
        return jsonify({
            'success': False, 
            'error': f"Errore di scansione: {str(e)}", 
            'network_prefix': request.args.get('network_prefix', '192.168.1')
        })

def get_responsive_ips(network_prefix):
    """Get a list of responsive IP addresses on the network quickly using ping sweep"""
    responsive_ips = []
    
    logger.info(f"Starting scan of {network_prefix} network for responsive IPs")
    
    try:
        # Define most common IP ranges for CS1200 devices
        # Only scan specific IP ranges that sono probabilmente utilizzati per dispositivi CS1200
        critical_ip_ranges = [
            list(range(20, 31)),      # Server range
            list(range(100, 105)),    # Common static IP range
            list(range(200, 205))     # Another common static range
        ]
        
        # Flatten list of IPs da controllare
        ip_to_check = []
        for ip_range in critical_ip_ranges:
            ip_to_check.extend(ip_range)
        
        # Add some individual important IPs che potrebbero non essere nelle ranges
        ip_to_check.extend([1, 10, 22, 23, 25, 110, 150, 210, 250])
        
        # Remove duplicates
        ip_to_check = list(set(ip_to_check))
        ip_to_check.sort()
        
        logger.info(f"Scanning {len(ip_to_check)} specific IPs in network {network_prefix}")
        
        # Scan each IP individually
        for i in ip_to_check:
            ip = f"{network_prefix}.{i}"
            
            # Direct socket connection check to port 3306 (MySQL) - faster and more reliable
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.2)  # Very short timeout
                result = sock.connect_ex((ip, 3306))
                sock.close()
                
                if result == 0:  # Port is open - very likely a CS1200
                    responsive_ips.append(ip)
                    logger.info(f"Found IP with MySQL port open: {ip}")
                    continue  # Skip ping check for this IP
            except:
                pass  # Continue with ping check
                
            # Fallback to ping for general connectivity
            try:
                # Use simpler ping approach for reliability
                ping_cmd = f"ping -n 1 -w 100 {ip}"
                process = subprocess.Popen(ping_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=1)  # Very short timeout
                
                if "Reply from" in stdout and ip not in responsive_ips:
                    responsive_ips.append(ip)
                    logger.info(f"Found responsive IP via ping: {ip}")
            except:
                # Ignore errors and continue
                pass
    
    except Exception as e:
        logger.error(f"Error in IP scanning: {str(e)}")
        # Even if we hit an error, continue with whatever IPs we've found
    
    logger.info(f"Completed scan. Found {len(responsive_ips)} responsive IPs: {responsive_ips}")
    return responsive_ips

def find_cs1200_devices(ips):
    """Find devices with hostnames starting with CS1200 using nbtstat"""
    cs1200_devices = []
    found_ips = []  # Keep track of already found IPs
    
    # First, treat all devices with open MySQL port (3306) as potential CS1200 devices
    for ip in ips:
        if ip in found_ips:
            continue
            
        try:
            # Check for MySQL port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex((ip, 3306))
            sock.close()
            
            if result == 0:  # MySQL port is open - assume it's a CS1200
                hostname = f"CS1200-{ip.split('.')[-1]}"
                logger.info(f"Found potential CS1200* device at {ip} (based on MySQL port)")
                found_ips.append(ip)
                cs1200_devices.append({'hostname': hostname, 'ip': ip})
                continue
        except:
            pass
    
    # Try to use nbtstat for remaining IPs, but with much shorter timeout
    for ip in ips:
        if ip in found_ips:
            continue
            
        try:
            # Simplify nbtstat command to reduce timeout risk
            nbt_command = f'nbtstat -A {ip}'
            nbt_process = subprocess.Popen(nbt_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            nbt_stdout, nbt_stderr = nbt_process.communicate(timeout=2)  # Shorter timeout
            
            # Look for hostname in output
            if nbt_stdout:
                name_match = re.search(r'([^\s]+)\s+<00>', nbt_stdout)
                if name_match:
                    hostname = name_match.group(1).strip()
                    if hostname.upper().startswith('CS1200'):
                        logger.info(f"Found CS1200* device at {ip}: {hostname}")
                        found_ips.append(ip)
                        cs1200_devices.append({'hostname': hostname, 'ip': ip})
        except Exception as e:
            logger.error(f"Error checking NetBIOS for {ip}: {str(e)}")
    
    # For IPs we still haven't identified, use a simpler approach for remaining IPs
    for ip in ips:
        if ip in found_ips:
            continue
            
        # Create the most likely name without nbtstat
        hostname = f"CS1200-{ip.split('.')[-1]}"
        cs1200_devices.append({'hostname': hostname, 'ip': ip})
        logger.info(f"Added fallback device at {ip} with hostname {hostname}")
    
    return cs1200_devices

def find_mysql_servers(network_prefix):
    """Find MySQL servers by trying to connect to port 3306"""
    mysql_servers = []
    
    # Get all responsive IPs rather than just checking predefined ones
    responsive_ips = get_responsive_ips(network_prefix)
    
    # Try to connect to each responsive IP
    for ip in responsive_ips:
        try:
            # Try TCP connection to MySQL port (3306)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1 second timeout
            sock.connect((ip, 3306))
            sock.close()
            # If connection succeeds, this IP has MySQL running
            mysql_servers.append({'hostname': "Possibile MySQL Server", 'ip': ip})
            logger.info(f"Found possible MySQL server at {ip}")
        except:
            # Connection failed, not a MySQL server or not responsive
            pass
    
    return mysql_servers

@app.route('/api/set_db_ip', methods=['POST'])
def set_db_ip():
    """Update the database connection to use the provided IP"""
    try:
        data = request.json
        if not data or 'ip' not in data:
            return jsonify({'success': False, 'error': 'No IP address provided'}), 400
        
        ip = data['ip']
        
        # Import here to avoid circular imports
        from app.config import REMOTE_DB_CONFIG, update_db_config
        
        # Debug logging
        logger.info(f"Current DB config before update: host={REMOTE_DB_CONFIG['host']}")
        logger.info(f"Attempting to update database connection to IP: {ip}")
        
        # Backup current config for rollback
        old_config = REMOTE_DB_CONFIG.copy()
        old_ip = REMOTE_DB_CONFIG['host']
        
        # Prepara la nuova configurazione
        new_config = REMOTE_DB_CONFIG.copy()
        new_config['host'] = ip
        
        # Update ALL config references to the IP using the centralized function
        update_db_config(new_config)
        
        # Update SQLAlchemy URI in Flask app
        app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{ip}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
        
        logger.info(f"Updated SQLALCHEMY_DATABASE_URI to: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        try:
            # First test a direct connection with PyMySQL
            logger.info(f"Testing direct connection to {ip}")
            import pymysql
            try:
                conn = pymysql.connect(
                    host=ip,
                    user=REMOTE_DB_CONFIG['user'],
                    password=REMOTE_DB_CONFIG['password'],
                    database=REMOTE_DB_CONFIG['database'],
                    port=REMOTE_DB_CONFIG['port'],
                    connect_timeout=5,
                    charset='utf8'
                )
                conn.ping()
                conn.close()
                logger.info(f"Direct connection to {ip} successful")
                
                # Se la connessione diretta è riuscita, non è necessario testare con SQLAlchemy
                # che potrebbe fallire per altri motivi
                logger.info(f"Skipping SQLAlchemy test since direct connection was successful")
                
                # La configurazione è già stata aggiornata dalla funzione update_db_config
                logger.info(f"Database configuration updated successfully to {ip}")
                
                logger.info(f"Database connection updated to {ip}")
                return jsonify({
                    'success': True, 
                    'message': f'Connessione al database aggiornata a {ip}',
                    'redirect': url_for('auth.login')
                })
            except Exception as pymysql_error:
                # Clean up error message to ensure the correct IP is shown
                error_msg = str(pymysql_error)
                # If error contains a wrong IP, replace it with the correct one
                if "Can't connect to MySQL server on" in error_msg and ip not in error_msg:
                    error_msg = error_msg.replace("Can't connect to MySQL server on", f"Can't connect to MySQL server on '{ip}'")
                logger.error(f"Direct connection to {ip} failed: {error_msg}")
                raise Exception(f"Direct connection to {ip} failed: {error_msg}")
                
        except Exception as db_error:
            # Rollback to old config if connection fails
            logger.error(f"Rolling back configuration to {old_ip}")
            update_db_config(old_config)
            app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{REMOTE_DB_CONFIG['user']}:{REMOTE_DB_CONFIG['password']}@{old_ip}:{REMOTE_DB_CONFIG['port']}/{REMOTE_DB_CONFIG['database']}?charset=utf8"
            
            # Create a custom error message that clearly indicates both IPs
            error_msg = str(db_error)
            # If the error message contains the wrong IP address, fix it
            if '192.168.1.25' in error_msg and ip != '192.168.1.25':
                error_msg = error_msg.replace('192.168.1.25', ip)
            
            logger.error(f"Failed to connect to database at {ip}: {error_msg}")
            return jsonify({'success': False, 'error': f'Impossibile connettersi al database a {ip}: {error_msg}'}), 500
            
    except Exception as e:
        logger.error(f"Error setting DB IP: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_db_connection', methods=['POST'])
def test_db_connection():
    """Test a database connection without changing the configuration"""
    try:
        data = request.json
        if not data or 'ip' not in data:
            return jsonify({'success': False, 'error': 'No IP address provided'}), 400
        
        ip = data['ip']
        
        # Import here to avoid circular imports
        from app.config import REMOTE_DB_CONFIG
        
        logger.info(f"Testing connection to database at {ip}")
        
        # Try direct connection
        try:
            import pymysql
            conn = pymysql.connect(
                host=ip,
                user=REMOTE_DB_CONFIG['user'],
                password=REMOTE_DB_CONFIG['password'],
                database=REMOTE_DB_CONFIG['database'],
                port=REMOTE_DB_CONFIG['port'],
                connect_timeout=5,
                charset='utf8'
            )
            conn.ping()
            conn.close()
            
            return jsonify({
                'success': True, 
                'message': f'Test di connessione a {ip} riuscito'
            })
        except Exception as conn_error:
            logger.error(f"Test connection to {ip} failed: {str(conn_error)}")
            return jsonify({
                'success': False, 
                'error': f'Test di connessione a {ip} fallito: {str(conn_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error testing DB connection: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    uploads_dir = os.path.join(app.root_path, 'Uploads')
    return send_from_directory(uploads_dir, filename)

# Run application if this file is executed directly
if __name__ == '__main__':
    # Log current database configuration
    from app.config import REMOTE_DB_CONFIG
    logger.info(f"Starting application with database configuration: host={REMOTE_DB_CONFIG['host']}, database={REMOTE_DB_CONFIG['database']}")
    
    # Using HTTPS with self-signed certificates for camera access
    app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('cert.pem', 'key.pem')) 