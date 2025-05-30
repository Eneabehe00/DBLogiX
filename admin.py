from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, User, ScanLog, Product, TicketHeader, Company, SystemConfig
from forms import RegistrationForm, DbConfigForm, CompanyConfigForm, ResetPasswordForm, SystemConfigForm
from sqlalchemy import func, desc
from config import REMOTE_DB_CONFIG
import pymysql
from datetime import datetime, timedelta
import json
import os

admin_bp = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(view_func):
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('warehouse.index'))
        return view_func(*args, **kwargs)
    wrapped_view.__name__ = view_func.__name__
    return wrapped_view

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
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
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
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/configurazioni/user_form.html', form=form, title='Edit User', edit_mode=True)

@admin_bp.route('/configurazioni/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.manage_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully!', 'success')
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
        flash('Password reset successfully!', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/configurazioni/reset_password.html', user=user, form=form)

@admin_bp.route('/configurazioni/general-config', methods=['GET', 'POST'])
@admin_required
def general_config():
    """Unified configuration page with tabs for DB, Company, and System settings"""
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
        
        # System form
        expiry_warning_days = SystemConfig.get_config('expiry_warning_days', 7)
        articles_per_package = SystemConfig.get_config('articles_per_package', 5)
        system_form.expiry_warning_days.data = expiry_warning_days
        system_form.articles_per_package.data = articles_per_package
    
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
                flash('Connessione al database riuscita!', 'success')
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
                import re
                pattern = r"REMOTE_DB_CONFIG = \{[^}]+\}"
                updated_content = re.sub(pattern, new_config_str, config_content)
                
                # Update the SQLALCHEMY_DATABASE_URI
                sqlalchemy_uri = f"SQLALCHEMY_DATABASE_URI = f\"mysql+pymysql://{new_config['user']}:{new_config['password']}@{new_config['host']}:{new_config['port']}/{new_config['database']}\""
                
                pattern = r"SQLALCHEMY_DATABASE_URI = f\"mysql\+pymysql://[^\"]+\""
                updated_content = re.sub(pattern, sqlalchemy_uri, updated_content)
                
                # Write the updated content back to the file
                with open('config.py', 'w') as f:
                    f.write(updated_content)
                
                flash('Configurazione database salvata con successo! Riavvia l\'applicazione per applicare le modifiche.', 'success')
            except Exception as e:
                flash(f'Errore nel salvataggio della configurazione: {str(e)}', 'danger')
    
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
            flash('Configurazione azienda salvata con successo!', 'success')
        except Exception as e:
            flash(f'Errore nel salvataggio della configurazione azienda: {str(e)}', 'danger')
    
    # Handle System config form submit
    if 'submit_system' in request.form and system_form.validate():
        try:
            # Save expiry warning days configuration
            SystemConfig.set_config(
                'expiry_warning_days', 
                system_form.expiry_warning_days.data,
                'Numero di giorni prima della scadenza per contrassegnare i ticket come "In Scadenza"',
                'integer'
            )
            
            # Save articles per package configuration
            SystemConfig.set_config(
                'articles_per_package',
                system_form.articles_per_package.data,
                'Numero di articoli necessari per determinare un collo nei DDT (escluso l\'articolo "trasporto")',
                'integer'
            )
            
            flash('Configurazioni sistema salvate con successo!', 'success')
        except Exception as e:
            flash(f'Errore nel salvataggio delle configurazioni sistema: {str(e)}', 'danger')
    
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
        
        flash('Tables created successfully!', 'success')
    except Exception as e:
        flash(f'Failed to create tables: {str(e)}', 'danger')
    
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