from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Section, Article
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from datetime import datetime
import base64
from werkzeug.utils import secure_filename
import os
from utils import admin_required, is_admin

sections_bp = Blueprint('sections', __name__, template_folder='templates')

@sections_bp.route('/')
@login_required
def index():
    """Display list of all sections"""
    sections = Section.query.all()
    return render_template('sections/index.html', sections=sections)

@sections_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Create a new section"""
    if request.method == 'POST':
        try:
            # Get next available IdSeccion
            max_id = db.session.query(db.func.max(Section.IdSeccion)).scalar() or 0
            new_id = max_id + 1
            
            # Handle form data
            nombre_seccion = request.form.get('NombreSeccion', '')[:50]  # varchar(50)
            id_logo = request.form.get('IdLogo') or None
            fto_tarjeta_articulo_a = request.form.get('FtoTarjetaArticuloA') or None
            fto_tarjeta_articulo_b = request.form.get('FtoTarjetaArticuloB') or None
            id_seccion_cliente = request.form.get('IdSeccionCliente') or None
            
            # Handle image upload
            imagen = None
            if 'Imagen' in request.files and request.files['Imagen'].filename:
                imagen_file = request.files['Imagen']
                imagen = imagen_file.read()
            
            # Create new section
            section = Section(
                IdSeccion=new_id,
                NombreSeccion=nombre_seccion,
                IdLogo=id_logo,
                Imagen=imagen,
                FtoTarjetaArticuloA=fto_tarjeta_articulo_a,
                FtoTarjetaArticuloB=fto_tarjeta_articulo_b,
                IdEmpresa=1,  # Default value
                IdSeccionCliente=id_seccion_cliente,
                Modificado=1,
                Operacion='A',
                Usuario=current_user.username,
                TimeStamp=datetime.utcnow()
            )
            
            db.session.add(section)
            db.session.commit()
            flash('Sezione creata con successo!', 'success')
            return redirect(url_for('sections.index'))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nella creazione della sezione: {str(e)}', 'danger')
    
    return render_template('sections/new.html')

@sections_bp.route('/<int:id>', methods=['GET'])
@login_required
def view(id):
    """View a single section and its related articles"""
    section = Section.query.filter_by(IdSeccion=id, IdEmpresa=1).first_or_404()
    
    # Get articles related to this section
    articles = Article.query.filter_by(IdSeccion=id).all()
    
    # Convert image to base64 for display if exists
    image_b64 = None
    if section.Imagen:
        image_b64 = base64.b64encode(section.Imagen).decode('utf-8')
    
    return render_template('sections/view.html', section=section, articles=articles, image_b64=image_b64)

@sections_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """Edit an existing section"""
    section = Section.query.filter_by(IdSeccion=id, IdEmpresa=1).first_or_404()
    
    if request.method == 'POST':
        try:
            section.NombreSeccion = request.form.get('NombreSeccion', '')[:50]
            section.IdLogo = request.form.get('IdLogo') or None
            section.FtoTarjetaArticuloA = request.form.get('FtoTarjetaArticuloA') or None
            section.FtoTarjetaArticuloB = request.form.get('FtoTarjetaArticuloB') or None
            section.IdSeccionCliente = request.form.get('IdSeccionCliente') or None
            
            # Update image only if a new one is provided
            if 'Imagen' in request.files and request.files['Imagen'].filename:
                section.Imagen = request.files['Imagen'].read()
            
            # If checkbox to remove image is checked, clear the image
            if request.form.get('RemoveImagen') == 'on':
                section.Imagen = None
            
            section.Modificado = 1
            section.Operacion = 'M'
            section.Usuario = current_user.username
            section.TimeStamp = datetime.utcnow()
            
            db.session.commit()
            flash('Sezione aggiornata con successo!', 'success')
            return redirect(url_for('sections.view', id=section.IdSeccion))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Errore nell\'aggiornamento della sezione: {str(e)}', 'danger')
    
    # Convert image to base64 for display if exists
    image_b64 = None
    if section.Imagen:
        image_b64 = base64.b64encode(section.Imagen).decode('utf-8')
    
    return render_template('sections/edit.html', section=section, image_b64=image_b64)

@sections_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(id):
    """Delete a section"""
    section = Section.query.filter_by(IdSeccion=id, IdEmpresa=1).first_or_404()
    
    try:
        # Check if there are any articles using this section
        articles_count = Article.query.filter_by(IdSeccion=id).count()
        
        if articles_count > 0:
            flash(f'Impossibile eliminare la sezione: ci sono {articles_count} articoli associati a questa sezione.', 'danger')
            return redirect(url_for('sections.view', id=id))
        
        db.session.delete(section)
        db.session.commit()
        flash('Sezione eliminata con successo!', 'success')
        return redirect(url_for('sections.index'))
        
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Errore nell\'eliminazione della sezione: {str(e)}', 'danger')
        return redirect(url_for('sections.view', id=id)) 