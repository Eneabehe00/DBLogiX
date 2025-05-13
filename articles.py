from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from models import db, Article
from forms import ArticleSearchForm, ArticleForm, ArticleDeleteForm
import csv
import os
from datetime import datetime
from decimal import Decimal

articles_bp = Blueprint('articles', __name__)

def parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except:
        return None

@articles_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search_form = ArticleSearchForm()
    
    # Get search query if exists
    query = request.args.get('query', '')
    
    # Query articles
    if query:
        articles_query = Article.query.filter(
            or_(
                Article.Descripcion.ilike(f'%{query}%'),
                Article.IdArticulo.ilike(f'%{query}%'),
                Article.EANScanner.ilike(f'%{query}%')
            )
        )
    else:
        articles_query = Article.query
    
    # Order and paginate
    articles = articles_query.order_by(Article.IdArticulo).paginate(page=page, per_page=20)
    
    return render_template('articles/index.html', 
                          articles=articles, 
                          search_form=search_form,
                          query=query)

@articles_bp.route('/search', methods=['POST'])
@login_required
def search():
    form = ArticleSearchForm()
    if form.validate_on_submit():
        return redirect(url_for('articles.index', query=form.query.data))
    return redirect(url_for('articles.index'))

@articles_bp.route('/view/<int:id>')
@login_required
def view(id):
    article = Article.query.get_or_404(id)
    return render_template('articles/view.html', article=article)

@articles_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = ArticleForm()
    
    if form.validate_on_submit():
        # Find the next available ID
        max_id = db.session.query(db.func.max(Article.IdArticulo)).scalar() or 0
        new_id = max_id + 1
        
        article = Article(
            IdArticulo=new_id,
            Descripcion=form.descripcion.data,
            Descripcion1=form.descripcion1.data,
            IdTipo=form.id_tipo.data,
            IdFamilia=form.id_familia.data,
            IdSubFamilia=form.id_subfamilia.data,
            IdDepartamento=form.id_departamento.data,
            IdSeccion=form.id_seccion.data,
            Favorito=form.favorito.data,
            PrecioSinIVA=form.precio_sin_iva.data,
            IdIVA=form.id_iva.data,
            PrecioConIVA=form.precio_con_iva.data,
            EANScanner=form.ean_scanner.data,
            Texto1=form.texto1.data,
            TextoLibre=form.texto_libre.data,
            StockActual=form.stock_actual.data,
            PesoMinimo=form.peso_minimo.data,
            PesoMaximo=form.peso_maximo.data,
            PesoObjetivo=form.peso_objetivo.data,
            FechaCaducidadActivada=form.fecha_caducidad_activada.data,
            DiasCaducidad=form.dias_caducidad.data,
            EnVenta=form.en_venta.data,
            IncluirGestionStock=form.incluir_gestion_stock.data,
            IdEmpresa=1,  # Default company ID
            Usuario=current_user.username,
            TimeStamp=datetime.utcnow(),
            Marca=1  # Default value
        )
        
        db.session.add(article)
        db.session.commit()
        
        flash('Article created successfully', 'success')
        return redirect(url_for('articles.view', id=article.IdArticulo))
    
    return render_template('articles/create.html', form=form)

@articles_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    article = Article.query.get_or_404(id)
    form = ArticleForm()
    
    if request.method == 'GET':
        # Populate form with existing data
        form.descripcion.data = article.Descripcion
        form.descripcion1.data = article.Descripcion1
        form.id_tipo.data = article.IdTipo
        form.id_familia.data = article.IdFamilia
        form.id_subfamilia.data = article.IdSubFamilia
        form.id_departamento.data = article.IdDepartamento
        form.id_seccion.data = article.IdSeccion
        form.favorito.data = article.Favorito
        form.precio_sin_iva.data = article.PrecioSinIVA
        form.id_iva.data = article.IdIVA
        form.precio_con_iva.data = article.PrecioConIVA
        form.ean_scanner.data = article.EANScanner
        form.texto1.data = article.Texto1
        form.texto_libre.data = article.TextoLibre
        form.stock_actual.data = article.StockActual
        form.peso_minimo.data = article.PesoMinimo
        form.peso_maximo.data = article.PesoMaximo
        form.peso_objetivo.data = article.PesoObjetivo
        form.fecha_caducidad_activada.data = article.FechaCaducidadActivada
        form.dias_caducidad.data = article.DiasCaducidad
        form.en_venta.data = article.EnVenta
        form.incluir_gestion_stock.data = article.IncluirGestionStock
    
    if form.validate_on_submit():
        # Update article with form data
        article.Descripcion = form.descripcion.data
        article.Descripcion1 = form.descripcion1.data
        article.IdTipo = form.id_tipo.data
        article.IdFamilia = form.id_familia.data
        article.IdSubFamilia = form.id_subfamilia.data
        article.IdDepartamento = form.id_departamento.data
        article.IdSeccion = form.id_seccion.data
        article.Favorito = form.favorito.data
        article.PrecioSinIVA = form.precio_sin_iva.data
        article.IdIVA = form.id_iva.data
        article.PrecioConIVA = form.precio_con_iva.data
        article.EANScanner = form.ean_scanner.data
        article.Texto1 = form.texto1.data
        article.TextoLibre = form.texto_libre.data
        article.StockActual = form.stock_actual.data
        article.PesoMinimo = form.peso_minimo.data
        article.PesoMaximo = form.peso_maximo.data
        article.PesoObjetivo = form.peso_objetivo.data
        article.FechaCaducidadActivada = form.fecha_caducidad_activada.data
        article.DiasCaducidad = form.dias_caducidad.data
        article.EnVenta = form.en_venta.data
        article.IncluirGestionStock = form.incluir_gestion_stock.data
        article.Usuario = current_user.username
        article.TimeStamp = datetime.utcnow()
        article.Modificado = True
        
        db.session.commit()
        
        flash('Article updated successfully', 'success')
        return redirect(url_for('articles.view', id=article.IdArticulo))
    
    return render_template('articles/edit.html', form=form, article=article)

@articles_bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete(id):
    article = Article.query.get_or_404(id)
    form = ArticleDeleteForm()
    
    if form.validate_on_submit() and form.confirm.data:
        db.session.delete(article)
        db.session.commit()
        flash('Article deleted successfully', 'success')
        return redirect(url_for('articles.index'))
    
    return render_template('articles/delete.html', form=form, article=article)

@articles_bp.route('/import-from-csv', methods=['GET', 'POST'])
@login_required
def import_from_csv():
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['csv_file']
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                csv_data = file.read().decode('utf-8')
                csv_reader = csv.DictReader(csv_data.splitlines())
                
                for row in csv_reader:
                    # Check if article already exists
                    article = Article.query.filter_by(IdArticulo=int(row['IdArticulo'])).first()
                    
                    if article:
                        # Update existing article
                        article.Descripcion = row['Descripcion']
                        article.Descripcion1 = row['Descripcion1']
                        article.IdTipo = int(row['IdTipo']) if row['IdTipo'] else 1
                        article.Favorito = bool(int(row['Favorito'])) if row['Favorito'] else True
                        article.Texto1 = row['Texto1']
                        article.TextoLibre = row['TextoLibre']
                        article.Usuario = current_user.username
                        article.TimeStamp = datetime.utcnow()
                        article.Modificado = True
                    else:
                        # Create new article
                        article = Article(
                            IdArticulo=int(row['IdArticulo']),
                            Descripcion=row['Descripcion'],
                            Descripcion1=row['Descripcion1'],
                            IdTipo=int(row['IdTipo']) if row['IdTipo'] else 1,
                            Favorito=bool(int(row['Favorito'])) if row['Favorito'] else True,
                            Texto1=row['Texto1'],
                            TextoLibre=row['TextoLibre'],
                            IdEmpresa=1,
                            Usuario=current_user.username,
                            TimeStamp=datetime.utcnow(),
                            Marca=1
                        )
                        db.session.add(article)
                
                db.session.commit()
                flash('Articles imported successfully', 'success')
            except Exception as e:
                flash(f'Error importing CSV: {str(e)}', 'danger')
                
            return redirect(url_for('articles.index'))
    
    return render_template('articles/import.html')

@articles_bp.route('/import-sample-data', methods=['GET'])
@login_required
def import_sample_data():
    """Import sample articles from the provided CSV file"""
    try:
        # Path to the sample CSV file
        csv_path = os.path.join('static', 'articoli.csv')
        
        # Read the CSV file
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            count_created = 0
            count_updated = 0
            
            for row in csv_reader:
                # Check if article already exists
                article = Article.query.filter_by(IdArticulo=int(row['IdArticulo'])).first()
                
                if article:
                    # Update existing article
                    article.Descripcion = row['Descripcion']
                    article.Descripcion1 = row['Descripcion1']
                    article.IdTipo = int(row['IdTipo']) if row['IdTipo'] else 1
                    article.LogoPantalla = row['LogoPantalla']
                    article.AvisoActivo = bool(int(row['AvisoActivo'])) if row['AvisoActivo'] else False
                    article.Aviso = row['Aviso']
                    article.IdFamilia = int(row['IdFamilia']) if row['IdFamilia'] else None
                    article.IdSubFamilia = int(row['IdSubFamilia']) if row['IdSubFamilia'] else None
                    article.IdDepartamento = int(row['IdDepartamento']) if row['IdDepartamento'] else None
                    article.IdSeccion = int(row['IdSeccion']) if row['IdSeccion'] else None
                    article.Favorito = bool(int(row['Favorito'])) if row['Favorito'] else True
                    article.Texto1 = row['Texto1']
                    article.TextoLibre = row['TextoLibre']
                    article.EANScanner = row['EANScanner']
                    article.Usuario = current_user.username
                    article.TimeStamp = datetime.utcnow()
                    article.Modificado = True
                    count_updated += 1
                else:
                    # Create new article
                    article = Article(
                        IdArticulo=int(row['IdArticulo']),
                        Descripcion=row['Descripcion'],
                        Descripcion1=row['Descripcion1'],
                        IdTipo=int(row['IdTipo']) if row['IdTipo'] else 1,
                        LogoPantalla=row['LogoPantalla'],
                        AvisoActivo=bool(int(row['AvisoActivo'])) if row['AvisoActivo'] else False,
                        Aviso=row['Aviso'],
                        IdFamilia=int(row['IdFamilia']) if row['IdFamilia'] else None,
                        IdSubFamilia=int(row['IdSubFamilia']) if row['IdSubFamilia'] else None,
                        IdDepartamento=int(row['IdDepartamento']) if row['IdDepartamento'] else None,
                        IdSeccion=int(row['IdSeccion']) if row['IdSeccion'] else None,
                        Favorito=bool(int(row['Favorito'])) if row['Favorito'] else True,
                        Texto1=row['Texto1'],
                        TextoLibre=row['TextoLibre'],
                        EANScanner=row['EANScanner'],
                        IdEmpresa=1,
                        Usuario=current_user.username,
                        TimeStamp=datetime.utcnow(),
                        Marca=1
                    )
                    db.session.add(article)
                    count_created += 1
            
            db.session.commit()
            flash(f'Successfully imported {count_created} new articles and updated {count_updated} existing articles.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing sample data: {str(e)}', 'danger')
    
    return redirect(url_for('articles.index')) 