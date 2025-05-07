import pymysql
from config import REMOTE_DB_CONFIG, get_direct_connection_config
from flask import current_app
import logging
import decimal

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
    """Format a price value with currency symbol.
    
    Args:
        value: A numeric price value.
    
    Returns:
        string: Formatted price with Euro symbol.
    """
    if value is None:
        return "€0,00"
    
    try:
        if isinstance(value, decimal.Decimal):
            # Handle Decimal objects directly to avoid float precision issues
            formatted_value = f"€{value:.2f}".replace('.', ',')
        else:
            formatted_value = f"€{float(value):.2f}".replace('.', ',')
        return formatted_value
    except (ValueError, TypeError):
        return "€0,00"

def format_weight(value):
    """Format a weight value with unit.
    
    Args:
        value: A numeric weight value.
    
    Returns:
        string: Formatted weight with kg unit.
    """
    if value is None:
        return "0,000 kg"
    
    try:
        if isinstance(value, decimal.Decimal):
            # Handle Decimal objects directly to avoid float precision issues
            formatted_value = f"{value:.3f} kg".replace('.', ',')
        else:
            formatted_value = f"{float(value):.3f} kg".replace('.', ',')
        return formatted_value
    except (ValueError, TypeError):
        return "0,000 kg"

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