from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse
from models import db, User
from forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('warehouse.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            if user.screen_task:
                next_page = url_for('tasks.task_screen')
            else:
                next_page = url_for('warehouse.index')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Sign In', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # Only allow registration if there are no users in the database (first run)
    # or if the current user is an admin
    if current_user.is_authenticated:
        if not current_user.is_admin:
            flash('Only administrators can register new users', 'warning')
            return redirect(url_for('warehouse.index'))
    elif User.query.count() > 0:
        flash('Registration is restricted. Please contact an administrator.', 'warning')
        return redirect(url_for('auth.login'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data if current_user.is_authenticated and current_user.is_admin else False,
            screen_task=form.screen_task.data if current_user.is_authenticated and current_user.is_admin else False
        )
        user.set_password(form.password.data)
        
        # First user is automatically an admin
        if User.query.count() == 0:
            user.is_admin = True
            
        db.session.add(user)
        db.session.commit()
        
        flash('User registered successfully!', 'success')
        if current_user.is_authenticated:
            return redirect(url_for('admin.manage_users'))
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', title='Register', form=form) 