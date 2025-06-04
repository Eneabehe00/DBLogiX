from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db, User, ScanLog, Product, TicketHeader, Company, SystemConfig, ChatMessage, Client, AlbaranCabecera, AlbaranLinea
from forms import RegistrationForm, DbConfigForm, CompanyConfigForm, ResetPasswordForm, SystemConfigForm
from sqlalchemy import func, desc
from config import REMOTE_DB_CONFIG
import pymysql
from datetime import datetime, timedelta
import json
import os
import re
from functools import wraps
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Devi avere privilegi di amministratore per accedere a questa pagina.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Admin index redirecting to dashboard
@admin_bp.route('/')
@admin_required
def index():
    """Admin index page - redirects to dashboard"""
    return redirect(url_for('admin.dashboard'))

# Dashboard Section
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics and overview"""
    # User statistics
    total_users = User.query.count()
    admin_users = User.query.filter_by(is_admin=True).count()
    
    # Activity statistics (today)
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    
    today_scans = ScanLog.query.filter(
        ScanLog.timestamp >= today,
        ScanLog.timestamp < tomorrow
    ).count()
    
    checkout_scans = ScanLog.query.filter_by(action='checkout').count()
    view_scans = ScanLog.query.filter_by(action='view').count()
    
    # Product statistics
    products_count = Product.query.count()
    
    # Ticket statistics
    total_tickets = TicketHeader.query.count()
    processed_tickets = TicketHeader.query.filter_by(Enviado=1).count()
    giacenza_tickets = TicketHeader.query.filter_by(Enviado=0).count()
    expired_tickets = TicketHeader.query.filter_by(Enviado=4).count()
    
    # Most active users (top 5)
    active_users = db.session.query(
        User.username,
        func.count(ScanLog.id).label('scan_count')
    ).join(ScanLog).group_by(User.id).order_by(
        desc('scan_count')
    ).limit(5).all()
    
    # Last 7 days activity
    last_week = datetime.utcnow() - timedelta(days=7)
    daily_activity = db.session.query(
        func.date(ScanLog.timestamp).label('date'),
        func.count(ScanLog.id).label('count')
    ).filter(ScanLog.timestamp >= last_week).group_by(
        'date'
    ).order_by('date').all()
    
    # Format data for charts
    dates = [item[0].strftime('%d/%m') for item in daily_activity]
    counts = [item[1] for item in daily_activity]
    
    activity_data = {
        'labels': dates,
        'data': counts
    }
    
    return render_template('admin/dashboard/statistics.html',
                         total_users=total_users,
                         admin_users=admin_users,
                         today_scans=today_scans,
                         checkout_scans=checkout_scans,
                         view_scans=view_scans,
                         products_count=products_count,
                         total_tickets=total_tickets,
                         processed_tickets=processed_tickets,
                         giacenza_tickets=giacenza_tickets,
                         expired_tickets=expired_tickets,
                         active_users=active_users,
                         activity_data=json.dumps(activity_data))

@admin_bp.route('/dashboard/scan_logs')
@admin_required
def scan_logs():
    """View all scan logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    logs = ScanLog.query.join(User).order_by(
        ScanLog.timestamp.desc()
    ).paginate(page=page, per_page=per_page)
    
    return render_template('admin/dashboard/scan_logs.html', logs=logs)

# Configurazioni Section
@admin_bp.route('/configurazioni/users')
@admin_required
def manage_users():
    """User management - list, create, edit users"""
    users = User.query.all()
    return render_template('admin/configurazioni/users.html', users=users)

@admin_bp.route('/configurazioni/users/new', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add a new user"""
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data,
            screen_task=form.screen_task.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Utente aggiunto con successo!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/configurazioni/user_form.html', form=form, title='Add User')

@admin_bp.route('/configurazioni/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit an existing user"""
    user = User.query.get_or_404(user_id)
    form = RegistrationForm(obj=user)
    
    # Don't require password for editing
    del form.password
    del form.password2
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        user.screen_task = form.screen_task.data
        db.session.commit()
        flash('Utente aggiornato con successo!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/configurazioni/user_form.html', form=form, title='Edit User', edit_mode=True)

@admin_bp.route('/configurazioni/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('Non puoi eliminare il tuo stesso account!', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Utente eliminato con successo!', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/configurazioni/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@admin_required
def reset_password(user_id):
    """Reset a user's password"""
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Password reimpostata con successo!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/configurazioni/reset_password.html', user=user, form=form)

@admin_bp.route('/configurazioni/general-config', methods=['GET', 'POST'])
@admin_required
def general_config():
    """Unified configuration page with tabs for DB, Company, and System settings"""
    
    # Migrazione automatica del logo esistente al nome fisso
    def migrate_existing_logo():
        """Migra eventuali loghi esistenti al nome fisso LogoDDT.png"""
        try:
            logo_dir = os.path.join('static', 'uploads', 'logos')
            if os.path.exists(logo_dir):
                for filename in os.listdir(logo_dir):
                    if filename.startswith('logo_') and filename.endswith(('.png', '.jpg', '.jpeg')):
                        old_path = os.path.join(logo_dir, filename)
                        new_path = os.path.join(logo_dir, 'LogoDDT.png')
                        
                        # Rimuovi il LogoDDT.png esistente se presente
                        if os.path.exists(new_path):
                            os.remove(new_path)
                        
                        # Rinomina il file
                        os.rename(old_path, new_path)
                        flash(f'Logo esistente {filename} migrato automaticamente a LogoDDT.png', 'info')
                        break  # Prendi solo il primo logo trovato
        except Exception as e:
            pass  # Ignora eventuali errori di migrazione
    
    # Esegui la migrazione del logo
    migrate_existing_logo()
    
    db_form = DbConfigForm(prefix="db")
    company_form = CompanyConfigForm(prefix="company")
    system_form = SystemConfigForm(prefix="system")
    
    # Pre-fill forms with current config
    if request.method == 'GET':
        # DB form
        db_form.host.data = REMOTE_DB_CONFIG['host']
        db_form.user.data = REMOTE_DB_CONFIG['user']
        db_form.password.data = REMOTE_DB_CONFIG['password']
        db_form.database.data = REMOTE_DB_CONFIG['database']
        db_form.port.data = str(REMOTE_DB_CONFIG['port'])
        
        # Company form
        company = Company.query.first()
        if company:
            company_form.nombre_empresa.data = company.NombreEmpresa
            company_form.cif_vat.data = company.CIF_VAT
            company_form.telefono.data = company.Telefono1
            company_form.direccion.data = company.Direccion
            company_form.cod_postal.data = company.CodPostal
            company_form.poblacion.data = company.Poblacion
            company_form.provincia.data = company.Provincia
        
        # System form - Carica tutte le configurazioni
        system_form.expiry_warning_days.data = SystemConfig.get_config('expiry_warning_days', 7)
        system_form.articles_per_package.data = SystemConfig.get_config('articles_per_package', 5)
        
        # Email configurations
        system_form.smtp_server.data = SystemConfig.get_config('smtp_server', '')
        system_form.smtp_port.data = SystemConfig.get_config('smtp_port', 587)
        system_form.smtp_username.data = SystemConfig.get_config('smtp_username', '')
        system_form.smtp_password.data = SystemConfig.get_config('smtp_password', '')
        system_form.smtp_use_tls.data = SystemConfig.get_config('smtp_use_tls', True)
        system_form.admin_email.data = SystemConfig.get_config('admin_email', '')
        system_form.enable_email_notifications.data = SystemConfig.get_config('enable_email_notifications', False)
        
        # Backup configurations
        system_form.backup_frequency_hours.data = SystemConfig.get_config('backup_frequency_hours', 24)
        system_form.backup_retention_days.data = SystemConfig.get_config('backup_retention_days', 7)
        system_form.backup_path.data = SystemConfig.get_config('backup_path', 'backups')
        
        # Database timeout configurations
        system_form.db_connect_timeout.data = SystemConfig.get_config('db_connect_timeout', 10)
        system_form.db_read_timeout.data = SystemConfig.get_config('db_read_timeout', 30)
        system_form.db_write_timeout.data = SystemConfig.get_config('db_write_timeout', 30)
        
        # Localization configurations
        system_form.timezone.data = SystemConfig.get_config('timezone', 'Europe/Rome')
        system_form.date_format.data = SystemConfig.get_config('date_format', '%d/%m/%Y')
        
        # Alert configurations
        system_form.enable_stock_alerts.data = SystemConfig.get_config('enable_stock_alerts', True)
        system_form.stock_alert_threshold.data = SystemConfig.get_config('stock_alert_threshold', 10)
        system_form.expiry_check_frequency_hours.data = SystemConfig.get_config('expiry_check_frequency_hours', 6)
        
        # Logging configurations
        system_form.log_level.data = SystemConfig.get_config('log_level', 'INFO')
        system_form.log_max_size_mb.data = SystemConfig.get_config('log_max_size_mb', 10)
        
        # Session configurations
        system_form.session_timeout_hours.data = SystemConfig.get_config('session_timeout_hours', 2)
        system_form.session_inactivity_minutes.data = SystemConfig.get_config('session_inactivity_minutes', 30)
        
        # Chat configurations
        system_form.enable_chat_auto_cleanup.data = SystemConfig.get_config('enable_chat_auto_cleanup', False)
        system_form.chat_cleanup_frequency_days.data = SystemConfig.get_config('chat_cleanup_frequency_days', 7)
        system_form.enable_chat_auto_backup.data = SystemConfig.get_config('enable_chat_auto_backup', True)
        system_form.chat_backup_retention_days.data = SystemConfig.get_config('chat_backup_retention_days', 30)
        system_form.chat_backup_path.data = SystemConfig.get_config('chat_backup_path', 'Backup/Chat')
        
        # Clienti backup configurations
        system_form.enable_clienti_auto_backup.data = SystemConfig.get_config('enable_clienti_auto_backup', True)
        system_form.clienti_backup_frequency_days.data = SystemConfig.get_config('clienti_backup_frequency_days', 7)
        system_form.clienti_backup_retention_days.data = SystemConfig.get_config('clienti_backup_retention_days', 30)
        system_form.clienti_backup_path.data = SystemConfig.get_config('clienti_backup_path', 'Backup/Clienti')
        
        # DDT backup configurations
        system_form.enable_ddt_auto_backup.data = SystemConfig.get_config('enable_ddt_auto_backup', True)
        system_form.ddt_backup_frequency_days.data = SystemConfig.get_config('ddt_backup_frequency_days', 7)
        system_form.ddt_backup_retention_days.data = SystemConfig.get_config('ddt_backup_retention_days', 30)
        system_form.ddt_backup_path.data = SystemConfig.get_config('ddt_backup_path', 'Backup/DDT')
        
        # Fatture backup configurations
        system_form.enable_fatture_auto_backup.data = SystemConfig.get_config('enable_fatture_auto_backup', True)
        system_form.fatture_backup_frequency_days.data = SystemConfig.get_config('fatture_backup_frequency_days', 7)
        system_form.fatture_backup_retention_days.data = SystemConfig.get_config('fatture_backup_retention_days', 30)
        system_form.fatture_backup_path.data = SystemConfig.get_config('fatture_backup_path', 'Backup/Fatture')
    
    # Handle DB config form submit
    if 'submit_db' in request.form and db_form.validate():
        if 'test_connection' in request.form:
            # Test the connection
            try:
                conn = pymysql.connect(
                    host=db_form.host.data,
                    user=db_form.user.data,
                    password=db_form.password.data,
                    database=db_form.database.data,
                    port=int(db_form.port.data),
                    connect_timeout=10
                )
                conn.close()
                flash('Database connesso!', 'success')
            except Exception as e:
                flash(f'Connessione fallita: {str(e)}', 'danger')
        else:
            # Save the configuration
            try:
                # Read the current config file
                with open('config.py', 'r') as f:
                    config_content = f.read()
                
                # Update the REMOTE_DB_CONFIG dictionary
                new_config = {
                    'host': db_form.host.data,
                    'user': db_form.user.data,
                    'password': db_form.password.data,
                    'database': db_form.database.data,
                    'port': int(db_form.port.data),
                    'connect_timeout': REMOTE_DB_CONFIG.get('connect_timeout', 10),
                    'read_timeout': REMOTE_DB_CONFIG.get('read_timeout', 30),
                    'write_timeout': REMOTE_DB_CONFIG.get('write_timeout', 30),
                    'charset': REMOTE_DB_CONFIG.get('charset', 'utf8'),
                    'use_unicode': REMOTE_DB_CONFIG.get('use_unicode', True),
                    'ssl_disabled': REMOTE_DB_CONFIG.get('ssl_disabled', True),
                    'cursorclass': REMOTE_DB_CONFIG.get('cursorclass', 'DictCursor')
                }
                
                # Format the new config content
                new_config_str = "REMOTE_DB_CONFIG = {\n"
                for key, value in new_config.items():
                    if isinstance(value, str):
                        new_config_str += f"    '{key}': '{value}',\n"
                    else:
                        new_config_str += f"    '{key}': {value},\n"
                new_config_str += "}"
                
                # Replace the old config with the new one
                updated_content = re.sub(r"REMOTE_DB_CONFIG = \{[^}]+\}", new_config_str, config_content)
                
                # Update the SQLALCHEMY_DATABASE_URI
                sqlalchemy_uri = f"SQLALCHEMY_DATABASE_URI = f\"mysql+pymysql://{new_config['user']}:{new_config['password']}@{new_config['host']}:{new_config['port']}/{new_config['database']}\""
                
                updated_content = re.sub(r"SQLALCHEMY_DATABASE_URI = f\"mysql\+pymysql://[^\"]+\"", sqlalchemy_uri, updated_content)
                
                # Write the updated content back to the file
                with open('config.py', 'w') as f:
                    f.write(updated_content)
                
                flash('Configurazione database aggiornata!', 'success')
            except Exception as e:
                flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    # Handle Company config form submit
    if 'submit_company' in request.form and company_form.validate():
        try:
            # Get existing company or create new one
            company = Company.query.first()
            if not company:
                company = Company()
                db.session.add(company)
            
            # Update company data
            company.NombreEmpresa = company_form.nombre_empresa.data
            company.CIF_VAT = company_form.cif_vat.data
            company.Telefono1 = company_form.telefono.data
            company.Direccion = company_form.direccion.data
            company.CodPostal = company_form.cod_postal.data
            company.Poblacion = company_form.poblacion.data
            company.Provincia = company_form.provincia.data
            
            db.session.commit()
            flash('Configurazione azienda aggiornata!', 'success')
        except Exception as e:
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    # Handle System config form submit
    if 'submit_system' in request.form and system_form.validate():
        try:
            # Save basic system configurations
            SystemConfig.set_config('expiry_warning_days', system_form.expiry_warning_days.data,
                                   'Numero di giorni prima della scadenza per contrassegnare i ticket come "In Scadenza"', 'integer')
            SystemConfig.set_config('articles_per_package', system_form.articles_per_package.data,
                                   'Numero di articoli necessari per determinare un collo nei DDT', 'integer')
            
            # Save Email configurations
            if system_form.smtp_server.data:
                SystemConfig.set_config('smtp_server', system_form.smtp_server.data, 'Server SMTP per invio email', 'string')
            if system_form.smtp_port.data:
                SystemConfig.set_config('smtp_port', system_form.smtp_port.data, 'Porta server SMTP', 'integer')
            if system_form.smtp_username.data:
                SystemConfig.set_config('smtp_username', system_form.smtp_username.data, 'Username autenticazione SMTP', 'string')
            if system_form.smtp_password.data:
                SystemConfig.set_config('smtp_password', system_form.smtp_password.data, 'Password autenticazione SMTP', 'string')
            SystemConfig.set_config('smtp_use_tls', system_form.smtp_use_tls.data, 'Utilizza TLS per SMTP', 'boolean')
            if system_form.admin_email.data:
                SystemConfig.set_config('admin_email', system_form.admin_email.data, 'Email amministratore per notifiche', 'string')
            SystemConfig.set_config('enable_email_notifications', system_form.enable_email_notifications.data, 'Abilita notifiche email automatiche', 'boolean')
            
            # Save Backup configurations
            SystemConfig.set_config('backup_frequency_hours', system_form.backup_frequency_hours.data, 'Frequenza backup automatico in ore', 'integer')
            SystemConfig.set_config('backup_retention_days', system_form.backup_retention_days.data, 'Giorni di conservazione backup', 'integer')
            SystemConfig.set_config('backup_path', system_form.backup_path.data, 'Percorso di salvataggio backup', 'string')
            
            # Save Database timeout configurations
            SystemConfig.set_config('db_connect_timeout', system_form.db_connect_timeout.data, 'Timeout connessione database in secondi', 'integer')
            SystemConfig.set_config('db_read_timeout', system_form.db_read_timeout.data, 'Timeout lettura database in secondi', 'integer')
            SystemConfig.set_config('db_write_timeout', system_form.db_write_timeout.data, 'Timeout scrittura database in secondi', 'integer')
            
            # Save Localization configurations
            SystemConfig.set_config('timezone', system_form.timezone.data, 'Fuso orario sistema', 'string')
            SystemConfig.set_config('date_format', system_form.date_format.data, 'Formato visualizzazione date', 'string')
            
            # Handle logo upload
            if system_form.company_logo.data:
                try:
                    import os
                    from werkzeug.utils import secure_filename
                    
                    # Create uploads directory if it doesn't exist
                    upload_dir = os.path.join('static', 'uploads', 'logos')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Always use the fixed filename LogoDDT.png
                    filename = "LogoDDT.png"
                    filepath = os.path.join(upload_dir, filename)
                    
                    # Remove existing logo if it exists
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    
                    # Save the new logo with the fixed name
                    system_form.company_logo.data.save(filepath)
                    
                    # Save path in config
                    logo_path = f"uploads/logos/{filename}"
                    SystemConfig.set_config('company_logo_path', logo_path, 'Percorso logo aziendale per DDT', 'string')
                    flash('Logo caricato con successo!', 'success')
                except Exception as e:
                    flash(f'Errore caricamento logo: {str(e)}', 'warning')
            
            # Save Alert configurations
            SystemConfig.set_config('enable_stock_alerts', system_form.enable_stock_alerts.data, 'Abilita alert per stock minimo', 'boolean')
            SystemConfig.set_config('stock_alert_threshold', system_form.stock_alert_threshold.data, 'Soglia minima per alert stock', 'integer')
            SystemConfig.set_config('expiry_check_frequency_hours', system_form.expiry_check_frequency_hours.data, 'Frequenza controllo scadenze in ore', 'integer')
            
            # Save Logging configurations
            SystemConfig.set_config('log_level', system_form.log_level.data, 'Livello di logging sistema', 'string')
            SystemConfig.set_config('log_max_size_mb', system_form.log_max_size_mb.data, 'Dimensione massima file log in MB', 'integer')
            
            # Save Session configurations
            SystemConfig.set_config('session_timeout_hours', system_form.session_timeout_hours.data, 'Durata massima sessione in ore', 'integer')
            SystemConfig.set_config('session_inactivity_minutes', system_form.session_inactivity_minutes.data, 'Timeout inattività in minuti', 'integer')
            
            # Chat configurations
            SystemConfig.set_config('enable_chat_auto_cleanup', system_form.enable_chat_auto_cleanup.data, 'Abilita auto-pulizia chat', 'boolean')
            SystemConfig.set_config('chat_cleanup_frequency_days', system_form.chat_cleanup_frequency_days.data, 'Frequenza auto-pulizia chat in giorni', 'integer')
            SystemConfig.set_config('enable_chat_auto_backup', system_form.enable_chat_auto_backup.data, 'Abilita auto-backup chat', 'boolean')
            SystemConfig.set_config('chat_backup_retention_days', system_form.chat_backup_retention_days.data, 'Giorni di conservazione backup chat', 'integer')
            SystemConfig.set_config('chat_backup_path', system_form.chat_backup_path.data, 'Percorso backup chat', 'string')
            
            # Clienti backup configurations
            SystemConfig.set_config('enable_clienti_auto_backup', system_form.enable_clienti_auto_backup.data, 'Abilita auto-backup clienti', 'boolean')
            SystemConfig.set_config('clienti_backup_frequency_days', system_form.clienti_backup_frequency_days.data, 'Frequenza auto-backup clienti in giorni', 'integer')
            SystemConfig.set_config('clienti_backup_retention_days', system_form.clienti_backup_retention_days.data, 'Giorni di conservazione backup clienti', 'integer')
            SystemConfig.set_config('clienti_backup_path', system_form.clienti_backup_path.data, 'Percorso backup clienti', 'string')
            
            # DDT backup configurations
            SystemConfig.set_config('enable_ddt_auto_backup', system_form.enable_ddt_auto_backup.data, 'Abilita auto-backup DDT', 'boolean')
            SystemConfig.set_config('ddt_backup_frequency_days', system_form.ddt_backup_frequency_days.data, 'Frequenza auto-backup DDT in giorni', 'integer')
            SystemConfig.set_config('ddt_backup_retention_days', system_form.ddt_backup_retention_days.data, 'Giorni di conservazione backup DDT', 'integer')
            SystemConfig.set_config('ddt_backup_path', system_form.ddt_backup_path.data, 'Percorso backup DDT', 'string')
            
            # Fatture backup configurations
            SystemConfig.set_config('enable_fatture_auto_backup', system_form.enable_fatture_auto_backup.data, 'Abilita auto-backup fatture', 'boolean')
            SystemConfig.set_config('fatture_backup_frequency_days', system_form.fatture_backup_frequency_days.data, 'Frequenza auto-backup fatture in giorni', 'integer')
            SystemConfig.set_config('fatture_backup_retention_days', system_form.fatture_backup_retention_days.data, 'Giorni di conservazione backup fatture', 'integer')
            SystemConfig.set_config('fatture_backup_path', system_form.fatture_backup_path.data, 'Percorso backup fatture', 'string')
            
            # Update config.py for session timeout (requires app restart)
            try:
                with open('config.py', 'r') as f:
                    config_content = f.read()
                
                # Update PERMANENT_SESSION_LIFETIME
                new_session_timeout = f"PERMANENT_SESSION_LIFETIME = timedelta(hours={system_form.session_timeout_hours.data})"
                pattern = r"PERMANENT_SESSION_LIFETIME = timedelta\(hours=\d+\)"
                
                if re.search(pattern, config_content):
                    updated_content = re.sub(pattern, new_session_timeout, config_content)
                    with open('config.py', 'w') as f:
                        f.write(updated_content)
                    flash('Configurazione sessioni aggiornata nel file config.py. Riavvia l\'app per applicare le modifiche.', 'info')
            except Exception as e:
                flash(f'Attenzione: Impossibile aggiornare il timeout sessioni nel file config.py: {str(e)}', 'warning')
            
            flash('Configurazioni sistema aggiornate!', 'success')
            
        except Exception as e:
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    # Handle Chat config form submit
    if 'submit_chat' in request.form:
        try:
            # Get form data from request
            enable_auto_cleanup = request.form.get('enable_auto_cleanup') == 'on'
            cleanup_frequency = int(request.form.get('cleanup_frequency', 7))
            enable_auto_backup = request.form.get('enable_auto_backup') == 'on'
            backup_retention = int(request.form.get('backup_retention', 30))
            chat_backup_path = request.form.get('chat_backup_path', 'Backup/Chat')
            
            # Save configurations
            SystemConfig.set_config('enable_chat_auto_cleanup', enable_auto_cleanup, 'Abilita auto-pulizia chat', 'boolean')
            SystemConfig.set_config('chat_cleanup_frequency_days', cleanup_frequency, 'Frequenza auto-pulizia chat in giorni', 'integer')
            SystemConfig.set_config('enable_chat_auto_backup', enable_auto_backup, 'Abilita auto-backup chat', 'boolean')
            SystemConfig.set_config('chat_backup_retention_days', backup_retention, 'Giorni di conservazione backup chat', 'integer')
            SystemConfig.set_config('chat_backup_path', chat_backup_path, 'Percorso backup chat', 'string')
            
            flash('Configurazioni chat aggiornate!', 'success')
            
        except Exception as e:
            flash(f'Errore nel salvataggio configurazioni chat: {str(e)}', 'danger')
    
    # Handle Clienti config form submit
    if 'submit_clienti' in request.form:
        try:
            # Get form data from request
            enable_auto_backup = request.form.get('enable_clienti_auto_backup') == 'on'
            backup_frequency = int(request.form.get('clienti_backup_frequency_days', 7))
            backup_retention = int(request.form.get('clienti_backup_retention_days', 30))
            backup_path = request.form.get('clienti_backup_path', 'Backup/Clienti')
            
            # Save configurations
            SystemConfig.set_config('enable_clienti_auto_backup', enable_auto_backup, 'Abilita auto-backup clienti', 'boolean')
            SystemConfig.set_config('clienti_backup_frequency_days', backup_frequency, 'Frequenza auto-backup clienti in giorni', 'integer')
            SystemConfig.set_config('clienti_backup_retention_days', backup_retention, 'Giorni di conservazione backup clienti', 'integer')
            SystemConfig.set_config('clienti_backup_path', backup_path, 'Percorso backup clienti', 'string')
            
            flash('Configurazioni clienti aggiornate!', 'success')
            
        except Exception as e:
            flash(f'Errore nel salvataggio configurazioni clienti: {str(e)}', 'danger')
    
    # Handle DDT config form submit
    if 'submit_ddt' in request.form:
        try:
            # Get form data from request
            enable_auto_backup = request.form.get('enable_ddt_auto_backup') == 'on'
            backup_frequency = int(request.form.get('ddt_backup_frequency_days', 7))
            backup_retention = int(request.form.get('ddt_backup_retention_days', 30))
            backup_path = request.form.get('ddt_backup_path', 'Backup/DDT')
            
            # Save configurations
            SystemConfig.set_config('enable_ddt_auto_backup', enable_auto_backup, 'Abilita auto-backup DDT', 'boolean')
            SystemConfig.set_config('ddt_backup_frequency_days', backup_frequency, 'Frequenza auto-backup DDT in giorni', 'integer')
            SystemConfig.set_config('ddt_backup_retention_days', backup_retention, 'Giorni di conservazione backup DDT', 'integer')
            SystemConfig.set_config('ddt_backup_path', backup_path, 'Percorso backup DDT', 'string')
            
            flash('Configurazioni DDT aggiornate!', 'success')
            
        except Exception as e:
            flash(f'Errore nel salvataggio configurazioni DDT: {str(e)}', 'danger')
    
    # Handle Fatture config form submit
    if 'submit_fatture' in request.form:
        try:
            # Get form data from request
            enable_auto_backup = request.form.get('enable_fatture_auto_backup') == 'on'
            backup_frequency = int(request.form.get('fatture_backup_frequency_days', 7))
            backup_retention = int(request.form.get('fatture_backup_retention_days', 30))
            backup_path = request.form.get('fatture_backup_path', 'Backup/Fatture')
            
            # Save configurations
            SystemConfig.set_config('enable_fatture_auto_backup', enable_auto_backup, 'Abilita auto-backup fatture', 'boolean')
            SystemConfig.set_config('fatture_backup_frequency_days', backup_frequency, 'Frequenza auto-backup fatture in giorni', 'integer')
            SystemConfig.set_config('fatture_backup_retention_days', backup_retention, 'Giorni di conservazione backup fatture', 'integer')
            SystemConfig.set_config('fatture_backup_path', backup_path, 'Percorso backup fatture', 'string')
            
            flash('Configurazioni fatture aggiornate!', 'success')
            
        except Exception as e:
            flash(f'Errore nel salvataggio configurazioni fatture: {str(e)}', 'danger')
    
    return render_template('admin/configurazioni/general_config.html', 
                         db_form=db_form, 
                         company_form=company_form, 
                         system_form=system_form)

@admin_bp.route('/configurazioni/create-tables', methods=['POST'])
@admin_required
def create_tables():
    """Create missing tables in the remote database"""
    try:
        # Create the tables if they don't exist
        db.create_all()
        
        flash('Tabelle create con successo!', 'success')
    except Exception as e:
        flash(f'Errore nella creazione delle tabelle: {str(e)}', 'danger')
    
    return redirect(url_for('admin.general_config'))

@admin_bp.route('/configurazioni/system-config', methods=['GET', 'POST'])
@admin_required
def system_config():
    """Redirect to general config for backward compatibility"""
    return redirect(url_for('admin.general_config'))

@admin_bp.route('/configurazioni/db-config', methods=['GET', 'POST'])
@admin_required
def db_config():
    """Redirect to general config for backward compatibility"""
    return redirect(url_for('admin.general_config'))

@admin_bp.route('/configurazioni/chat-operation', methods=['POST'])
@admin_required
def chat_operation():
    """Handle chat operations (clear, backup)"""
    import json
    import os
    from datetime import datetime
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'backup':
            # Create backup
            backup_result = create_chat_backup()
            if backup_result['success']:
                return jsonify({'success': True, 'message': f'Backup creato: {backup_result["filename"]}'})
            else:
                return jsonify({'success': False, 'error': backup_result['error']})
                
        elif operation == 'clear':
            # Create backup first, then clear
            backup_result = create_chat_backup()
            if not backup_result['success']:
                return jsonify({'success': False, 'error': f'Errore durante il backup: {backup_result["error"]}'})
            
            # Clear all messages
            ChatMessage.query.delete()
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'Chat svuotata e backup creato: {backup_result["filename"]}'})
        
        else:
            return jsonify({'success': False, 'error': 'Operazione non valida'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/chat-stats')
@admin_required
def chat_stats():
    """Get chat statistics"""
    from datetime import datetime, timedelta
    import os
    
    try:
        # Total messages
        total_messages = ChatMessage.query.count()
        
        # Today's messages
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        today_messages = ChatMessage.query.filter(
            ChatMessage.timestamp >= today,
            ChatMessage.timestamp < tomorrow
        ).count()
        
        # Last backup info
        backup_path = SystemConfig.get_config('chat_backup_path', 'Backup/Chat')
        backup_dir = os.path.join(backup_path)
        
        last_backup = 'Mai'
        backup_count = 0
        
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('chat_backup_') and f.endswith('.json')]
            backup_count = len(backup_files)
            
            if backup_files:
                # Get most recent backup
                backup_files.sort(reverse=True)
                last_backup_file = backup_files[0]
                # Extract date from filename (chat_backup_YYYYMMDD_HHMMSS.json)
                try:
                    date_part = last_backup_file.replace('chat_backup_', '').replace('.json', '')
                    backup_date = datetime.strptime(date_part, '%Y%m%d_%H%M%S')
                    last_backup = backup_date.strftime('%d/%m/%Y %H:%M')
                except:
                    last_backup = 'Errore data'
        
        return jsonify({
            'success': True,
            'total_messages': total_messages,
            'today_messages': today_messages,
            'last_backup': last_backup,
            'backup_count': backup_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/chat-config')
@admin_required 
def chat_config():
    """Get current chat configuration"""
    try:
        return jsonify({
            'success': True,
            'enable_auto_cleanup': SystemConfig.get_config('enable_chat_auto_cleanup', False),
            'cleanup_frequency': SystemConfig.get_config('chat_cleanup_frequency_days', 7),
            'enable_auto_backup': SystemConfig.get_config('enable_chat_auto_backup', True),
            'backup_retention': SystemConfig.get_config('chat_backup_retention_days', 30),
            'backup_path': SystemConfig.get_config('chat_backup_path', 'Backup/Chat')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ===== BACKUP ROUTES FOR CLIENTI, DDT, FATTURE =====

@admin_bp.route('/configurazioni/clienti-operation', methods=['POST'])
@admin_required
def clienti_operation():
    """Handle clienti operations (backup)"""
    import json
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'backup':
            # Create backup
            backup_result = create_clienti_backup()
            if backup_result['success']:
                return jsonify({'success': True, 'message': f'Backup clienti creato: {backup_result["filename"]}'})
            else:
                return jsonify({'success': False, 'error': backup_result['error']})
        else:
            return jsonify({'success': False, 'error': 'Operazione non valida'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/clienti-stats')
@admin_required
def clienti_stats():
    """Get clienti statistics"""
    import os
    
    try:
        # Total clients
        total_clients = Client.query.count()
        
        # Active clients (clients with orders)
        active_clients = db.session.query(Client.IdCliente).join(
            AlbaranCabecera, Client.IdCliente == AlbaranCabecera.IdCliente
        ).distinct().count()
        
        # Last backup info
        backup_path = SystemConfig.get_config('clienti_backup_path', 'Backup/Clienti')
        backup_dir = os.path.join(backup_path)
        
        last_backup = 'Mai'
        backup_count = 0
        
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('clienti_backup_') and f.endswith('.json')]
            backup_count = len(backup_files)
            
            if backup_files:
                # Get most recent backup
                backup_files.sort(reverse=True)
                last_backup_file = backup_files[0]
                # Extract date from filename (clienti_backup_YYYYMMDD_HHMMSS.json)
                try:
                    date_part = last_backup_file.replace('clienti_backup_', '').replace('.json', '')
                    backup_date = datetime.strptime(date_part, '%Y%m%d_%H%M%S')
                    last_backup = backup_date.strftime('%d/%m/%Y %H:%M')
                except:
                    last_backup = 'Errore data'
        
        return jsonify({
            'success': True,
            'total_clients': total_clients,
            'active_clients': active_clients,
            'last_backup': last_backup,
            'backup_count': backup_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/clienti-config')
@admin_required 
def clienti_config():
    """Get current clienti configuration"""
    try:
        return jsonify({
            'success': True,
            'enable_auto_backup': SystemConfig.get_config('enable_clienti_auto_backup', True),
            'backup_frequency': SystemConfig.get_config('clienti_backup_frequency_days', 7),
            'backup_retention': SystemConfig.get_config('clienti_backup_retention_days', 30),
            'backup_path': SystemConfig.get_config('clienti_backup_path', 'Backup/Clienti')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/ddt-operation', methods=['POST'])
@admin_required
def ddt_operation():
    """Handle DDT operations (backup)"""
    import json
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'backup':
            # Create backup
            backup_result = create_ddt_backup()
            if backup_result['success']:
                return jsonify({'success': True, 'message': f'Backup DDT creato: {backup_result["filename"]}'})
            else:
                return jsonify({'success': False, 'error': backup_result['error']})
        else:
            return jsonify({'success': False, 'error': 'Operazione non valida'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/ddt-stats')
@admin_required
def ddt_stats():
    """Get DDT statistics"""
    from datetime import datetime, timedelta
    import os
    
    try:
        # Total DDTs
        total_ddts = AlbaranCabecera.query.count()
        
        # Today's DDTs
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        today_ddts = AlbaranCabecera.query.filter(
            AlbaranCabecera.Fecha >= today,
            AlbaranCabecera.Fecha < tomorrow
        ).count()
        
        # Last backup info
        backup_path = SystemConfig.get_config('ddt_backup_path', 'Backup/DDT')
        backup_dir = os.path.join(backup_path)
        
        last_backup = 'Mai'
        backup_count = 0
        
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.startswith('ddt_backup_') and f.endswith('.json')]
            backup_count = len(backup_files)
            
            if backup_files:
                # Get most recent backup
                backup_files.sort(reverse=True)
                last_backup_file = backup_files[0]
                # Extract date from filename (ddt_backup_YYYYMMDD_HHMMSS.json)
                try:
                    date_part = last_backup_file.replace('ddt_backup_', '').replace('.json', '')
                    backup_date = datetime.strptime(date_part, '%Y%m%d_%H%M%S')
                    last_backup = backup_date.strftime('%d/%m/%Y %H:%M')
                except:
                    last_backup = 'Errore data'
        
        return jsonify({
            'success': True,
            'total_ddts': total_ddts,
            'today_ddts': today_ddts,
            'last_backup': last_backup,
            'backup_count': backup_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/ddt-config')
@admin_required 
def ddt_config():
    """Get current DDT configuration"""
    try:
        return jsonify({
            'success': True,
            'enable_auto_backup': SystemConfig.get_config('enable_ddt_auto_backup', True),
            'backup_frequency': SystemConfig.get_config('ddt_backup_frequency_days', 7),
            'backup_retention': SystemConfig.get_config('ddt_backup_retention_days', 30),
            'backup_path': SystemConfig.get_config('ddt_backup_path', 'Backup/DDT')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/fatture-operation', methods=['POST'])
@admin_required
def fatture_operation():
    """Handle fatture operations (backup)"""
    import json
    
    try:
        data = request.get_json()
        operation = data.get('operation')
        
        if operation == 'backup':
            # Create backup
            backup_result = create_fatture_backup()
            if backup_result['success']:
                return jsonify({'success': True, 'message': f'Backup fatture creato: {backup_result["filename"]}'})
            else:
                return jsonify({'success': False, 'error': backup_result['error']})
        else:
            return jsonify({'success': False, 'error': 'Operazione non valida'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/fatture-stats')
@admin_required
def fatture_stats():
    """Get fatture statistics"""
    import os
    
    try:
        # Get fatture directory
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        
        # Count XML files
        total_fatture = 0
        today_fatture = 0
        
        if os.path.exists(fatture_dir):
            xml_files = [f for f in os.listdir(fatture_dir) if f.endswith('.xml')]
            total_fatture = len(xml_files)
            
            # Count today's fatture (based on file creation)
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            
            for filename in xml_files:
                file_path = os.path.join(fatture_dir, filename)
                creation_time = datetime.fromtimestamp(os.path.getctime(file_path)).date()
                if creation_time == today:
                    today_fatture += 1
        
        # Last backup info
        backup_path = SystemConfig.get_config('fatture_backup_path', 'Backup/Fatture')
        backup_dir = os.path.join(backup_path)
        
        last_backup = 'Mai'
        backup_count = 0
        
        if os.path.exists(backup_dir):
            backup_folders = [f for f in os.listdir(backup_dir) if f.startswith('fatture_backup_') and os.path.isdir(os.path.join(backup_dir, f))]
            backup_count = len(backup_folders)
            
            if backup_folders:
                # Get most recent backup
                backup_folders.sort(reverse=True)
                last_backup_folder = backup_folders[0]
                # Extract date from folder name (fatture_backup_YYYYMMDD_HHMMSS)
                try:
                    date_part = last_backup_folder.replace('fatture_backup_', '')
                    backup_date = datetime.strptime(date_part, '%Y%m%d_%H%M%S')
                    last_backup = backup_date.strftime('%d/%m/%Y %H:%M')
                except:
                    last_backup = 'Errore data'
        
        return jsonify({
            'success': True,
            'total_fatture': total_fatture,
            'today_fatture': today_fatture,
            'last_backup': last_backup,
            'backup_count': backup_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/configurazioni/fatture-config')
@admin_required 
def fatture_config():
    """Get current fatture configuration"""
    try:
        return jsonify({
            'success': True,
            'enable_auto_backup': SystemConfig.get_config('enable_fatture_auto_backup', True),
            'backup_frequency': SystemConfig.get_config('fatture_backup_frequency_days', 7),
            'backup_retention': SystemConfig.get_config('fatture_backup_retention_days', 30),
            'backup_path': SystemConfig.get_config('fatture_backup_path', 'Backup/Fatture')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def create_chat_backup():
    """Create a backup of all chat messages"""
    import json
    import os
    from datetime import datetime
    
    try:
        # Get backup path from config
        backup_path = SystemConfig.get_config('chat_backup_path', 'Backup/Chat')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        # Get all messages
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
        
        # Convert to JSON format
        backup_data = {
            'backup_date': datetime.utcnow().isoformat(),
            'total_messages': len(messages),
            'messages': []
        }
        
        for msg in messages:
            backup_data['messages'].append({
                'id': msg.id,
                'user_id': msg.user_id,
                'username': msg.user.username,
                'message': msg.message,
                'timestamp': msg.timestamp.isoformat(),
                'is_read': msg.is_read,
                'room_id': msg.room_id
            })
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'chat_backup_{timestamp}.json'
        filepath = os.path.join(backup_path, filename)
        
        # Save backup
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Clean old backups based on retention policy
        cleanup_old_backups(backup_path)
        
        return {'success': True, 'filename': filename, 'path': filepath}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def cleanup_old_backups(backup_path):
    """Clean up old backup files based on retention policy"""
    try:
        retention_days = SystemConfig.get_config('chat_backup_retention_days', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        if os.path.exists(backup_path):
            for filename in os.listdir(backup_path):
                if filename.startswith('chat_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(backup_path, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        
    except Exception as e:
        # Log error but don't fail the backup operation
        print(f"Error cleaning old backups: {e}")

# ===== BACKUP FUNCTIONS FOR CLIENTI, DDT, FATTURE =====

def create_clienti_backup():
    """Create a backup of all clients"""
    import json
    import os
    from datetime import datetime
    
    try:
        # Get backup path from config
        backup_path = SystemConfig.get_config('clienti_backup_path', 'Backup/Clienti')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        # Get all clients
        clients = Client.query.order_by(Client.IdCliente.asc()).all()
        
        # Convert to JSON format
        backup_data = {
            'backup_date': datetime.utcnow().isoformat(),
            'total_clients': len(clients),
            'clients': []
        }
        
        for client in clients:
            backup_data['clients'].append({
                'IdCliente': client.IdCliente,
                'IdEmpresa': client.IdEmpresa,
                'Nombre': client.Nombre,
                'Direccion': client.Direccion,
                'CodPostal': client.CodPostal,
                'Poblacion': client.Poblacion,
                'Provincia': client.Provincia,
                'Pais': client.Pais,
                'DNI': client.DNI,
                'Telefono1': client.Telefono1,
                'Telefono2': client.Telefono2,
                'Telefono3': client.Telefono3,
                'Email': client.Email,
                'TipoEmailTicket': client.TipoEmailTicket,
                'TipoEmailAlbaran': client.TipoEmailAlbaran,
                'TipoEmailFactura': client.TipoEmailFactura,
                'IdTarifa': client.IdTarifa,
                'Ofertas': client.Ofertas,
                'IdFormaPago': client.IdFormaPago,
                'IdEstado': client.IdEstado,
                'Observaciones': client.Observaciones,
                'CodInterno': client.CodInterno,
                'Descuento': float(client.Descuento) if client.Descuento else None,
                'PuntosFidelidad': client.PuntosFidelidad,
                'CuentaPendiente': float(client.CuentaPendiente) if client.CuentaPendiente else None,
                'EANScanner': client.EANScanner,
                'FormatoAlbaran': client.FormatoAlbaran,
                'UsarRecargoEquivalencia': client.UsarRecargoEquivalencia,
                'DtoProntoPago': float(client.DtoProntoPago) if client.DtoProntoPago else None,
                'NombreBanco': client.NombreBanco,
                'CodigoCuenta': client.CodigoCuenta,
                'NumeroVencimientos': client.NumeroVencimientos,
                'DiasEntreVencimientos': client.DiasEntreVencimientos,
                'TotalPorArticulo': client.TotalPorArticulo,
                'AplicarTarifaEtiqueta': client.AplicarTarifaEtiqueta,
                'FormatoFactura': client.FormatoFactura,
                'ModoFacturacion': client.ModoFacturacion,
                'Modificado': client.Modificado,
                'Operacion': client.Operacion,
                'Usuario': client.Usuario,
                'TimeStamp': client.TimeStamp.isoformat() if client.TimeStamp else None
            })
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'clienti_backup_{timestamp}.json'
        filepath = os.path.join(backup_path, filename)
        
        # Save backup
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Clean old backups based on retention policy
        cleanup_old_clienti_backups(backup_path)
        
        return {'success': True, 'filename': filename, 'path': filepath}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_ddt_backup():
    """Create a backup of all DDT (AlbaranCabecera and AlbaranLinea)"""
    import json
    import os
    from datetime import datetime
    
    try:
        # Get backup path from config
        backup_path = SystemConfig.get_config('ddt_backup_path', 'Backup/DDT')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        # Get all DDT with their lines
        ddts = AlbaranCabecera.query.order_by(AlbaranCabecera.IdAlbaran.asc()).all()
        
        # Convert to JSON format
        backup_data = {
            'backup_date': datetime.utcnow().isoformat(),
            'total_ddts': len(ddts),
            'ddts': []
        }
        
        for ddt in ddts:
            # Get DDT lines
            lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
            
            ddt_data = {
                # Header data
                'header': {
                    'IdAlbaran': ddt.IdAlbaran,
                    'NumAlbaran': ddt.NumAlbaran,
                    'IdEmpresa': ddt.IdEmpresa,
                    'NombreEmpresa': ddt.NombreEmpresa,
                    'CIF_VAT_Empresa': ddt.CIF_VAT_Empresa,
                    'DireccionEmpresa': ddt.DireccionEmpresa,
                    'PoblacionEmpresa': ddt.PoblacionEmpresa,
                    'CPEmpresa': ddt.CPEmpresa,
                    'TelefonoEmpresa': ddt.TelefonoEmpresa,
                    'ProvinciaEmpresa': ddt.ProvinciaEmpresa,
                    'IdTienda': ddt.IdTienda,
                    'NombreTienda': ddt.NombreTienda,
                    'IdBalanzaMaestra': ddt.IdBalanzaMaestra,
                    'NombreBalanzaMaestra': ddt.NombreBalanzaMaestra,
                    'IdBalanzaEsclava': ddt.IdBalanzaEsclava,
                    'NombreBalanzaEsclava': ddt.NombreBalanzaEsclava,
                    'Tipo': ddt.Tipo,
                    'IdVendedor': ddt.IdVendedor,
                    'NombreVendedor': ddt.NombreVendedor,
                    'IdCliente': ddt.IdCliente,
                    'NombreCliente': ddt.NombreCliente,
                    'DNICliente': ddt.DNICliente,
                    'EmailCliente': ddt.EmailCliente,
                    'DireccionCliente': ddt.DireccionCliente,
                    'PoblacionCliente': ddt.PoblacionCliente,
                    'ProvinciaCliente': ddt.ProvinciaCliente,
                    'PaisCliente': ddt.PaisCliente,
                    'CPCliente': ddt.CPCliente,
                    'TelefonoCliente': ddt.TelefonoCliente,
                    'ObservacionesCliente': ddt.ObservacionesCliente,
                    'EANCliente': ddt.EANCliente,
                    'ReferenciaDocumento': ddt.ReferenciaDocumento,
                    'ObservacionesDocumento': ddt.ObservacionesDocumento,
                    'TipoVenta': ddt.TipoVenta,
                    'ImporteLineas': float(ddt.ImporteLineas) if ddt.ImporteLineas else None,
                    'PorcDescuento': float(ddt.PorcDescuento) if ddt.PorcDescuento else None,
                    'ImporteDescuento': float(ddt.ImporteDescuento) if ddt.ImporteDescuento else None,
                    'ImporteRE': float(ddt.ImporteRE) if ddt.ImporteRE else None,
                    'ImporteTotalSinRE': float(ddt.ImporteTotalSinRE) if ddt.ImporteTotalSinRE else None,
                    'ImporteTotalSinIVAConDtoLConDtoTotalConRE': float(ddt.ImporteTotalSinIVAConDtoLConDtoTotalConRE) if ddt.ImporteTotalSinIVAConDtoLConDtoTotalConRE else None,
                    'ImporteTotal': float(ddt.ImporteTotal) if ddt.ImporteTotal else None,
                    'Fecha': ddt.Fecha.isoformat() if ddt.Fecha else None,
                    'FechaModificacion': ddt.FechaModificacion.isoformat() if ddt.FechaModificacion else None,
                    'Enviado': ddt.Enviado,
                    'NumLineas': ddt.NumLineas,
                    'CodigoBarras': ddt.CodigoBarras,
                    'Modificado': ddt.Modificado,
                    'Operacion': ddt.Operacion,
                    'Usuario': ddt.Usuario,
                    'TimeStamp': ddt.TimeStamp.isoformat() if ddt.TimeStamp else None,
                    'EstadoTicket': ddt.EstadoTicket
                },
                # Lines data
                'lines': []
            }
            
            for line in lines:
                ddt_data['lines'].append({
                    'IdLineaAlbaran': line.IdLineaAlbaran,
                    'IdEmpresa': line.IdEmpresa,
                    'IdTienda': line.IdTienda,
                    'IdBalanzaMaestra': line.IdBalanzaMaestra,
                    'IdBalanzaEsclava': line.IdBalanzaEsclava,
                    'IdAlbaran': line.IdAlbaran,
                    'TipoVenta': line.TipoVenta,
                    'EstadoLinea': line.EstadoLinea,
                    'IdTicket': line.IdTicket,
                    'IdArticulo': line.IdArticulo,
                    'Descripcion': line.Descripcion,
                    'Descripcion1': line.Descripcion1,
                    'Comportamiento': line.Comportamiento,
                    'ComportamientoDevolucion': line.ComportamientoDevolucion,
                    'EntradaManual': line.EntradaManual,
                    'Tara': float(line.Tara) if line.Tara else None,
                    'TaraPreprogramada': line.TaraPreprogramada,
                    'Peso': float(line.Peso) if line.Peso else None,
                    'PesoBruto': float(line.PesoBruto) if line.PesoBruto else None,
                    'PesoEmbalaje': float(line.PesoEmbalaje) if line.PesoEmbalaje else None,
                    'PesoRegalado': float(line.PesoRegalado) if line.PesoRegalado else None,
                    'PesoNetoNoEscurrido': float(line.PesoNetoNoEscurrido) if line.PesoNetoNoEscurrido else None,
                    'ValorTaraPorcentual': float(line.ValorTaraPorcentual) if line.ValorTaraPorcentual else None,
                    'TaraNoEscurrida': float(line.TaraNoEscurrida) if line.TaraNoEscurrida else None,
                    'DetalleTara': line.DetalleTara,
                    'Cantidad2': float(line.Cantidad2) if line.Cantidad2 else None,
                    'Cantidad2Regalada': float(line.Cantidad2Regalada) if line.Cantidad2Regalada else None,
                    'Medida2': line.Medida2,
                    'PrecioPorCienGramos': line.PrecioPorCienGramos,
                    'Precio': float(line.Precio) if line.Precio else None,
                    'PrecioSinOferta': float(line.PrecioSinOferta) if line.PrecioSinOferta else None,
                    'PrecioSinIVA': float(line.PrecioSinIVA) if line.PrecioSinIVA else None,
                    'PrecioConIVASinDtoL': float(line.PrecioConIVASinDtoL) if line.PrecioConIVASinDtoL else None,
                    'IdIVA': line.IdIVA,
                    'PorcentajeIVA': float(line.PorcentajeIVA) if line.PorcentajeIVA else None,
                    'RecargoEquivalencia': float(line.RecargoEquivalencia) if line.RecargoEquivalencia else None,
                    'Descuento': float(line.Descuento) if line.Descuento else None,
                    'TipoDescuento': line.TipoDescuento,
                    'Importe': float(line.Importe) if line.Importe else None,
                    'FechaCaducidad': line.FechaCaducidad.isoformat() if line.FechaCaducidad else None,
                    'FechaEnvasado': line.FechaEnvasado.isoformat() if line.FechaEnvasado else None,
                    'FechaFabricacion': line.FechaFabricacion.isoformat() if line.FechaFabricacion else None,
                    'LogoEtiqueta': line.LogoEtiqueta,
                    'CodInterno': line.CodInterno,
                    'EANScannerArticulo': line.EANScannerArticulo,
                    'TextoLote': line.TextoLote,
                    'IdClase': line.IdClase,
                    'NombreClase': line.NombreClase,
                    'IdFamilia': line.IdFamilia,
                    'NombreFamilia': line.NombreFamilia,
                    'IdSeccion': line.IdSeccion,
                    'NombreSeccion': line.NombreSeccion,
                    'IdSubFamilia': line.IdSubFamilia,
                    'NombreSubFamilia': line.NombreSubFamilia,
                    'IdDepartamento': line.IdDepartamento,
                    'NombreDepartamento': line.NombreDepartamento,
                    'Texto1': line.Texto1,
                    'TextoLibre': line.TextoLibre,
                    'Facturada': line.Facturada,
                    'CantidadFacturada': float(line.CantidadFacturada) if line.CantidadFacturada else None,
                    'Modificado': line.Modificado,
                    'Operacion': line.Operacion,
                    'Usuario': line.Usuario,
                    'TimeStamp': line.TimeStamp.isoformat() if line.TimeStamp else None
                })
            
            backup_data['ddts'].append(ddt_data)
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'ddt_backup_{timestamp}.json'
        filepath = os.path.join(backup_path, filename)
        
        # Save backup
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Clean old backups based on retention policy
        cleanup_old_ddt_backups(backup_path)
        
        return {'success': True, 'filename': filename, 'path': filepath}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_fatture_backup():
    """Create a backup of all fatture (XML files)"""
    import json
    import os
    import shutil
    from datetime import datetime
    
    try:
        # Get backup path from config
        backup_path = SystemConfig.get_config('fatture_backup_path', 'Backup/Fatture')
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_path, exist_ok=True)
        
        # Get fatture directory
        fatture_dir = os.path.join(current_app.root_path, 'Fatture')
        
        # Initialize backup data
        backup_data = {
            'backup_date': datetime.utcnow().isoformat(),
            'total_fatture': 0,
            'fatture_files': [],
            'fatture_data': []
        }
        
        # Create timestamp for this backup
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_folder = os.path.join(backup_path, f'fatture_backup_{timestamp}')
        os.makedirs(backup_folder, exist_ok=True)
        
        # Check if fatture directory exists
        if os.path.exists(fatture_dir):
            fatture_files = [f for f in os.listdir(fatture_dir) if f.endswith('.xml')]
            backup_data['total_fatture'] = len(fatture_files)
            
            for filename in fatture_files:
                src_path = os.path.join(fatture_dir, filename)
                dst_path = os.path.join(backup_folder, filename)
                
                # Copy the XML file
                shutil.copy2(src_path, dst_path)
                
                # Get file stats
                file_stats = os.stat(src_path)
                creation_time = datetime.fromtimestamp(file_stats.st_ctime)
                file_size = file_stats.st_size
                
                # Try to extract basic info from XML
                fattura_info = {
                    'filename': filename,
                    'file_size': file_size,
                    'creation_time': creation_time.isoformat(),
                    'invoice_number': None,
                    'client_name': None,
                    'total_amount': None,
                    'ddt_reference': None,
                    'invoice_date': None
                }
                
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(src_path)
                    root = tree.getroot()
                    
                    # Extract basic information
                    for elem in root.iter():
                        if 'Numero' in elem.tag and elem.text and not fattura_info['invoice_number']:
                            fattura_info['invoice_number'] = elem.text
                        elif 'Denominazione' in elem.tag and elem.text and not fattura_info['client_name']:
                            fattura_info['client_name'] = elem.text
                        elif 'ImportoPagamento' in elem.tag and elem.text:
                            fattura_info['total_amount'] = elem.text
                        elif 'NumeroDDT' in elem.tag and elem.text:
                            fattura_info['ddt_reference'] = elem.text
                        elif 'Data' in elem.tag and elem.text and not fattura_info['invoice_date']:
                            fattura_info['invoice_date'] = elem.text
                            
                except Exception as xml_error:
                    fattura_info['xml_parse_error'] = str(xml_error)
                
                backup_data['fatture_files'].append(filename)
                backup_data['fatture_data'].append(fattura_info)
        
        # Create metadata file
        metadata_file = os.path.join(backup_folder, 'backup_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        # Clean old backups based on retention policy
        cleanup_old_fatture_backups(backup_path)
        
        return {'success': True, 'filename': f'fatture_backup_{timestamp}', 'path': backup_folder}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def cleanup_old_clienti_backups(backup_path):
    """Clean up old client backup files based on retention policy"""
    try:
        retention_days = SystemConfig.get_config('clienti_backup_retention_days', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        if os.path.exists(backup_path):
            for filename in os.listdir(backup_path):
                if filename.startswith('clienti_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(backup_path, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        
    except Exception as e:
        print(f"Error cleaning old client backups: {e}")

def cleanup_old_ddt_backups(backup_path):
    """Clean up old DDT backup files based on retention policy"""
    try:
        retention_days = SystemConfig.get_config('ddt_backup_retention_days', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        if os.path.exists(backup_path):
            for filename in os.listdir(backup_path):
                if filename.startswith('ddt_backup_') and filename.endswith('.json'):
                    filepath = os.path.join(backup_path, filename)
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_mtime < cutoff_date:
                        os.remove(filepath)
                        
    except Exception as e:
        print(f"Error cleaning old DDT backups: {e}")

def cleanup_old_fatture_backups(backup_path):
    """Clean up old fatture backup folders based on retention policy"""
    try:
        retention_days = SystemConfig.get_config('fatture_backup_retention_days', 30)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        if os.path.exists(backup_path):
            for dirname in os.listdir(backup_path):
                if dirname.startswith('fatture_backup_'):
                    dirpath = os.path.join(backup_path, dirname)
                    if os.path.isdir(dirpath):
                        dir_mtime = datetime.fromtimestamp(os.path.getmtime(dirpath))
                        
                        if dir_mtime < cutoff_date:
                            import shutil
                            shutil.rmtree(dirpath)
                            
    except Exception as e:
        print(f"Error cleaning old fatture backups: {e}") 