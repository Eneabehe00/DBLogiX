from flask import Flask, render_template, jsonify
from flask_login import LoginManager, login_required
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS
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
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Load configuration
    try:
        app.config.from_object('config.Config')
        
        # Override config with environment variables if present
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config.get('SECRET_KEY', 'dev-key-for-dblogix'))
        
        # Set debug mode to True
        app.config['DEBUG'] = True
        
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
        from ddt import ddt_bp
        from clients import clients_bp
        from articles import articles_bp
        
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(warehouse_bp, url_prefix='/warehouse')
        app.register_blueprint(admin_bp, url_prefix='/admin')
        app.register_blueprint(ddt_bp, url_prefix='/ddt')
        app.register_blueprint(clients_bp, url_prefix='/clients')
        app.register_blueprint(articles_bp, url_prefix='/articles')
        
        # Register template filters
        from utils import format_price, format_weight, current_time, b64encode
        
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
            
        # Setup debug toolbar
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
            toolbar = DebugToolbarExtension(app)
            logger.info("Debug toolbar enabled")
        except ImportError:
            logger.warning("Flask-DebugToolbar not installed. Debug toolbar will not be available.")
            
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
    from models import User, Product, TicketHeader, TicketLine, ScanLog, Client, DDTHead, DDTLine, Company, Article
    return {
        'db': db, 
        'User': User, 
        'Product': Product, 
        'TicketHeader': TicketHeader, 
        'TicketLine': TicketLine,
        'ScanLog': ScanLog,
        'Client': Client,
        'DDTHead': DDTHead,
        'DDTLine': DDTLine,
        'Company': Company,
        'Article': Article
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

# Run application if this file is executed directly
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 