import os
import logging
from logging.handlers import RotatingFileHandler
import sys

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
    
# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/dblogix.log', maxBytes=10240, backupCount=5),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)
logger.info('Starting DBLogiX application')

try:
    # Import Flask application - don't import db here to avoid circular dependencies
    from app import app
    
    # Import db directly from models now for database operations
    from models import db
    
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
        host = os.environ.get('FLASK_HOST', '0.0.0.0')
        port = int(os.environ.get('FLASK_PORT', 5000))
        debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
        
        logger.info(f'Running application on {host}:{port} (debug={debug})')
        app.run(host=host, port=port, debug=debug)
        
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