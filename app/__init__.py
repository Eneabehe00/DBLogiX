"""
DBLogiX App Package
Re-exports the create_app function from the main app module
"""

def create_app():
    """
    Create Flask application
    This function imports and calls the actual create_app from the main app.py file
    Handles both development and PyInstaller compiled environments
    """
    import sys
    import os
    from pathlib import Path
    
    # Check if we're running in a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        # In this case, the app.py module should be available directly as 'main_app'
        # since PyInstaller compiles it into the executable
        try:
            # Try to import the main app module that was compiled with PyInstaller
            # PyInstaller renames the main module, so we need to find it
            import importlib
            
            # The main app.py should be available as a compiled module
            # Let's try different possible names
            possible_names = ['main_app', 'app_main', '__main__']
            main_app = None
            
            for name in possible_names:
                try:
                    main_app = importlib.import_module(name)
                    if hasattr(main_app, 'create_app'):
                        break
                except ImportError:
                    continue
            
            if main_app and hasattr(main_app, 'create_app'):
                return main_app.create_app()
            
            # If the above doesn't work, try to load the app.py content directly
            # since it should be embedded in the PyInstaller bundle
            import runpy
            import tempfile
            
            # Get the bundle directory
            bundle_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
            
            # Try to find and execute app.py content from the bundle
            app_py_path = Path(bundle_dir) / 'app.py'
            if app_py_path.exists():
                # Load app.py as a module
                import importlib.util
                spec = importlib.util.spec_from_file_location("main_app", app_py_path)
                main_app = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(main_app)
                return main_app.create_app()
            
            # Last resort: try to import app directly (might work if PyInstaller configured correctly)
            try:
                # Import the module that contains our Flask app
                # This should work if the app.py was properly included in the build
                sys.path.insert(0, str(bundle_dir))
                
                # Import all the necessary modules first
                import flask
                from flask import Flask
                
                # Now import our app module
                from . import models, config, auth
                import modules.warehouse
                import modules.admin
                import modules.ddt
                import modules.clients
                import modules.articles
                import modules.sections
                import modules.fattura_pa
                import services.chat
                import modules.tasks
                
                # Create the app directly here since we have all the components
                app = Flask(__name__)
                
                # Load configuration
                app.config.from_object('app.config.Config')
                
                # Initialize CSRF protection
                from flask_wtf.csrf import CSRFProtect
                csrf = CSRFProtect(app)
                
                # Initialize extensions
                from .models import db
                db.init_app(app)
                
                # Setup login manager
                from flask_login import LoginManager
                login_manager = LoginManager()
                login_manager.login_view = 'auth.login'
                login_manager.init_app(app)
                
                @login_manager.user_loader
                def load_user(id):
                    from .models import User
                    return User.query.get(int(id))
                
                # Register blueprints
                from modules.warehouse import warehouse_bp
                from .auth import auth_bp
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
                
                # Add root route that redirects to login (missing in PyInstaller version)
                from flask import redirect, url_for, render_template, flash
                @app.route('/')
                def index():
                    return redirect(url_for('auth.login'))
                
                # Add error handlers (missing in PyInstaller version)
                from sqlalchemy.exc import OperationalError, SQLAlchemyError
                
                @app.errorhandler(OperationalError)
                def handle_db_connection_error(error):
                    if "doesn't exist" in str(error) or "Table" in str(error) or "Unknown table" in str(error):
                        flash_message = ("ERRORE STRUTTURA DATABASE:<br>"
                                       "- IL DISPOSITIVO CONNESSO HA UN DATABASE NON COMPATIBILE.<br>"
                                       "- VERIFICARE DI AVER SELEZIONATO LA BILANCIA MASTER CORRETTA.")
                        flash(flash_message, "error")
                        return render_template('errors/db_structure_error.html', error=str(error)), 500
                    else:
                        flash_message = ("NON RIESCO A CONNETTERMI ALLA BILANCIA MASTER:<br>"
                                       "- CONTROLLARE IL CAVO INTERNET LE LUCI LED SE SONO ACCESE.<br>"
                                       "- CONTROLLARE SE LA BILANCIA E' ACCESA.")
                        flash(flash_message, "error")
                        return render_template('errors/db_connection_error.html'), 500
                
                @app.errorhandler(404)
                def not_found_error(error):
                    return render_template('errors/404.html'), 404
                
                @app.errorhandler(500)
                def internal_error(error):
                    from .models import db
                    db.session.rollback()
                    return render_template('errors/500.html'), 500
                
                return app
                
            except Exception as e:
                raise ImportError(f"Could not create Flask app in PyInstaller environment: {e}")
                
        except Exception as e:
            raise ImportError(f"Could not load app in PyInstaller bundle: {e}")
    
    else:
        # Running in development environment
        # Get the root directory (parent of app/ directory)
        root_dir = Path(__file__).parent.parent
        
        # Add root directory to sys.path if not already there
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))
        
        # Import the main app module from root directory
        import importlib.util
        app_py_path = root_dir / 'app.py'
        
        if app_py_path.exists():
            # Load app.py as a module
            spec = importlib.util.spec_from_file_location("main_app", app_py_path)
            main_app = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_app)
            
            # Call create_app from the main app.py file
            return main_app.create_app()
        else:
            raise ImportError(f"Could not find app.py at {app_py_path}")
