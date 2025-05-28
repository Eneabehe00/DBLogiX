from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_, text, cast, String
from models import db, Article
from forms import ArticleSearchForm, ArticleForm, ArticleDeleteForm
import csv
import os
from datetime import datetime
from decimal import Decimal
import base64
from werkzeug.utils import secure_filename
from utils import admin_required, is_admin

articles_bp = Blueprint('articles', __name__)

def format_price(price):
    """Format a price value for display"""
    if price is None:
        return 'N/A'
    try:
        return f"€ {float(price):.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return 'N/A'

def parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.'))
    except:
        return None

def load_sections():
    """Load sections from dat_seccion table"""
    try:
        # Using raw SQL since we don't have a model for dat_seccion
        result = db.session.execute(text("SELECT IdSeccion, NombreSeccion FROM dat_seccion ORDER BY NombreSeccion"))
        sections = [(row[0], row[1]) for row in result]
        return sections
    except Exception as e:
        print(f"Error loading sections: {str(e)}")
        return []

def load_families():
    """Load families from dat_familia table"""
    try:
        result = db.session.execute(text("SELECT IdFamilia, NombreFamilia FROM dat_familia ORDER BY NombreFamilia"))
        families = [(row[0], row[1]) for row in result]
        return families
    except Exception as e:
        print(f"Error loading families: {str(e)}")
        return []

def load_departments():
    """Load departments from dat_departamento table"""
    try:
        result = db.session.execute(text("SELECT IdDepartamento, NombreDepartamento FROM dat_departamento ORDER BY NombreDepartamento"))
        departments = [(row[0], row[1]) for row in result]
        return departments
    except Exception as e:
        print(f"Error loading departments: {str(e)}")
        return []

def load_iva_rates():
    """Load IVA rates from dat_iva table"""
    try:
        result = db.session.execute(text("SELECT IdIVA, PorcentajeIVA FROM dat_iva ORDER BY PorcentajeIVA"))
        iva_rates = [(row[0], f"{row[1]}%") for row in result]
        return iva_rates
    except Exception as e:
        print(f"Error loading IVA rates: {str(e)}")
        return [(1, "4%"), (2, "10%"), (3, "22%")]  # Default values

def load_traceability_classes():
    """Load traceability classes from dat_clase table"""
    try:
        result = db.session.execute(text("SELECT IdClase, NombreClase FROM dat_clase ORDER BY NombreClase"))
        classes = [{"IdClase": row[0], "NombreClase": row[1]} for row in result]
        return classes
    except Exception as e:
        print(f"Error loading traceability classes: {str(e)}")
        return []

def load_associated_lots(id_clase):
    """Load associated lots from dat_elem_asociado table"""
    try:
        result = db.session.execute(text("SELECT IdElemAsociado, NombreElemAsociado, Peso, FechaCaducidad FROM dat_elem_asociado WHERE IdClase = :id_clase"),
                                   {"id_clase": id_clase})
        lots = [{"IdElemAsociado": row[0], 
                "NombreElemAsociado": row[1], 
                "Peso": row[2],
                "FechaCaducidad": row[3]} for row in result]
        return lots
    except Exception as e:
        print(f"Error loading associated lots: {str(e)}")
        return []

def load_article_eanscanners(id_articulo):
    """Load EAN scanners for an article from dat_articulo_eanscanner table"""
    try:
        result = db.session.execute(text("""
            SELECT IdRegistro, EANScanner, Activo 
            FROM dat_articulo_eanscanner 
            WHERE IdArticulo = :id_articulo
            ORDER BY Activo DESC, IdRegistro DESC
        """), {"id_articulo": id_articulo})
        
        eanscanner_list = [{"IdRegistro": row[0], "EANScanner": row[1], "Activo": row[2]} for row in result]
        return eanscanner_list
    except Exception as e:
        print(f"Error loading EAN scanners: {str(e)}")
        return []

def load_article_tickets(id_articulo, limit=10):
    """Load the most recent tickets related to an article"""
    try:
        result = db.session.execute(text("""
            SELECT tc.IdTicket, tc.NumTicket, tc.Fecha, tc.Enviado, tl.Descripcion, tl.Peso, tl.comportamiento
            FROM dat_ticket_cabecera tc 
            JOIN dat_ticket_linea tl ON tc.IdTicket = tl.IdTicket
            WHERE tl.IdArticulo = :id_articulo
            ORDER BY tc.Fecha DESC
            LIMIT :limit
        """), {"id_articulo": id_articulo, "limit": limit})
        
        tickets = []
        for row in result:
            ticket = {
                "IdTicket": row[0],
                "NumTicket": row[1],
                "Fecha": row[2],
                "Enviado": row[3],
                "Descripcion": row[4],
                "Peso": row[5],
                "Comportamiento": row[6]
            }
            # Formattare la data
            if ticket["Fecha"]:
                ticket["FechaFormateada"] = ticket["Fecha"].strftime('%d/%m/%Y %H:%M')
            else:
                ticket["FechaFormateada"] = "N/A"
            
            # Impostare lo stato del ticket
            if ticket["Enviado"] == 0:
                ticket["EstadoTicket"] = "Giacenza"
            elif ticket["Enviado"] == 1:
                ticket["EstadoTicket"] = "Processato"
            elif ticket["Enviado"] == 2:
                ticket["EstadoTicket"] = "DDT1"
            elif ticket["Enviado"] == 3:
                ticket["EstadoTicket"] = "DDT2"
            elif ticket["Enviado"] == 4:
                ticket["EstadoTicket"] = "Scaduto"
            else:
                ticket["EstadoTicket"] = "Sconosciuto"
                
            tickets.append(ticket)
        
        return tickets
    except Exception as e:
        print(f"Error loading tickets: {str(e)}")
        return []

def save_eanscanner(id_articulo, eanscanner, activo=1):
    """Save EAN scanner to dat_articulo_eanscanner table"""
    try:
        # Log inputs to help with debugging
        print(f"Attempting to save EAN scanner: Article ID={id_articulo}, EAN={eanscanner}, Activo={activo}")
        
        # If we're setting this EAN as active, deactivate all others
        if activo == 1:
            # Assicuriamoci di disattivare tutti gli altri EAN scanner per questo articolo
            db.session.execute(text("""
                UPDATE dat_articulo_eanscanner 
                SET Activo = 0, 
                    Modificado = 1,
                    Usuario = 'DBLogiX',
                    TimeStamp = NOW()
                WHERE IdArticulo = :id_articulo
            """), {"id_articulo": id_articulo})
            print(f"Deactivated all existing EAN scanners for article {id_articulo}")
        
        # Check if this EAN scanner already exists for this article
        result = db.session.execute(text("""
            SELECT IdRegistro FROM dat_articulo_eanscanner 
            WHERE IdArticulo = :id_articulo AND EANScanner = :eanscanner
        """), {"id_articulo": id_articulo, "eanscanner": eanscanner}).fetchone()
        
        if result:
            # Update existing record
            print(f"EAN scanner already exists (IdRegistro={result[0]}). Updating...")
            db.session.execute(text("""
                UPDATE dat_articulo_eanscanner 
                SET Activo = :activo,
                    Modificado = 1,
                    Usuario = 'DBLogiX',
                    TimeStamp = NOW()
                WHERE IdRegistro = :id_registro
            """), {"id_registro": result[0], "activo": activo})
            print(f"Updated existing EAN scanner (IdRegistro={result[0]})")
        else:
            # Insert new record
            print(f"EAN scanner doesn't exist. Creating new record...")
            
            # Calculate the next available IdRegistro for this article
            max_id_result = db.session.execute(text("""
                SELECT MAX(IdRegistro) FROM dat_articulo_eanscanner
                WHERE IdArticulo = :id_articulo
            """), {"id_articulo": id_articulo}).fetchone()
            
            next_id = 1
            if max_id_result and max_id_result[0] is not None:
                next_id = max_id_result[0] + 1
            
            print(f"Next IdRegistro for article {id_articulo} will be {next_id}")
            
            insert_query = """
                INSERT INTO dat_articulo_eanscanner 
                (IdRegistro, IdArticulo, EANScanner, Activo, IdEmpresa, Modificado, Operacion, Usuario, TimeStamp)
                VALUES
                (:id_registro, :id_articulo, :eanscanner, :activo, 1, 1, 'A', 'DBLogiX', NOW())
            """
            print(f"Executing insert query with params: id_registro={next_id}, id_articulo={id_articulo}, eanscanner={eanscanner}, activo={activo}")
            
            result = db.session.execute(text(insert_query), {
                "id_registro": next_id,
                "id_articulo": id_articulo, 
                "eanscanner": eanscanner, 
                "activo": activo
            })
            
            print(f"Insert result: {result.rowcount} rows affected")
        
        # Final check: make sure there's only one active EAN scanner
        # Count active EAN scanners for this article
        active_count = db.session.execute(text("""
            SELECT COUNT(*) FROM dat_articulo_eanscanner
            WHERE IdArticulo = :id_articulo AND Activo = 1
        """), {"id_articulo": id_articulo}).scalar()
        
        print(f"Active EAN scanners for article {id_articulo}: {active_count}")
        
        if active_count > 1:
            print(f"WARNING: Found {active_count} active EAN scanners for article {id_articulo}. Fixing...")
            
            # Get the most recently updated one (should be the one we just added/updated)
            latest_ean = db.session.execute(text("""
                SELECT IdRegistro FROM dat_articulo_eanscanner
                WHERE IdArticulo = :id_articulo AND Activo = 1
                ORDER BY TimeStamp DESC LIMIT 1
            """), {"id_articulo": id_articulo}).scalar()
            
            if latest_ean:
                print(f"Keeping only the most recent EAN scanner (IdRegistro={latest_ean}) active")
                
                # Deactivate all others
                db.session.execute(text("""
                    UPDATE dat_articulo_eanscanner 
                    SET Activo = 0,
                        Modificado = 1,
                        Usuario = 'DBLogiX',
                        TimeStamp = NOW()
                    WHERE IdArticulo = :id_articulo AND IdRegistro != :id_registro
                """), {"id_articulo": id_articulo, "id_registro": latest_ean})
        
        # Make sure changes are committed immediately
        db.session.commit()
        print(f"Changes committed successfully")
        
        return True
    except Exception as e:
        print(f"ERROR saving EAN scanner: {str(e)}")
        db.session.rollback()
        print(f"Transaction rolled back due to error")
        return False

def delete_eanscanner(id_registro):
    """Delete EAN scanner from dat_articulo_eanscanner table"""
    try:
        db.session.execute(text("""
            DELETE FROM dat_articulo_eanscanner 
            WHERE IdRegistro = :id_registro
        """), {"id_registro": id_registro})
        return True
    except Exception as e:
        print(f"Error deleting EAN scanner: {str(e)}")
        return False

def save_articulo_balanza(id_articulo, usuario="DBLogiX"):
    """Save article to dat_articulo_t_b table for balanza association"""
    try:
        # Check if record already exists
        existing_record = db.session.execute(text("""
            SELECT COUNT(*) FROM dat_articulo_t_b 
            WHERE IdArticulo = :id_articulo AND IdEmpresa = 1 AND IdTienda = 1 AND IdBalanza = 1
        """), {"id_articulo": id_articulo}).scalar()
        
        if existing_record > 0:
            print(f"dat_articulo_t_b record already exists for article ID {id_articulo}")
            return True
        
        # Insert new record
        sql_insert_balanza = """
            INSERT INTO dat_articulo_t_b 
            (IdArticulo, IdEmpresa, IdTienda, IdBalanza, Modificado, Operacion, Usuario, TimeStamp)
            VALUES
            (:id_articulo, 1, 1, 1, 1, 'A', :usuario, NOW())
        """
        
        db.session.execute(text(sql_insert_balanza), {
            'id_articulo': id_articulo,
            'usuario': usuario
        })
        
        print(f"Successfully created dat_articulo_t_b record for article ID {id_articulo}")
        return True
    except Exception as e:
        print(f"Error creating dat_articulo_t_b record: {str(e)}")
        return False

def save_articulo_t(id_articulo, usuario="DBLogiX"):
    """Save article to dat_articulo_t table for tienda association"""
    try:
        # Check if record already exists
        existing_record = db.session.execute(text("""
            SELECT COUNT(*) FROM dat_articulo_t 
            WHERE IdArticulo = :id_articulo AND IdEmpresa = 1 AND IdTienda = 1
        """), {"id_articulo": id_articulo}).scalar()
        
        if existing_record > 0:
            print(f"dat_articulo_t record already exists for article ID {id_articulo}")
            return True
        
        # Insert new record
        sql_insert_t = """
            INSERT INTO dat_articulo_t 
            (IdArticulo, IdEmpresa, IdTienda, Modificado, Operacion, Usuario, TimeStamp)
            VALUES
            (:id_articulo, 1, 1, 1, 'A', :usuario, NOW())
        """
        
        db.session.execute(text(sql_insert_t), {
            'id_articulo': id_articulo,
            'usuario': usuario
        })
        
        print(f"Successfully created dat_articulo_t record for article ID {id_articulo}")
        return True
    except Exception as e:
        print(f"Error creating dat_articulo_t record: {str(e)}")
        return False

def calculate_article_quantity(id_articulo):
    """
    Calculate the total number of pending tickets for an article.
    Returns the count of pending tickets (Enviado = 0) for this article.
    This represents how many tickets containing this article are pending.
    """
    try:
        # Count pending tickets (Enviado = 0) for this article
        result = db.session.execute(text("""
            SELECT COUNT(*) as ticket_count
            FROM dat_ticket_linea tl
            JOIN dat_ticket_cabecera tc ON tl.IdTicket = tc.IdTicket
            WHERE tl.IdArticulo = :id_articulo
            AND tc.Enviado = 0
        """), {"id_articulo": id_articulo}).fetchone()
        
        # Return the count of pending tickets
        ticket_count = result[0] if result else 0
        return ticket_count
    except Exception as e:
        print(f"Error calculating article quantity: {str(e)}")
        return 0

@articles_bp.route('/')
@login_required
def index():
    try:
        page = request.args.get('page', 1, type=int)
        search_form = ArticleSearchForm()
        
        # Get search query if exists
        query = request.args.get('query', '')
        
        # Query articles
        if query:
            try:
                # First check if we can find any products by EAN code
                ean_article_ids = []
                try:
                    # Run raw SQL query to get article IDs matching EAN scanner
                    ean_result = db.session.execute(text("""
                        SELECT IdArticulo FROM dat_articulo_eanscanner 
                        WHERE EANScanner LIKE :ean
                    """), {"ean": f'%{query}%'}).fetchall()
                    
                    # Extract article IDs
                    ean_article_ids = [row[0] for row in ean_result]
                except Exception:
                    pass
                
                # Now build the query
                if ean_article_ids:
                    # If we found EANs, include them in the search
                    articles_base_query = Article.query.filter(
                        or_(
                            Article.Descripcion.ilike(f'%{query}%'),
                            cast(Article.IdArticulo, String).ilike(f'%{query}%'),
                            Article.IdArticulo.in_(ean_article_ids)
                        )
                    )
                else:
                    # Otherwise just search by description and ID
                    articles_base_query = Article.query.filter(
                        or_(
                            Article.Descripcion.ilike(f'%{query}%'),
                            cast(Article.IdArticulo, String).ilike(f'%{query}%')
                        )
                    )
            except Exception as e:
                raise
        else:
            articles_base_query = Article.query
        
        # Order by ID
        articles_base_query = articles_base_query.order_by(Article.IdArticulo)
        
        # Paginate the results
        try:
            articles_paged = articles_base_query.paginate(page=page, per_page=20)
        except Exception as e:
            raise
        
        # Get sections info for all articles on this page
        articles_ids = [article.IdArticulo for article in articles_paged.items]
        
        try:
            # Get sections names
            section_info = {}
            if articles_ids:
                try:
                    # Handle the case when there's only one article ID
                    if len(articles_ids) == 1:
                        query_params = {"ids": (articles_ids[0],)}
                    else:
                        query_params = {"ids": tuple(articles_ids)}
                    
                    sections_result = db.session.execute(text("""
                        SELECT a.IdArticulo, s.NombreSeccion 
                        FROM dat_articulo a
                        LEFT JOIN dat_seccion s ON a.IdSeccion = s.IdSeccion
                        WHERE a.IdArticulo IN :ids
                    """), query_params).fetchall()
                    
                    for row in sections_result:
                        section_info[row[0]] = row[1] or 'N/A'
                except Exception:
                    section_info = {}  # Use empty dict if there's an error
            
            # Get IVA rates info
            iva_rates = {}
            if articles_ids:
                try:
                    # Handle the case when there's only one article ID
                    if len(articles_ids) == 1:
                        query_params = {"ids": (articles_ids[0],)}
                    else:
                        query_params = {"ids": tuple(articles_ids)}
                    
                    iva_result = db.session.execute(text("""
                        SELECT a.IdArticulo, i.PorcentajeIVA 
                        FROM dat_articulo a
                        LEFT JOIN dat_iva i ON a.IdIVA = i.IdIVA
                        WHERE a.IdArticulo IN :ids
                    """), query_params).fetchall()
                    
                    for row in iva_result:
                        iva_rates[row[0]] = f"{row[1]}%" if row[1] is not None else 'N/A'
                except Exception:
                    iva_rates = {}  # Use empty dict if there's an error
            
            # Calculate quantity for each article
            article_quantities = {}
            try:
                for article_id in articles_ids:
                    try:
                        article_quantities[article_id] = calculate_article_quantity(article_id)
                    except Exception:
                        article_quantities[article_id] = 0
            except Exception:
                article_quantities = {}
        
        except Exception:
            # Continue with empty data if there's an error
            section_info = {}
            iva_rates = {}
            article_quantities = {}
        
        return render_template('articles/index.html', 
                            articles=articles_paged, 
                            search_form=search_form,
                            query=query,
                            section_info=section_info,
                            iva_rates=iva_rates,
                            article_quantities=article_quantities)
    
    except Exception as e:
        import traceback
        # Return a simple error template instead of 500
        return render_template('articles/index.html', 
                            articles=None,  # Use None to indicate error state 
                            search_form=ArticleSearchForm(),
                            query=request.args.get('query', ''),
                            section_info={},
                            iva_rates={},
                            article_quantities={},
                            error=str(e))

@articles_bp.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query', '')
    
    # If we have a query, redirect to the index page with the query parameter
    if query:
        return redirect(url_for('articles.index', query=query))
    
    # If no query, just go back to the index
    return redirect(url_for('articles.index'))

@articles_bp.route('/view/<int:id>')
@login_required
def view(id):
    article = Article.query.get_or_404(id)
    
    # Load traceability data
    lotes_asociados = []
    clase_nombre = 'N/A'
    
    if article.IdClase:
        lotes_asociados = load_associated_lots(article.IdClase)
        # Get clase name
        result = db.session.execute(text("SELECT NombreClase FROM dat_clase WHERE IdClase = :id_clase"),
                                   {"id_clase": article.IdClase}).fetchone()
        if result:
            clase_nombre = result[0]
    
    # Load EAN scanner data
    eanscanner_list = load_article_eanscanners(id)
    
    # Load recent tickets for this article
    article_tickets = load_article_tickets(id, limit=10)
    
    # Get descriptive names for related entities
    familia_nombre = 'N/A'
    subfamilia_nombre = 'N/A'
    departamento_nombre = 'N/A'
    seccion_nombre = 'N/A'
    
    # Get family name
    if article.IdFamilia:
        familia_result = db.session.execute(text("SELECT NombreFamilia FROM dat_familia WHERE IdFamilia = :id"),
                                         {"id": article.IdFamilia}).fetchone()
        if familia_result:
            familia_nombre = familia_result[0]
    
    # Get subfamily name
    if article.IdSubFamilia:
        subfamilia_result = db.session.execute(text("SELECT NombreSubFamilia FROM dat_subfamilia WHERE IdSubFamilia = :id"),
                                            {"id": article.IdSubFamilia}).fetchone()
        if subfamilia_result:
            subfamilia_nombre = subfamilia_result[0]
    
    # Get department name
    if article.IdDepartamento:
        departamento_result = db.session.execute(text("SELECT NombreDepartamento FROM dat_departamento WHERE IdDepartamento = :id"),
                                               {"id": article.IdDepartamento}).fetchone()
        if departamento_result:
            departamento_nombre = departamento_result[0]
    
    # Get section name
    if article.IdSeccion:
        seccion_result = db.session.execute(text("SELECT NombreSeccion FROM dat_seccion WHERE IdSeccion = :id"),
                                          {"id": article.IdSeccion}).fetchone()
        if seccion_result:
            seccion_nombre = seccion_result[0]
    
    return render_template('articles/view.html', 
                          article=article,
                          lotes_asociados=lotes_asociados,
                          clase_nombre=clase_nombre,
                          eanscanner_list=eanscanner_list,
                          familia_nombre=familia_nombre,
                          subfamilia_nombre=subfamilia_nombre,
                          departamento_nombre=departamento_nombre,
                          seccion_nombre=seccion_nombre,
                          article_tickets=article_tickets)

@articles_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create():
    form = ArticleForm()
    
    # Load data for dropdowns
    form.id_seccion.choices = [(0, 'Seleziona una sezione')] + load_sections()
    form.id_familia.choices = [(0, 'Seleziona una famiglia')] + load_families()
    form.id_departamento.choices = [(0, 'Seleziona un reparto')] + load_departments()
    form.id_iva.choices = load_iva_rates()
    
    # Get traceability classes for the dropdown
    clases_trazabilidad = load_traceability_classes()
    form.id_clase.choices = [(0, 'Seleziona una classe')] + [(clase["IdClase"], f"{clase['NombreClase']} ({clase['IdClase']})") for clase in clases_trazabilidad]
    
    if form.validate_on_submit():
        # Find the next available ID
        max_id = db.session.query(db.func.max(Article.IdArticulo)).scalar() or 0
        new_id = max_id + 1
        
        article = Article(
            IdArticulo=new_id if not form.id_articulo.data else form.id_articulo.data,
            Descripcion=form.descripcion.data,
            Descripcion1=form.descripcion1.data,
            IdTipo=form.id_tipo.data,
            IdFamilia=form.id_familia.data,
            IdSubFamilia=form.id_subfamilia.data,
            IdDepartamento=form.id_departamento.data,
            IdSeccion=form.id_seccion.data,
            TeclaDirecta=form.tasto_directo.data,
            TaraFija=form.tara_fija.data,
            Favorito=form.favorito.data,
            PrecioSinIVA=form.precio_sin_iva.data,
            IdIVA=form.id_iva.data,
            PrecioConIVA=form.precio_con_iva.data,
            Texto1=form.texto1.data,
            Texto2=form.texto2.data,
            Texto3=form.texto3.data,
            Texto4=form.texto4.data,
            Texto5=form.texto5.data,
            Texto6=form.texto6.data,
            Texto7=form.texto7.data,
            Texto8=form.texto8.data,
            Texto9=form.texto9.data,
            Texto10=form.texto10.data,
            Texto11=form.texto11.data,
            Texto12=form.texto12.data,
            Texto13=form.texto13.data,
            Texto14=form.texto14.data,
            Texto15=form.texto15.data,
            Texto16=form.texto16.data,
            Texto17=form.texto17.data,
            Texto18=form.texto18.data,
            Texto19=form.texto19.data,
            Texto20=form.texto20.data,
            TextoLibre=form.texto_libre.data,
            StockActual=form.stock_actual.data,
            PesoMinimo=form.peso_minimo.data,
            PesoMaximo=form.peso_maximo.data,
            PesoObjetivo=form.peso_objetivo.data,
            FechaCaducidadActivada=form.fecha_caducidad_activada.data,
            DiasCaducidad=form.dias_caducidad.data,
            EnVenta=form.en_venta.data,
            IncluirGestionStock=form.incluir_gestion_stock.data,
            IdClase=form.id_clase.data,
            IdEmpresa=1,  # Default company ID
            Usuario=current_user.username,
            TimeStamp=datetime.utcnow(),
            Marca=1,  # Default value
            Modificado=True,  # Impostato a 1 come nell'articolo 63 funzionante
            Operacion="A",  # A = Aggiunto, come nell'articolo 63 funzionante
        )
        
        # Remove EANScanner from Article creation - we'll use dat_articulo_eanscanner table instead
        article.EANScanner = None
        
        db.session.add(article)
        db.session.flush()  # Get the article ID without committing
        
        # Now insert Texto2-Texto20 using direct SQL
        id_articulo = article.IdArticulo
        
        # Use parameterized queries to prevent SQL injection and set required fields
        sql_update = """
            UPDATE dat_articulo 
            SET 
                Texto2 = :texto2, 
                Texto3 = :texto3,
                Texto4 = :texto4,
                Texto5 = :texto5,
                Texto6 = :texto6,
                Texto7 = :texto7,
                Texto8 = :texto8,
                Texto9 = :texto9,
                Texto10 = :texto10,
                Texto11 = :texto11,
                Texto12 = :texto12,
                Texto13 = :texto13,
                Texto14 = :texto14,
                Texto15 = :texto15,
                Texto16 = :texto16,
                Texto17 = :texto17,
                Texto18 = :texto18,
                Texto19 = :texto19,
                Texto20 = :texto20,
                Modificado = 1,
                Operacion = 'A',
                TipoCalculo = 1,
                AplicarRE = 1,
                TipoDescuento = 1,
                NumUnidadesDto = 2,
                IdCodBarras = 0,
                ModificadoTextos = 0,
                ModificadoTextoG = 0
            WHERE IdArticulo = :id_articulo
        """
        
        db.session.execute(text(sql_update), {
            'texto2': form.texto2.data or "",
            'texto3': form.texto3.data or "",
            'texto4': form.texto4.data or "",
            'texto5': form.texto5.data or "",
            'texto6': form.texto6.data or "",
            'texto7': form.texto7.data or "",
            'texto8': form.texto8.data or "",
            'texto9': form.texto9.data or "",
            'texto10': form.texto10.data or "",
            'texto11': form.texto11.data or "",
            'texto12': form.texto12.data or "",
            'texto13': form.texto13.data or "",
            'texto14': form.texto14.data or "",
            'texto15': form.texto15.data or "",
            'texto16': form.texto16.data or "",
            'texto17': form.texto17.data or "",
            'texto18': form.texto18.data or "",
            'texto19': form.texto19.data or "",
            'texto20': form.texto20.data or "",
            'id_articulo': id_articulo
        })
        
        # Save EAN Scanner to dat_articulo_eanscanner if provided
        if form.ean_scanner.data:
            print(f"Creating EAN scanner for article ID {id_articulo}: {form.ean_scanner.data}")
            ean_result = save_eanscanner(id_articulo, form.ean_scanner.data, activo=1)
            if not ean_result:
                flash('Article created but EAN scanner could not be saved. Please add it manually.', 'warning')
        
        # Insert record into dat_articulo_t_b table for balanza association
        balanza_result = save_articulo_balanza(id_articulo, current_user.username)
        if not balanza_result:
            flash('Article created but balanza association could not be saved.', 'warning')
        
        # Insert record into dat_articulo_t table for tienda association
        tienda_result = save_articulo_t(id_articulo, current_user.username)
        if not tienda_result:
            flash('Article created but tienda association could not be saved.', 'warning')
        
        db.session.commit()
        
        flash('Article created successfully', 'success')
        return redirect(url_for('articles.view', id=article.IdArticulo))
    
    return render_template('articles/create.html', 
                          form=form, 
                          clases_trazabilidad=clases_trazabilidad)

@articles_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    article = Article.query.get_or_404(id)
    form = ArticleForm()
    
    # Load data for dropdowns
    form.id_seccion.choices = [(0, 'Seleziona una sezione')] + load_sections()
    form.id_familia.choices = [(0, 'Seleziona una famiglia')] + load_families()
    form.id_departamento.choices = [(0, 'Seleziona un reparto')] + load_departments()
    form.id_iva.choices = load_iva_rates()
    
    # Get traceability classes for the dropdown
    clases_trazabilidad = load_traceability_classes()
    form.id_clase.choices = [(0, 'Seleziona una classe')] + [(clase["IdClase"], f"{clase['NombreClase']} ({clase['IdClase']})") for clase in clases_trazabilidad]
    
    # Handle reload_clase parameter - when a user changes the clase
    reload_clase = request.args.get('reload_clase', None)
    if reload_clase and reload_clase.isdigit():
        id_clase = int(reload_clase)
        article.IdClase = id_clase  # Temporarily update for display only
    
    # Load traceability data
    lotes_asociados = []
    if article.IdClase:
        lotes_asociados = load_associated_lots(article.IdClase)
    
    # Load EAN scanner codes
    eanscanner_list = load_article_eanscanners(id)
    
    # Load Texto2-Texto20 from database directly with raw SQL
    if request.method == 'GET':
        # Query the extra text fields directly from the database
        try:
            sql = "SELECT Texto2, Texto3, Texto4, Texto5, Texto6, Texto7, Texto8, Texto9, Texto10, Texto11, Texto12, Texto13, Texto14, Texto15, Texto16, Texto17, Texto18, Texto19, Texto20 FROM dat_articulo WHERE IdArticulo = :id"
            result = db.session.execute(text(sql), {'id': id}).fetchone()
            
            if result:
                article.Texto2 = result[0]
                article.Texto3 = result[1]
                article.Texto4 = result[2]
                article.Texto5 = result[3]
                article.Texto6 = result[4]
                article.Texto7 = result[5]
                article.Texto8 = result[6]
                article.Texto9 = result[7]
                article.Texto10 = result[8]
                article.Texto11 = result[9]
                article.Texto12 = result[10]
                article.Texto13 = result[11]
                article.Texto14 = result[12]
                article.Texto15 = result[13]
                article.Texto16 = result[14]
                article.Texto17 = result[15]
                article.Texto18 = result[16]
                article.Texto19 = result[17]
                article.Texto20 = result[18]
        except Exception as e:
            flash(f'Error loading text fields: {str(e)}', 'warning')
    
    if request.method == 'GET':
        # Populate form with existing data
        form.id_articulo.data = article.IdArticulo
        form.descripcion.data = article.Descripcion
        form.descripcion1.data = article.Descripcion1
        form.id_tipo.data = article.IdTipo
        form.id_familia.data = article.IdFamilia
        form.id_subfamilia.data = article.IdSubFamilia
        form.id_departamento.data = article.IdDepartamento
        form.id_seccion.data = article.IdSeccion
        form.tasto_directo.data = article.TeclaDirecta
        form.tara_fija.data = article.TaraFija
        form.favorito.data = article.Favorito
        form.precio_sin_iva.data = article.PrecioSinIVA
        form.id_iva.data = article.IdIVA
        form.precio_con_iva.data = article.PrecioConIVA
        form.ean_scanner.data = article.EANScanner
        form.texto1.data = article.Texto1
        form.texto2.data = article.Texto2
        form.texto3.data = article.Texto3
        form.texto4.data = article.Texto4
        form.texto5.data = article.Texto5
        form.texto6.data = article.Texto6
        form.texto7.data = article.Texto7
        form.texto8.data = article.Texto8
        form.texto9.data = article.Texto9
        form.texto10.data = article.Texto10
        form.texto11.data = article.Texto11
        form.texto12.data = article.Texto12
        form.texto13.data = article.Texto13
        form.texto14.data = article.Texto14
        form.texto15.data = article.Texto15
        form.texto16.data = article.Texto16
        form.texto17.data = article.Texto17
        form.texto18.data = article.Texto18
        form.texto19.data = article.Texto19
        form.texto20.data = article.Texto20
        form.texto_libre.data = article.TextoLibre
        form.stock_actual.data = article.StockActual
        form.peso_minimo.data = article.PesoMinimo
        form.peso_maximo.data = article.PesoMaximo
        form.peso_objetivo.data = article.PesoObjetivo
        form.fecha_caducidad_activada.data = article.FechaCaducidadActivada
        form.dias_caducidad.data = article.DiasCaducidad
        form.en_venta.data = article.EnVenta
        form.incluir_gestion_stock.data = article.IncluirGestionStock
        form.id_clase.data = article.IdClase
        form.logo_pantalla.data = article.LogoPantalla if hasattr(article, 'LogoPantalla') else None
    
    if form.validate_on_submit():
        # Update article with form data
        article.Descripcion = form.descripcion.data
        article.Descripcion1 = form.descripcion1.data
        article.IdTipo = form.id_tipo.data
        article.IdFamilia = form.id_familia.data
        article.IdSubFamilia = form.id_subfamilia.data
        article.IdDepartamento = form.id_departamento.data
        article.IdSeccion = form.id_seccion.data
        article.TeclaDirecta = form.tasto_directo.data
        article.TaraFija = form.tara_fija.data
        article.Favorito = form.favorito.data
        article.PrecioSinIVA = form.precio_sin_iva.data
        article.IdIVA = form.id_iva.data
        article.PrecioConIVA = form.precio_con_iva.data
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
        article.IdClase = form.id_clase.data
        article.Usuario = current_user.username
        article.TimeStamp = datetime.utcnow()
        article.Modificado = True
        
        # Update LogoPantalla if provided in the form
        if form.logo_pantalla.data:
            # Only update if the field has been modified
            # The field is usually updated via the upload_photo route
            logo_path = form.logo_pantalla.data
            db.session.execute(text("""
                UPDATE dat_articulo 
                SET LogoPantalla = :logo_path
                WHERE IdArticulo = :id_articulo
            """), {
                "logo_path": logo_path,
                "id_articulo": article.IdArticulo
            })
        
        db.session.flush()  # Update without committing
        
        # Now update Texto2-Texto20 using direct SQL
        sql_update = """
            UPDATE dat_articulo 
            SET 
                Texto2 = :texto2, 
                Texto3 = :texto3,
                Texto4 = :texto4,
                Texto5 = :texto5,
                Texto6 = :texto6,
                Texto7 = :texto7,
                Texto8 = :texto8,
                Texto9 = :texto9,
                Texto10 = :texto10,
                Texto11 = :texto11,
                Texto12 = :texto12,
                Texto13 = :texto13,
                Texto14 = :texto14,
                Texto15 = :texto15,
                Texto16 = :texto16,
                Texto17 = :texto17,
                Texto18 = :texto18,
                Texto19 = :texto19,
                Texto20 = :texto20
            WHERE IdArticulo = :id_articulo
        """
        
        db.session.execute(text(sql_update), {
            'texto2': form.texto2.data,
            'texto3': form.texto3.data,
            'texto4': form.texto4.data,
            'texto5': form.texto5.data,
            'texto6': form.texto6.data,
            'texto7': form.texto7.data,
            'texto8': form.texto8.data,
            'texto9': form.texto9.data,
            'texto10': form.texto10.data,
            'texto11': form.texto11.data,
            'texto12': form.texto12.data,
            'texto13': form.texto13.data,
            'texto14': form.texto14.data,
            'texto15': form.texto15.data,
            'texto16': form.texto16.data,
            'texto17': form.texto17.data,
            'texto18': form.texto18.data,
            'texto19': form.texto19.data,
            'texto20': form.texto20.data,
            'id_articulo': article.IdArticulo
        })
        
        # Check if EAN scanner has changed
        if form.ean_scanner.data and not eanscanner_list:
            # No existing EAN scanners but now we have one, add it
            print(f"Adding new EAN scanner for article ID {article.IdArticulo}: {form.ean_scanner.data}")
            
            # Verifica se questo EAN scanner esiste già per qualche motivo
            duplicate_check = db.session.execute(text("""
                SELECT COUNT(*) FROM dat_articulo_eanscanner 
                WHERE IdArticulo = :id_articulo AND EANScanner = :eanscanner
            """), {"id_articulo": article.IdArticulo, "eanscanner": form.ean_scanner.data}).scalar()
            
            if duplicate_check > 0:
                flash('Questo EAN scanner esiste già per questo articolo.', 'warning')
            else:
                # Prima disattiva tutti gli EAN scanner esistenti
                db.session.execute(text("""
                    UPDATE dat_articulo_eanscanner 
                    SET Activo = 0,
                        Modificado = 1,
                        Usuario = 'DBLogiX',
                        TimeStamp = NOW()
                    WHERE IdArticulo = :id_articulo
                """), {"id_articulo": article.IdArticulo})
                
                ean_result = save_eanscanner(article.IdArticulo, form.ean_scanner.data, activo=1)
                if not ean_result:
                    flash('Article updated but EAN scanner could not be saved. Please add it manually.', 'warning')
        elif form.ean_scanner.data:
            # Find if this EAN scanner already exists
            existing = False
            for ean in eanscanner_list:
                if ean['EANScanner'] == form.ean_scanner.data:
                    existing = True
                    # If it's not the active one, activate it
                    if ean['Activo'] != 1:
                        print(f"Activating existing EAN scanner {ean['IdRegistro']} for article {article.IdArticulo}")
                        try:
                            # Prima disattiva tutti gli EAN scanner
                            db.session.execute(text("""
                                UPDATE dat_articulo_eanscanner 
                                SET Activo = 0,
                                    Modificado = 1,
                                    Usuario = 'DBLogiX',
                                    TimeStamp = NOW()
                                WHERE IdArticulo = :id_articulo
                            """), {"id_articulo": article.IdArticulo})
                            
                            # Poi attiva solo quello selezionato
                            db.session.execute(text("""
                                UPDATE dat_articulo_eanscanner 
                                SET Activo = 1,
                                    Modificado = 1,
                                    Usuario = 'DBLogiX',
                                    TimeStamp = NOW()
                                WHERE IdRegistro = :id_registro
                            """), {"id_registro": ean['IdRegistro']})
                            
                            print(f"Successfully activated EAN scanner {ean['IdRegistro']}")
                        except Exception as e:
                            print(f"Error activating EAN scanner: {str(e)}")
                            flash('Error activating existing EAN scanner', 'danger')
                    break
            
            # If it doesn't exist, add it
            if not existing:
                print(f"Adding new EAN scanner for article ID {article.IdArticulo}: {form.ean_scanner.data}")
                
                # Prima disattiva tutti gli EAN scanner esistenti
                db.session.execute(text("""
                    UPDATE dat_articulo_eanscanner 
                    SET Activo = 0,
                        Modificado = 1,
                        Usuario = 'DBLogiX',
                        TimeStamp = NOW()
                    WHERE IdArticulo = :id_articulo
                """), {"id_articulo": article.IdArticulo})
                
                ean_result = save_eanscanner(article.IdArticulo, form.ean_scanner.data, activo=1)
                if not ean_result:
                    flash('Article updated but EAN scanner could not be saved. Please add it manually.', 'warning')
        
        # Set EANScanner to NULL in the main article table since we're using dat_articulo_eanscanner
        article.EANScanner = None
        
        db.session.commit()
        
        flash('Article updated successfully', 'success')
        return redirect(url_for('articles.view', id=article.IdArticulo))
    
    return render_template('articles/edit.html', 
                          form=form, 
                          article=article, 
                          clases_trazabilidad=clases_trazabilidad,
                          lotes_asociados=lotes_asociados,
                          eanscanner_list=eanscanner_list)

@articles_bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def delete(id):
    article = Article.query.get_or_404(id)
    
    # If it's a POST request, delete the article
    if request.method == 'POST':
        try:
            db.session.delete(article)
            db.session.commit()
            flash('Articolo eliminato con successo', 'success')
            return redirect(url_for('articles.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'eliminazione dell\'articolo: {str(e)}', 'danger')
            return redirect(url_for('articles.view', id=id))
    
    # If it's a GET request, show the confirmation page
    form = ArticleDeleteForm()
    return render_template('articles/delete.html', form=form, article=article)

@articles_bp.route('/import-from-csv', methods=['GET', 'POST'])
@login_required
@admin_required
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
                            Marca=1,
                            Modificado=True,
                            Operacion="A"
                        )
                        db.session.add(article)
                        db.session.flush()  # Flush to get the article ID
                        
                        # Insert record into dat_articulo_t_b table for balanza association for new articles
                        balanza_result = save_articulo_balanza(article.IdArticulo, current_user.username)
                        if not balanza_result:
                            print(f"Warning: Could not create dat_articulo_t_b record for imported article ID {article.IdArticulo}")
                        
                        # Insert record into dat_articulo_t table for tienda association for new articles
                        tienda_result = save_articulo_t(article.IdArticulo, current_user.username)
                        if not tienda_result:
                            print(f"Warning: Could not create dat_articulo_t record for imported article ID {article.IdArticulo}")
                    
                    # Save EAN Scanner to dat_articulo_eanscanner if provided
                    if 'EANScanner' in row and row['EANScanner']:
                        article.EANScanner = None  # Clear from main article table
                        db.session.flush()  # Flush to get the article ID if it's a new article
                        save_eanscanner(article.IdArticulo, row['EANScanner'], activo=1)
                
                db.session.commit()
                flash('Articles imported successfully', 'success')
            except Exception as e:
                flash(f'Error importing CSV: {str(e)}', 'danger')
                
            return redirect(url_for('articles.index'))
    
    return render_template('articles/import.html')

@articles_bp.route('/import-sample-data', methods=['GET'])
@login_required
@admin_required
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
                        IdEmpresa=1,
                        Usuario=current_user.username,
                        TimeStamp=datetime.utcnow(),
                        Marca=1,
                        Modificado=True,
                        Operacion="A"
                    )
                    db.session.add(article)
                    count_created += 1
                    db.session.flush()  # Flush to get the article ID
                    
                    # Insert record into dat_articulo_t_b table for balanza association for new articles
                    balanza_result = save_articulo_balanza(article.IdArticulo, current_user.username)
                    if not balanza_result:
                        print(f"Warning: Could not create dat_articulo_t_b record for sample article ID {article.IdArticulo}")
                    
                    # Insert record into dat_articulo_t table for tienda association for new articles
                    tienda_result = save_articulo_t(article.IdArticulo, current_user.username)
                    if not tienda_result:
                        print(f"Warning: Could not create dat_articulo_t record for sample article ID {article.IdArticulo}")
                
                # Save EAN Scanner to dat_articulo_eanscanner if provided
                if 'EANScanner' in row and row['EANScanner']:
                    article.EANScanner = None  # Clear from main article table
                    db.session.flush()  # Flush to get the article ID if it's a new article
                    save_eanscanner(article.IdArticulo, row['EANScanner'], activo=1)
            
            db.session.commit()
            flash(f'Successfully imported {count_created} new articles and updated {count_updated} existing articles.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error importing sample data: {str(e)}', 'danger')
    
    return redirect(url_for('articles.index'))

@articles_bp.route('/get-lot-details/<int:id_elem_asociado>')
@login_required
def get_lot_details(id_elem_asociado):
    """Get lot details from dat_detalle_elem_asociado table"""
    try:
        result = db.session.execute(text("""
            SELECT IdParametro, Parametro, Valor 
            FROM dat_detalle_elem_asociado 
            WHERE IdElemAsociado = :id_elem_asociado
            ORDER BY IdParametro
        """), {"id_elem_asociado": id_elem_asociado})
        
        details = [{"IdParametro": row[0], "Parametro": row[1], "Valor": row[2]} for row in result]
        return jsonify({"success": True, "data": details})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@articles_bp.route('/toggle-eanscanner/<int:id_registro>')
@login_required
@admin_required
def toggle_eanscanner(id_registro):
    """Toggle active status of an EAN scanner"""
    try:
        # Get the EAN scanner record
        result = db.session.execute(text("""
            SELECT IdArticulo FROM dat_articulo_eanscanner 
            WHERE IdRegistro = :id_registro
        """), {"id_registro": id_registro}).fetchone()
        
        if not result:
            return jsonify({"success": False, "error": "EAN scanner not found"})
        
        id_articulo = result[0]
        
        # Deactivate all EAN scanners for this article
        db.session.execute(text("""
            UPDATE dat_articulo_eanscanner 
            SET Activo = 0,
                Modificado = 1,
                Usuario = 'DBLogiX',
                TimeStamp = NOW()
            WHERE IdArticulo = :id_articulo
        """), {"id_articulo": id_articulo})
        
        # Activate the selected EAN scanner
        db.session.execute(text("""
            UPDATE dat_articulo_eanscanner 
            SET Activo = 1,
                Modificado = 1,
                Usuario = 'DBLogiX',
                TimeStamp = NOW()
            WHERE IdRegistro = :id_registro
        """), {"id_registro": id_registro})
        
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@articles_bp.route('/delete-eanscanner/<int:id_registro>')
@login_required
@admin_required
def remove_eanscanner(id_registro):
    """Remove an EAN scanner"""
    try:
        # Check if this is the active EAN scanner
        result = db.session.execute(text("""
            SELECT IdArticulo, Activo FROM dat_articulo_eanscanner 
            WHERE IdRegistro = :id_registro
        """), {"id_registro": id_registro}).fetchone()
        
        if not result:
            return jsonify({"success": False, "error": "EAN scanner not found"})
        
        id_articulo = result[0]
        was_active = result[1] == 1
        
        # Delete the EAN scanner
        db.session.execute(text("""
            DELETE FROM dat_articulo_eanscanner 
            WHERE IdRegistro = :id_registro
        """), {"id_registro": id_registro})
        
        # If it was active, set another one as active if available
        if was_active:
            # Find another EAN scanner for this article
            result = db.session.execute(text("""
                SELECT IdRegistro FROM dat_articulo_eanscanner 
                WHERE IdArticulo = :id_articulo 
                LIMIT 1
            """), {"id_articulo": id_articulo}).fetchone()
            
            if result:
                # Set it as active
                db.session.execute(text("""
                    UPDATE dat_articulo_eanscanner 
                    SET Activo = 1,
                        Modificado = 1,
                        Usuario = 'DBLogiX',
                        TimeStamp = NOW()
                    WHERE IdRegistro = :id_registro
                """), {"id_registro": result[0]})
        
        db.session.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

@articles_bp.route('/add-eanscanner/<int:id_articulo>', methods=['POST'])
@login_required
@admin_required
def add_eanscanner(id_articulo):
    """Add a new EAN scanner"""
    try:
        data = request.json
        eanscanner = data.get('eanscanner')
        
        if not eanscanner:
            return jsonify({"success": False, "error": "EAN scanner is required"})
        
        # Verifica se questo EAN scanner esiste già per questo articolo
        existing_ean = db.session.execute(text("""
            SELECT IdRegistro FROM dat_articulo_eanscanner 
            WHERE IdArticulo = :id_articulo AND EANScanner = :eanscanner
        """), {"id_articulo": id_articulo, "eanscanner": eanscanner}).fetchone()
        
        if existing_ean:
            return jsonify({"success": False, "error": "Questo EAN scanner esiste già per questo articolo"})
        
        # Prima disattiva tutti gli EAN scanner per questo articolo
        db.session.execute(text("""
            UPDATE dat_articulo_eanscanner 
            SET Activo = 0,
                Modificado = 1,
                Usuario = 'DBLogiX',
                TimeStamp = NOW()
            WHERE IdArticulo = :id_articulo
        """), {"id_articulo": id_articulo})
        
        # Save the EAN scanner
        result = save_eanscanner(id_articulo, eanscanner, activo=1)
        
        if result:
            db.session.commit()
            
            # Get the new EAN scanner record
            result = db.session.execute(text("""
                SELECT IdRegistro, EANScanner, Activo 
                FROM dat_articulo_eanscanner 
                WHERE IdArticulo = :id_articulo AND EANScanner = :eanscanner
            """), {"id_articulo": id_articulo, "eanscanner": eanscanner}).fetchone()
            
            if result:
                return jsonify({
                    "success": True, 
                    "eanscanner": {
                        "IdRegistro": result[0],
                        "EANScanner": result[1],
                        "Activo": result[2]
                    }
                })
        
        return jsonify({"success": False, "error": "Failed to save EAN scanner"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})

# API endpoint for real-time article search
@articles_bp.route('/api/search')
@login_required
def api_search():
    query = request.args.get('query', '')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    try:
        # First find articles with matching EAN codes
        ean_article_ids = []
        try:
            # Run raw SQL query to get article IDs matching EAN scanner
            ean_result = db.session.execute(text("""
                SELECT IdArticulo FROM dat_articulo_eanscanner 
                WHERE EANScanner LIKE :ean
            """), {"ean": f'%{query}%'}).fetchall()
            
            # Extract article IDs
            ean_article_ids = [row[0] for row in ean_result]
        except Exception:
            pass
        
        # Build the article query
        if ean_article_ids:
            # If we found matching EANs, include them
            articles_query = db.session.query(
                Article.IdArticulo,
                Article.Descripcion,
                Article.PrecioConIVA
            ).filter(
                or_(
                    Article.Descripcion.ilike(f'%{query}%'),
                    cast(Article.IdArticulo, String).ilike(f'%{query}%'),
                    Article.IdArticulo.in_(ean_article_ids)
                )
            ).order_by(Article.Descripcion).limit(10)
        else:
            # Just search by description and ID
            articles_query = db.session.query(
                Article.IdArticulo,
                Article.Descripcion,
                Article.PrecioConIVA
            ).filter(
                or_(
                    Article.Descripcion.ilike(f'%{query}%'),
                    cast(Article.IdArticulo, String).ilike(f'%{query}%')
                )
            ).order_by(Article.Descripcion).limit(10)
        
        results = []
        for article in articles_query:
            # Get EAN codes for this article
            ean_codes = []
            ean_result = db.session.execute(text("""
                SELECT EANScanner FROM dat_articulo_eanscanner 
                WHERE IdArticulo = :id AND Activo = 1
                LIMIT 1
            """), {"id": article.IdArticulo}).fetchone()
            
            if ean_result:
                ean_code = ean_result[0]
            else:
                ean_code = 'N/A'
            
            results.append({
                'id': article.IdArticulo,
                'text': f"{article.Descripcion} (ID: {article.IdArticulo})",
                'description': article.Descripcion,
                'price': article.PrecioConIVA,
                'formatted_price': format_price(article.PrecioConIVA),
                'ean': ean_code
            })
        
        return jsonify(results)
    except Exception:
        return jsonify([])

@articles_bp.route('/upload_photo/<int:id_articulo>', methods=['POST'])
@login_required
@admin_required
def upload_photo(id_articulo):
    """Handle photo upload for an article"""
    article = Article.query.get_or_404(id_articulo)
    
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': 'No photo included in request'}), 400
    
    photo = request.files['photo']
    
    if not photo.filename:
        return jsonify({'success': False, 'message': 'Empty photo file'}), 400
    
    # Ensure local Uploads directory exists
    upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Create a unique filename using article ID and timestamp
    filename = f"article_{id_articulo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    
    # Save the file locally
    filepath = os.path.join(upload_dir, filename)
    photo.save(filepath)
    
    # Format the network path to the shared folder
    network_path = f"\\\\192.168.1.26\\DBLogiXUploads\\{filename}"
    
    try:
        # Update LogoPantalla field in database with the network path
        db.session.execute(text("""
            UPDATE dat_articulo 
            SET LogoPantalla = :logo_path,
                Modificado = 1,
                Usuario = :username,
                TimeStamp = NOW()
            WHERE IdArticulo = :id_articulo
        """), {
            "logo_path": network_path,
            "username": current_user.username,
            "id_articulo": id_articulo
        })
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Photo uploaded successfully',
            'path': network_path,
            'filename': filename
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@articles_bp.route('/get_product_photo/<int:id_articulo>')
@login_required
def get_product_photo(id_articulo):
    """Get the product photo path for the article"""
    try:
        result = db.session.execute(text("""
            SELECT LogoPantalla FROM dat_articulo WHERE IdArticulo = :id_articulo
        """), {"id_articulo": id_articulo}).fetchone()
        
        if result and result[0]:
            return jsonify({'success': True, 'path': result[0]})
        else:
            return jsonify({'success': False, 'message': 'No photo found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500 