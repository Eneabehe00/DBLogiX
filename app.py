from flask import Flask, render_template
from flask_login import LoginManager
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime

# Initialize logger
logger = logging.getLogger(__name__)

# Import db from models directly - this avoids circular imports
from models import db

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    try:
        app.config.from_object('config.Config')
        
        # Override config with environment variables if present
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'dev-key-for-dblogix'))
        
        # Database configuration can be updated from environment
        db_host = os.environ.get('DB_HOST')
        db_user = os.environ.get('DB_USER')
        db_pass = os.environ.get('DB_PASSWORD')
        db_name = os.environ.get('DB_NAME')
        db_port = os.environ.get('DB_PORT')
        
        # Import here to avoid circular imports
        from config import REMOTE_DB_CONFIG
        
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
            from models import User
            return User.query.get(int(id))
        
        # Register blueprints
        from warehouse import warehouse_bp
        from auth import auth_bp
        from admin import admin_bp
        
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(warehouse_bp, url_prefix='/warehouse')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        
        # Register template filters
        from utils import format_price, format_weight, current_time
        
        @app.template_filter('price')
        def price_filter(value):
            return format_price(value)
        
        @app.template_filter('weight')
        def weight_filter(value):
            return format_weight(value)
        
        @app.context_processor
        def utility_processor():
            from datetime import datetime
            return {
                'current_time': current_time,
                'now': lambda: datetime.now()
            }
        
        # Error handlers
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('errors/500.html'), 500
        
        # Setup logging
        if not app.debug and not os.environ.get('FLASK_DEBUG'):
            if not os.path.exists('logs'):
                os.mkdir('logs')
            try:
                file_handler = RotatingFileHandler('logs/dblogix.log', maxBytes=10240, backupCount=5, delay=True)
                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)
                
                app.logger.setLevel(logging.INFO)
                app.logger.info('DBLogiX startup')
            except Exception as e:
                print(f"Warning: Could not set up file logging: {str(e)}")
                # Fall back to console logging
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                console_handler.setLevel(logging.INFO)
                app.logger.addHandler(console_handler)
                app.logger.setLevel(logging.INFO)
                app.logger.info('DBLogiX startup (console logging only)')
            
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
    from models import User, Product, TicketHeader, TicketLine, ScanLog
    return {
        'db': db, 
        'User': User, 
        'Product': Product, 
        'TicketHeader': TicketHeader, 
        'TicketLine': TicketLine,
        'ScanLog': ScanLog
    }

# Run application if this file is executed directly
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 