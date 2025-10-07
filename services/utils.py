import pymysql
from app.config import REMOTE_DB_CONFIG, get_direct_connection_config
from flask import current_app, abort, flash
import logging
import decimal
from datetime import datetime
import locale
import base64
from flask_login import current_user
from functools import wraps

# Set up logger
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a database connection to the remote MySQL server.
    
    Returns:
        connection: A PyMySQL connection object if successful, None otherwise
    """
    try:
        # Get connection config from helper function
        config = get_direct_connection_config()
        
        connection = pymysql.connect(**config)
        logger.info("Database connection established successfully")
        return connection
    except Exception as e:
        error_msg = f"Database connection error: {str(e)}"
        logger.error(error_msg)
        if current_app:
            current_app.logger.error(error_msg)
        return None

def test_db_connection(config=None):
    """Test database connection with optional configuration.
    
    Args:
        config: Optional dictionary with database configuration parameters.
                If None, uses the default configuration.
    
    Returns:
        tuple: (success, message) where success is a boolean indicating if the
               connection was successful, and message is a descriptive string.
    """
    if config is None:
        config = get_direct_connection_config()
    
    try:
        connection = pymysql.connect(**config)
        
        # Test a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        
        connection.close()
        
        if result and result.get('1') == 1:
            return True, "Connection successful"
        else:
            return False, "Connection established but database query failed"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"

def format_price(value):
    """Format a price value with euro symbol"""
    if value is None:
        return '€ 0,00'
    try:
        # Set locale for European format (comma as decimal separator)
        locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
    except:
        # Fallback if locale not available
        try:
            locale.setlocale(locale.LC_ALL, 'it_IT')
        except:
            # If still fails, use the default locale
            pass
    
    try:
        return locale.currency(float(value), symbol='€', grouping=True)
    except:
        # If conversion fails, return a default formatted value
        return f'€ {float(value):.2f}'.replace('.', ',')

def format_weight(value, comportamiento=0):
    """Format a weight value with unit.
    
    Args:
        value: A numeric weight value.
        comportamiento: 0 for unit, 1 for kg. Default is 0.
    
    Returns:
        string: Formatted weight with appropriate unit (unit or kg).
    """
    if value is None:
        return "0" if comportamiento == 0 else "0,000 kg"
    
    try:
        if comportamiento == 0:  # Unità
            if isinstance(value, decimal.Decimal):
                # Per le unità mostriamo senza decimali
                formatted_value = f"{int(value)} unità"
            else:
                formatted_value = f"{int(float(value))} unità"
        else:  # Kg
            if isinstance(value, decimal.Decimal):
                # Handle Decimal objects directly to avoid float precision issues
                formatted_value = f"{value:.3f} kg".replace('.', ',')
            else:
                formatted_value = f"{float(value):.3f} kg".replace('.', ',')
        return formatted_value
    except (ValueError, TypeError):
        return "0" if comportamiento == 0 else "0,000 kg"

def safe_execute_query(query, params=None, fetch_all=True):
    """Execute a SQL query safely and return the results.
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Parameters for the query
        fetch_all (bool): Whether to fetch all results or just one
        
    Returns:
        tuple: (success, result/error_message)
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return False, "Failed to establish database connection"
        
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            
            if fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.fetchone()
                
        conn.close()
        return True, result
    except Exception as e:
        if conn:
            conn.close()
        error_msg = f"Query execution error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def current_time():
    """Return the current datetime object for use in templates."""
    return datetime.now()

def b64encode(data):
    """Encode binary data as base64 for use in templates."""
    if data is None:
        return ''
    try:
        return base64.b64encode(data).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image: {str(e)}")
        return ''

def admin_required(f):
    """
    Decorator to require admin permissions for a route.
    If user is not admin, it will abort with a 403 error.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    """
    Helper function to check if current user is admin.
    Returns True if user has admin role, False otherwise.
    """
    return current_user.is_authenticated and current_user.is_admin

# ===== LOT MANAGEMENT FUNCTIONS =====

def generate_lot_from_timestamp(ticket_date, format_type='ddmmyyyy'):
    """
    Generate a lot number based on ticket timestamp.
    
    Args:
        ticket_date (datetime): The date of the ticket
        format_type (str): Format type - 'ddmmyyyy' or 'yyyymmdd'
    
    Returns:
        str: Lot number based on timestamp
    """
    if not ticket_date:
        return ""
    
    try:
        if format_type == 'yyyymmdd':
            return ticket_date.strftime('%Y%m%d')
        else:  # Default ddmmyyyy
            return ticket_date.strftime('%d%m%Y')
    except Exception as e:
        logger.error(f"Error generating lot from timestamp: {str(e)}")
        return ""

def get_ticket_lot_info(ticket, ticket_line=None):
    """
    Get lot information for a ticket based on configuration.
    
    Args:
        ticket: TicketHeader object
        ticket_line: Optional TicketLine object (for TextoLote)
    
    Returns:
        dict: Lot information with 'lot_number', 'lot_source', 'display_text'
    """
    try:
        # Import here to avoid circular imports
        from app.config import get_lot_config_from_file
        from app.models import SystemConfig
        
        lot_config = get_lot_config_from_file()
        # Usa il database come fallback se il file non ha il valore
        lot_mode = lot_config.get('lot_mode') or SystemConfig.get_config('lot_mode', 'disabled')
        
        if lot_mode == 'disabled':
            return {
                'lot_number': '',
                'lot_source': 'disabled',
                'display_text': ''
            }
        
        elif lot_mode == 'timestamp':
            lot_format = lot_config.get('lot_timestamp_format') or SystemConfig.get_config('lot_timestamp_format', 'ddmmyyyy')
            lot_number = generate_lot_from_timestamp(ticket.Fecha, lot_format)
            return {
                'lot_number': lot_number,
                'lot_source': 'timestamp',
                'display_text': f"LOTTO N: {lot_number}" if lot_number else ''
            }
        
        elif lot_mode == 'textoLote':
            # Debug logging per troubleshooting
            logger.info(f"DEBUG: Lot mode 'textoLote' - ticket_line exists: {ticket_line is not None}")
            if ticket_line:
                logger.info(f"DEBUG: ticket_line.TextoLote exists: {hasattr(ticket_line, 'TextoLote')}")
                if hasattr(ticket_line, 'TextoLote'):
                    logger.info(f"DEBUG: ticket_line.TextoLote value: '{ticket_line.TextoLote}'")
            
            if ticket_line and hasattr(ticket_line, 'TextoLote') and ticket_line.TextoLote:
                lot_text = str(ticket_line.TextoLote).strip()
                logger.info(f"DEBUG: Using TextoLote: '{lot_text}'")
                return {
                    'lot_number': lot_text,
                    'lot_source': 'textoLote',
                    'display_text': f"LOTTO: {lot_text}"
                }
            else:
                logger.info(f"DEBUG: No TextoLote found - returning empty")
                return {
                    'lot_number': '',
                    'lot_source': 'textoLote',
                    'display_text': ''
                }
        
        # Unknown mode
        return {
            'lot_number': '',
            'lot_source': 'unknown',
            'display_text': ''
        }
        
    except Exception as e:
        logger.error(f"Error getting ticket lot info: {str(e)}")
        return {
            'lot_number': '',
            'lot_source': 'error',
            'display_text': ''
        }

def format_lot_for_ddt(ticket, ticket_line=None):
    """
    Format lot information for DDT display.
    
    Args:
        ticket: TicketHeader object
        ticket_line: Optional TicketLine object
    
    Returns:
        str: Formatted lot text for DDT or empty string if disabled
    """
    try:
        from app.config import get_lot_config_from_file
        from app.models import SystemConfig
        
        lot_config = get_lot_config_from_file()
        
        # Check if lot display in DDT is enabled - usa il database come fallback
        display_in_ddt = lot_config.get('lot_display_in_ddt')
        if display_in_ddt is None:
            display_in_ddt = SystemConfig.get_config('lot_display_in_ddt', True)
        
        if not display_in_ddt:
            return ""
        
        lot_info = get_ticket_lot_info(ticket, ticket_line)
        
        if lot_info['lot_number']:
            return f" - {lot_info['display_text']}"
        
        return ""
        
    except Exception as e:
        logger.error(f"Error formatting lot for DDT: {str(e)}")
        return ""

def extract_lot_from_description(description):
    """
    Extract lot information from description text.
    
    Args:
        description (str): Full description that may contain lot information
    
    Returns:
        tuple: (clean_description, lot_number) where:
               - clean_description is the description without lot info
               - lot_number is the extracted lot number or empty string
    """
    import re
    
    if not description:
        return description, ""
    
    # Pattern per riconoscere il formato " - LOTTO N: XXXXXXXX" o " - LOTTO: XXXXXXXX"
    lot_pattern = r'\s*-\s*LOTTO\s*N?:\s*(.+?)$'
    
    match = re.search(lot_pattern, description, re.IGNORECASE)
    if match:
        lot_number = match.group(1).strip()
        # Rimuovi la parte del lotto dalla descrizione
        clean_description = re.sub(lot_pattern, '', description, flags=re.IGNORECASE).strip()
        return clean_description, lot_number
    
    return description, ""

def get_lot_config_display():
    """
    Get lot configuration for display purposes.
    
    Returns:
        dict: Configuration with user-friendly labels
    """
    try:
        from app.config import get_lot_config_from_file
        from app.models import SystemConfig
        
        lot_config = get_lot_config_from_file()
        
        mode_labels = {
            'disabled': 'Disabilitato',
            'timestamp': 'Basato su data ticket',
            'textoLote': 'Basato su campo TextoLote'
        }
        
        format_labels = {
            'ddmmyyyy': 'gg/mm/aaaa (es. 10072025)',
            'yyyymmdd': 'aaaa/mm/gg (es. 20250710)'
        }
        
        # Usa il database come fallback per tutti i valori
        lot_mode = lot_config.get('lot_mode') or SystemConfig.get_config('lot_mode', 'disabled')
        timestamp_format = lot_config.get('lot_timestamp_format') or SystemConfig.get_config('lot_timestamp_format', 'ddmmyyyy')
        display_in_ticket = lot_config.get('lot_display_in_ticket')
        if display_in_ticket is None:
            display_in_ticket = SystemConfig.get_config('lot_display_in_ticket', True)
        display_in_ddt = lot_config.get('lot_display_in_ddt')
        if display_in_ddt is None:
            display_in_ddt = SystemConfig.get_config('lot_display_in_ddt', True)
        
        return {
            'mode': lot_mode,
            'mode_label': mode_labels.get(lot_mode, 'Sconosciuto'),
            'timestamp_format': timestamp_format,
            'timestamp_format_label': format_labels.get(timestamp_format, 'Formato sconosciuto'),
            'display_in_ticket': display_in_ticket,
            'display_in_ddt': display_in_ddt
        }
        
    except Exception as e:
        logger.error(f"Error getting lot config display: {str(e)}")
        return {
            'mode': 'disabled',
            'mode_label': 'Errore configurazione',
            'timestamp_format': 'ddmmyyyy',
            'timestamp_format_label': 'gg/mm/aaaa',
            'display_in_ticket': False,
            'display_in_ddt': False
        } 