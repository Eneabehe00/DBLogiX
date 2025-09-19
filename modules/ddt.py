from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, not_, exists
from app.models import db, Client, TicketHeader, TicketLine, Product, Company, AlbaranCabecera, AlbaranLinea, Article, ListinoPrezziHeader, ListinoPrezziRiga
from app.forms import DDTClientSelectForm, DDTTicketFilterForm, DDTCreateForm, DDTDeleteForm, DDTExportForm
from flask_cors import cross_origin
import json
from datetime import datetime, timedelta
import io
import os
from decimal import Decimal
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from sqlalchemy.sql import text
import time
from app.models import SystemConfig
from services.utils import admin_required
from app.config import get_system_config_from_file

ddt_bp = Blueprint('ddt', __name__)

def custom_round(value, digits=2):
    """
    Arrotondamento bancario (round half to even) per evitare errori cumulativi.
    Più preciso dell'arrotondamento per eccesso che causava +1 centesimo.
    """
    if value is None:
        return 0.0
    
    # Usa l'arrotondamento bancario di Python che è più preciso
    # per evitare errori cumulativi negli importi
    return round(float(value), digits)

def round_vat_amount(value):
    """Arrotonda importi IVA con 2 cifre decimali"""
    return custom_round(value, 2)

def round_product_amount(value):
    """Arrotonda importi prodotti con massimo 2 cifre decimali"""
    if value is None:
        return 0.0
    
    # Forza sempre l'arrotondamento a 2 cifre decimali per garantire
    # che la scorporazione dell'IVA non abbia mai più di 2 decimali
    return custom_round(value, 2)

def round_price_without_vat(value):
    """Arrotonda prezzi scorporati dall'IVA con massimo 2 cifre decimali"""
    if value is None:
        return 0.0
    return custom_round(value, 2)

def check_ddt_permissions():
    """Controlla se l'utente corrente può creare DDT basandosi sulla configurazione"""
    # Se l'utente è admin, può sempre creare DDT
    if current_user.is_admin:
        return True
    
    # Altrimenti controlla la configurazione
    try:
        system_config = get_system_config_from_file()
        allow_users_create_ddt = system_config.get('allow_users_create_ddt', False)
        
        # Fallback al database se il file non è disponibile
        if allow_users_create_ddt is None:
            allow_users_create_ddt = SystemConfig.get_config('allow_users_create_ddt', False)
        
        return allow_users_create_ddt
    except Exception as e:
        current_app.logger.error(f"Errore nel controllo permessi DDT: {str(e)}")
        # In caso di errore, permetti solo agli admin (comportamento sicuro)
        return False

def calculate_ticket_price_with_vat(cliente_id, articolo_id, precio_originale, id_iva):
    """
    Calcola il prezzo finale con IVA per un ticket, applicando il listino del cliente se disponibile.
    CORREZIONE ARROTONDAMENTO: Evita arrotondamenti intermedi per prevenire errori cumulativi.
    
    Args:
        cliente_id (int): ID del cliente
        articolo_id (int): ID dell'articolo
        precio_originale (float): Prezzo originale del ticket (GIÀ CON IVA)
        id_iva (int): ID dell'aliquota IVA
        
    Returns:
        tuple: (precio_con_iva, precio_senza_iva, vat_rate)
    """
    # Calcola l'aliquota IVA
    vat_rate = 0.04  # Default 4%
    if id_iva == 4:
        vat_rate = 0.00  # 0% - Esente IVA
    elif id_iva == 1:
        vat_rate = 0.04  # 4%
    elif id_iva == 2:
        vat_rate = 0.10  # 10%
    elif id_iva == 3:
        vat_rate = 0.22  # 22%
    
    # Ottieni il prezzo dal listino del cliente
    listino_price = get_cliente_listino_price(cliente_id, articolo_id, precio_originale)
    
    cliente = Client.query.get(cliente_id)
    if not cliente or not cliente.IdListino:
        # CLIENTE SENZA LISTINO: Il prezzo originale è già CON IVA
        precio_con_iva = float(precio_originale)
        # 🔧 CORREZIONE IVA 0%: Per IVA 0%, prezzo senza IVA = prezzo con IVA (nessuna IVA da applicare)
        if vat_rate > 0:
            precio_senza_iva = precio_con_iva / (1 + vat_rate)
        else:
            # IVA 0% - Esente IVA: il prezzo è già il prezzo finale senza IVA
            precio_senza_iva = precio_con_iva
        current_app.logger.info(f"💰 Cliente senza listino - CON IVA: €{precio_con_iva:.2f}, SENZA IVA: €{precio_senza_iva:.6f}, IVA: {vat_rate*100:.0f}%")
    else:
        # 🔧 CORREZIONE DOPPIO CALCOLO IVA: I prezzi del listino sono GIÀ CON IVA
        precio_con_iva = float(listino_price)
        # 🔧 CORREZIONE IVA 0%: Per IVA 0%, prezzo senza IVA = prezzo con IVA
        if vat_rate > 0:
            precio_senza_iva = precio_con_iva / (1 + vat_rate)
        else:
            # IVA 0% - Esente IVA: il prezzo è già il prezzo finale senza IVA
            precio_senza_iva = precio_con_iva
        current_app.logger.info(f"💰 Cliente con listino - CON IVA: €{precio_con_iva:.2f}, SENZA IVA: €{precio_senza_iva:.6f}, IVA: {vat_rate*100:.0f}%")
    
    return precio_con_iva, precio_senza_iva, vat_rate

def get_cliente_listino_price(cliente_id, articolo_id, default_price):
    """
    Ottiene il prezzo di un articolo dal listino associato al cliente.
    Se il cliente non ha un listino o l'articolo non è nel listino, usa il prezzo di default.
    
    Args:
        cliente_id (int): ID del cliente
        articolo_id (int): ID dell'articolo
        default_price (float): Prezzo di default da usare se non c'è listino
        
    Returns:
        float: Prezzo dell'articolo (da listino o default) - CON IVA
    """
    try:
        # Recupera il cliente
        cliente = Client.query.get(cliente_id)
        if not cliente or not cliente.IdListino:
            current_app.logger.info(f"🏷️  Cliente {cliente_id} senza listino associato, uso prezzo standard: €{default_price:.3f}")
            return default_price
        
        # Cerca l'articolo nel listino del cliente
        riga_listino = ListinoPrezziRiga.query.filter_by(
            IdListino=cliente.IdListino,
            IdArticolo=articolo_id
        ).first()
        
        if riga_listino:
            prezzo_listino = float(riga_listino.Prezzo)
            current_app.logger.info(f"🏷️  Articolo {articolo_id} trovato nel listino {cliente.IdListino}: €{prezzo_listino:.3f} (era €{default_price:.3f})")
            return prezzo_listino
        else:
            current_app.logger.info(f"🏷️  Articolo {articolo_id} non trovato nel listino {cliente.IdListino}, uso prezzo standard: €{default_price:.3f}")
            return default_price
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore recupero prezzo listino per cliente {cliente_id}, articolo {articolo_id}: {str(e)}")
        current_app.logger.info(f"🏷️  Fallback al prezzo standard: €{default_price:.3f}")
        return default_price

@ddt_bp.route('/')
@login_required
def index():
    """Display a list of all DDTs with enhanced search functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 15  # Aumentato da 10 a 15 per visualizzare più elementi
    search_query = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort_by', 'id', type=str).strip()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip()

    # Validate sort parameters
    valid_sort_fields = {
        'id': AlbaranCabecera.NumAlbaran,
        'cliente_nome': AlbaranCabecera.NombreCliente,
        'date': AlbaranCabecera.Fecha,
        'totale': AlbaranCabecera.ImporteTotal,
        'num_linee': AlbaranCabecera.NumLineas,
        'created_by': AlbaranCabecera.Usuario
    }

    if sort_by not in valid_sort_fields:
        sort_by = 'date'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    # Base query
    ddts_query = AlbaranCabecera.query

    # Apply search filter if provided
    if search_query:
        try:
            # Try to convert search to integer for ID search
            search_id = int(search_query)
            ddts_query = ddts_query.filter(
                db.or_(
                    AlbaranCabecera.IdAlbaran == search_id,
                    AlbaranCabecera.NombreCliente.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            # Search only by client name if not a valid ID
            ddts_query = ddts_query.filter(
                AlbaranCabecera.NombreCliente.ilike(f'%{search_query}%')
            )

    # Apply dynamic sorting
    sort_column = valid_sort_fields[sort_by]
    if sort_order == 'desc':
        ddts = ddts_query.order_by(sort_column.desc()).all()
    else:
        ddts = ddts_query.order_by(sort_column.asc()).all()
    
    # Preparare i dati per la visualizzazione
    combined_ddts = []
    
    for ddt in ddts:
        combined_ddts.append({
            'id': ddt.NumAlbaran,  # Usa NumAlbaran per l'identificazione visuale
            'internal_id': ddt.IdAlbaran,  # Mantieni IdAlbaran per i link interni
            'date': ddt.Fecha,
            'formatted_date': ddt.Fecha.strftime('%d/%m/%Y %H:%M') if ddt.Fecha else 'N/A',
            'cliente_id': ddt.IdCliente,
            'cliente_nome': ddt.NombreCliente,
            'totale': float(ddt.ImporteTotal) if ddt.ImporteTotal else 0,
            'num_linee': ddt.NumLineas,
            'model_type': 'albaran',
            'created_by': ddt.Usuario  # Add the Usuario field to identify the creator
        })
    
    # Paginazione manuale
    start = (page - 1) * per_page
    end = start + per_page
    paginated_ddts = combined_ddts[start:end]
    
    # Crea un oggetto paginazione manuale per il template
    class ManualPagination:
        def __init__(self, items, total, page, per_page):
            self.items = items
            self.total = total
            self.page = page
            self.per_page = per_page
        
        @property
        def pages(self):
            return max(1, (self.total + self.per_page - 1) // self.per_page)
        
        @property
        def has_prev(self):
            return self.page > 1
        
        @property
        def has_next(self):
            return self.page < self.pages
        
        @property
        def prev_num(self):
            return self.page - 1 if self.has_prev else None
        
        @property
        def next_num(self):
            return self.page + 1 if self.has_next else None
        
        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num
    
    pagination = ManualPagination(
        items=paginated_ddts,
        total=len(combined_ddts),
        page=page,
        per_page=per_page
    )
    
    return render_template('ddt/index.html', ddts=pagination, search_query=search_query, sort_by=sort_by, sort_order=sort_order)

@ddt_bp.route('/api/sort', methods=['GET'])
@login_required
def api_sort_ddts():
    """API endpoint for sorting DDTs without page reload"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 15, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    sort_by = request.args.get('sort_by', 'id', type=str).strip()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip()

    # Validate sort parameters
    valid_sort_fields = {
        'id': AlbaranCabecera.NumAlbaran,
        'cliente_nome': AlbaranCabecera.NombreCliente,
        'date': AlbaranCabecera.Fecha,
        'totale': AlbaranCabecera.ImporteTotal,
        'num_linee': AlbaranCabecera.NumLineas,
        'created_by': AlbaranCabecera.Usuario
    }

    if sort_by not in valid_sort_fields:
        sort_by = 'date'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'

    # Base query
    ddts_query = AlbaranCabecera.query

    # Apply search filter if provided
    if search_query:
        try:
            # Try to convert search to integer for ID search
            search_id = int(search_query)
            ddts_query = ddts_query.filter(
                db.or_(
                    AlbaranCabecera.IdAlbaran == search_id,
                    AlbaranCabecera.NombreCliente.ilike(f'%{search_query}%')
                )
            )
        except ValueError:
            # Search only by client name if not a valid ID
            ddts_query = ddts_query.filter(
                AlbaranCabecera.NombreCliente.ilike(f'%{search_query}%')
            )

    # Apply dynamic sorting
    sort_column = valid_sort_fields[sort_by]
    if sort_order == 'desc':
        ddts = ddts_query.order_by(sort_column.desc()).all()
    else:
        ddts = ddts_query.order_by(sort_column.asc()).all()

    # Preparare i dati per la risposta JSON
    combined_ddts = []

    for ddt in ddts:
        combined_ddts.append({
            'id': ddt.NumAlbaran,  # Usa NumAlbaran per l'identificazione visuale
            'internal_id': ddt.IdAlbaran,  # Mantieni IdAlbaran per i link interni
            'date': ddt.Fecha.isoformat() if ddt.Fecha else None,
            'formatted_date': ddt.Fecha.strftime('%d/%m/%Y %H:%M') if ddt.Fecha else 'N/A',
            'cliente_id': ddt.IdCliente,
            'cliente_nome': ddt.NombreCliente,
            'totale': float(ddt.ImporteTotal) if ddt.ImporteTotal else 0,
            'num_linee': ddt.NumLineas,
            'model_type': 'albaran',
            'created_by': ddt.Usuario  # Add the Usuario field to identify the creator
        })

    # Paginazione manuale
    start = (page - 1) * per_page
    end = start + per_page
    paginated_ddts = combined_ddts[start:end]

    # Calcola informazioni sulla paginazione
    total_items = len(combined_ddts)
    total_pages = max(1, (total_items + per_page - 1) // per_page)

    return jsonify({
        'success': True,
        'ddts': paginated_ddts,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_items,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
        },
        'sort_by': sort_by,
        'sort_order': sort_order
    })

@ddt_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    """Step 1: Select a client for the new DDT"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        flash('Non hai i permessi per creare DDT. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('index'))
    
    form = DDTClientSelectForm()
    
    if form.validate_on_submit():
        cliente_id = form.cliente_id.data
        # Verify client exists
        client = Client.query.get(cliente_id)
        if not client:
            flash('Cliente non trovato.', 'danger')
            return redirect(url_for('ddt.new'))
        
        # Redirect to the ticket selection page
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))
    
    return render_template('ddt/select_client.html', form=form)

@ddt_bp.route('/select_tickets/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def select_tickets(cliente_id):
    """Step 2: Select tickets to include in the DDT - organized by products"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        flash('Non hai i permessi per creare DDT. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('index'))
    
    cliente = Client.query.get_or_404(cliente_id)
    form = DDTTicketFilterForm()
    
    # Get current empresa ID - use first available empresa for demo
    # In a real app, you would get this from the user's session/profile
    empresa = Company.query.first()
    if not empresa:
        flash('Nessuna azienda configurata nel sistema.', 'danger')
        return redirect(url_for('ddt.index'))
    
    id_empresa = empresa.IdEmpresa
    
    # 🚀 QUERY OTTIMIZZATA: Una sola query per recuperare tutti i dati
    # Invece di N+1 query, eseguiamo una sola query con JOIN
    # Include anche i prezzi di listino se il cliente ne ha uno associato

    # 🎯 GESTIONE PREZZI DI LISTINO PER CLIENTE
    # Se il cliente ha un listino associato, utilizziamo i prezzi specifici del listino
    # altrimenti utilizziamo i prezzi standard dal ticket
    prezzo_field = "tl.Precio"  # Prezzo di default dal ticket
    join_listino = ""

    if cliente.IdListino:
        # Il cliente ha un listino personalizzato, usa i prezzi dal listino
        prezzo_field = "COALESCE(lp.Prezzo, tl.Precio)"  # Usa prezzo listino se disponibile, altrimenti prezzo ticket
        join_listino = f"""
            LEFT JOIN price_list_line lp ON lp.IdArticolo = tl.IdArticulo
                AND lp.IdListino = {cliente.IdListino}
        """
        current_app.logger.info(f"💰 Cliente {cliente.IdCliente} ({cliente.Nombre}) usa listino {cliente.IdListino}")
    else:
        current_app.logger.info(f"💰 Cliente {cliente.IdCliente} ({cliente.Nombre}) usa prezzi standard")

    optimized_query = f"""
        SELECT
            tc.IdTicket,
            tc.NumTicket,
            tc.Fecha,
            tc.IdEmpresa,
            tc.IdTienda,
            tc.IdBalanzaMaestra,
            tc.IdBalanzaEsclava,
            tc.TipoVenta,
            tc.CodigoBarras,
            tl.IdLineaTicket,
            tl.IdArticulo,
            tl.Descripcion,
            tl.Peso,
            tl.comportamiento,
            tl.FechaCaducidad,
            {prezzo_field} as Precio,
            p.IdFamilia,
            p.IdSubFamilia,
            p.IdIva,
            CASE
                WHEN p.IdIva = 1 THEN 4
                WHEN p.IdIva = 2 THEN 10
                WHEN p.IdIva = 3 THEN 22
                WHEN p.IdIva = 4 THEN 0
                ELSE 4
            END as PorcentajeIva
        FROM dat_ticket_cabecera tc
        INNER JOIN dat_ticket_linea tl ON tc.IdTicket = tl.IdTicket
        LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
        {join_listino}
        WHERE tc.Enviado = 0
        ORDER BY tc.Fecha DESC, tl.IdArticulo
    """

    # Debug: Log della query generata per verificare che sia corretta
    current_app.logger.debug(f"🔍 Query generata per cliente {cliente.IdCliente}: {optimized_query[:200]}...")

    # Esegui la query ottimizzata
    result = db.session.execute(text(optimized_query))
    
    # Organize tickets by products - raggruppa i dati per IdArticulo
    products_map = {}
    
    for row in result:
        # Estrai i dati dalla riga
        id_ticket = row[0]
        num_ticket = row[1]
        fecha = row[2]
        id_empresa = row[3]
        id_tienda = row[4] or 1
        id_balanza_maestra = row[5] or 1
        id_balanza_esclava = row[6] or -1
        tipo_venta = row[7] or 2
        codigo_barras = row[8] or ''
        id_linea_ticket = row[9]  # IMPORTANTE: ID reale della linea
        id_articulo = row[10]
        descripcion = row[11]
        peso = float(row[12] or 0)
        comportamiento = row[13] or 0
        fecha_caducidad = row[14]
        precio = float(row[15] or 0)
        id_familia = row[16]
        id_subfamilia = row[17]
        id_iva = row[18]  # ID dell'aliquota IVA
        porcentaje_iva = row[19]  # Percentuale IVA calcolata
        
        # Group by product (IdArticulo)
        if id_articulo not in products_map:
            products_map[id_articulo] = {
                'id_articulo': id_articulo,
                'descripcion': descripcion,
                'comportamiento': comportamiento,
                'precio': precio,
                'id_familia': id_familia,
                'id_subfamilia': id_subfamilia,
                'id_iva': id_iva,
                'porcentaje_iva': porcentaje_iva,
                'tickets': [],
                'total_weight': 0,
                'total_value': 0
            }
        
        # Add ticket info to product with enhanced data for filtering
        products_map[id_articulo]['tickets'].append({
            'id_ticket': id_ticket,
            'num_ticket': num_ticket,
            'fecha': fecha.strftime('%d/%m/%Y %H:%M') if fecha else '',
            'fecha_raw': fecha.isoformat() if fecha else '',  # ISO format for JavaScript Date parsing
            'peso': peso,
            'fecha_caducidad': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None,
            'fecha_caducidad_raw': fecha_caducidad.isoformat() if fecha_caducidad else None,  # ISO format for filtering
            'importe': peso * precio,
            'precio': precio,
            'comportamiento': comportamiento,
            'id_iva': id_iva,
            'porcentaje_iva': porcentaje_iva,
            'id_empresa': id_empresa,
            'id_tienda': id_tienda,
            'id_balanza_maestra': id_balanza_maestra,
            'id_balanza_esclava': id_balanza_esclava,
            'tipo_venta': tipo_venta,
            'codigo_barras': codigo_barras
        })
        
        # Update totals per prodotto
        products_map[id_articulo]['total_weight'] += peso
        products_map[id_articulo]['total_value'] += peso * precio
    
    # Convert to list and sort by product name
    products = list(products_map.values())
    products.sort(key=lambda x: x['descripcion'])
    
    # Also create the create form for the hidden form CSRF token
    create_form = DDTCreateForm()

    # Informazioni sul listino utilizzato
    listino_info = None
    if cliente.IdListino and cliente.listino:
        listino_info = {
            'id': cliente.listino.IdListino,
            'nome': cliente.listino.NomeListino,
            'descrizione': cliente.listino.Descrizione
        }

    return render_template('ddt/select_tickets.html',
                          cliente=cliente,
                          products=products,
                          form=form,
                          create_form=create_form,
                          id_empresa=id_empresa,
                          listino_info=listino_info)

@ddt_bp.route('/preview', methods=['GET', 'POST'])
@login_required
def preview():
    """Step 2.5: Preview DDT before final creation with ability to modify tickets"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        flash('Non hai i permessi per creare DDT. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('index'))
    
    # Handle GET requests (redirect to localStorage recovery page)
    if request.method == 'GET':
        # If GET request and we have query parameters, check for localStorage fallback
        cliente_id = request.args.get('cliente_id')
        if cliente_id:
            # Redirect to localStorage recovery page
            return render_template('ddt/localStorage_recovery.html', cliente_id=cliente_id)
        else:
            flash('Accesso non valido alla preview DDT', 'danger')
            return redirect(url_for('ddt.new'))
    
    # Get form data for POST requests
    cliente_id = request.form.get('cliente_id')
    id_empresa = request.form.get('id_empresa', 1)
    tickets_data = request.form.get('tickets') or request.form.get('selected_tickets')
    
    # Parametri aggiuntivi per gestire i task e warehouse
    from_task = request.form.get('from_task') == 'true'
    from_warehouse = request.form.get('from_warehouse') == 'true'
    task_id = request.form.get('task_id')
    
    if not cliente_id:
        flash('ID cliente mancante', 'danger')
        return redirect(url_for('ddt.new'))
    
    if not tickets_data:
        # If no tickets data in POST, try localStorage recovery
        flash('Nessun ticket selezionato. Provo a recuperare dal localStorage...', 'warning')
        return redirect(url_for('ddt.preview', cliente_id=cliente_id))
    
    # Get client and company info
    cliente = Client.query.get_or_404(int(cliente_id))
    empresa = Company.query.get_or_404(int(id_empresa))
    
    # Parse selected tickets
    try:
        selected_tickets = json.loads(tickets_data)
    except json.JSONDecodeError:
        flash('Formato dati ticket non valido', 'danger')
        if from_task and task_id:
            return redirect(url_for('tasks.view_task', task_id=task_id))
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))
    
    # Get detailed ticket information
    preview_data = []
    
    # Debug: Log selected tickets
    current_app.logger.info(f"🔍 DEBUG: Elaborazione {len(selected_tickets)} ticket selezionati")
    
    for ticket_info in selected_tickets:
        # Force session refresh to avoid caching issues
        db.session.expire_all()
        
        ticket = TicketHeader.query.filter_by(
            IdTicket=ticket_info['id_ticket'],
            IdEmpresa=ticket_info['id_empresa']
        ).first()
        
        if ticket:
            # DEBUG: Log ticket info
            current_app.logger.info(f"🎫 DEBUG: Processando Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket})")
            
            # Get ticket lines with both ORM and raw SQL for comparison
            lines = TicketLine.query.filter_by(
                IdTicket=ticket.IdTicket
            ).all()
            
            # More robust query using explicit join to ensure data integrity
            verified_query = db.session.query(TicketLine).join(
                TicketHeader, TicketLine.IdTicket == TicketHeader.IdTicket
            ).filter(
                TicketHeader.IdTicket == ticket.IdTicket,
                TicketLine.IdTicket == ticket.IdTicket
            ).all()
            
            current_app.logger.info(f"🔍 DEBUG: Standard query: {len(lines)} lines, Join query: {len(verified_query)} lines")
            
            # Use the join query as it's more reliable
            lines = verified_query
            
            # Alternative query using raw SQL to avoid potential ORM caching issues
            raw_query = """
            SELECT IdLineaTicket, IdTicket, IdArticulo, Descripcion, Peso, Precio, FechaCaducidad, comportamiento
            FROM dat_ticket_linea 
            WHERE IdTicket = :ticket_id
            ORDER BY IdLineaTicket
            """
            raw_result = db.session.execute(text(raw_query), {'ticket_id': ticket.IdTicket})
            raw_lines = []
            for row in raw_result:
                raw_lines.append({
                    'IdLineaTicket': row[0],
                    'IdTicket': row[1],
                    'IdArticulo': row[2],
                    'Descripcion': row[3],
                    'Peso': row[4],
                    'Precio': row[5],
                    'FechaCaducidad': row[6],
                    'comportamiento': row[7]
                })
            
            # Compare ORM vs raw results
            current_app.logger.info(f"🔍 DEBUG: ORM query returned {len(lines)} lines, Raw SQL returned {len(raw_lines)} lines")
            if len(lines) != len(raw_lines):
                current_app.logger.error(f"🚨 DISCREPANZA: ORM e SQL raw hanno risultati diversi per ticket {ticket.IdTicket}")
                # Use raw SQL results as they are more reliable
                lines = []
                for raw_line in raw_lines:
                    # Create a mock TicketLine object for compatibility
                    mock_line = type('MockTicketLine', (), raw_line)()
                    lines.append(mock_line)
            
            # DEBUG: Log lines found
            current_app.logger.info(f"📋 DEBUG: Trovate {len(lines)} linee per ticket {ticket.IdTicket}")
            
            # Additional verification: ensure all lines actually belong to this ticket
            verified_lines = []
            for line in lines:
                if line.IdTicket == ticket.IdTicket:
                    verified_lines.append(line)
                else:
                    current_app.logger.error(f"🚨 ERRORE: Linea {line.IdLineaTicket} ha IdTicket={line.IdTicket} ma dovrebbe essere {ticket.IdTicket}")
            
            current_app.logger.info(f"✅ DEBUG: Verificate {len(verified_lines)} linee valide per ticket {ticket.IdTicket}")
            
            ticket_lines_data = []
            
            for line in verified_lines:
                # DEBUG: Log each line
                current_app.logger.info(f"   🔸 Linea {line.IdLineaTicket}: IdTicket={line.IdTicket}, IdArticulo={line.IdArticulo}, Desc={line.Descripcion}")
                
                # Additional verification: ensure line belongs to this ticket
                if line.IdTicket != ticket.IdTicket:
                    current_app.logger.error(f"🚨 ERRORE CRITICO: Linea {line.IdLineaTicket} non appartiene al ticket {ticket.IdTicket}")
                    continue
                
                # Get product info for reference (still needed for other data)
                product = Product.query.get(line.IdArticulo)

                # ✅ CORREZIONE: Leggi IVA direttamente dalla linea del ticket (dat_ticket_linea)
                # Usa i valori IdIVA e PorcentajeIVA dalla tabella dat_ticket_linea invece di product.IdIva
                vat_rate = 0
                id_iva_ticket = getattr(line, 'IdIVA', None)
                porcentaje_iva_ticket = getattr(line, 'PorcentajeIVA', None)

                if id_iva_ticket is not None and porcentaje_iva_ticket is not None:
                    # Usa i valori diretti dalla linea del ticket
                    vat_rate = float(porcentaje_iva_ticket) / 100
                    current_app.logger.info(f"✅ IVA dal ticket: IdIVA={id_iva_ticket}, PorcentajeIVA={porcentaje_iva_ticket}%, vat_rate={vat_rate}")
                else:
                    # Fallback: usa il prodotto se i valori del ticket non sono disponibili
                    current_app.logger.warning(f"⚠️ IVA ticket non disponibile per linea {line.IdLineaTicket}, uso fallback dal prodotto")
                    if product and product.IdIva:
                        if product.IdIva == 1:
                            vat_rate = 0.04  # 4%
                        elif product.IdIva == 2:
                            vat_rate = 0.10  # 10%
                        elif product.IdIva == 3:
                            vat_rate = 0.22  # 22%
                        elif product.IdIva == 4:
                            vat_rate = 0.00  # 0% - Esente IVA
                
                # Calculate prices correctly - use listino price if available
                ticket_price = float(getattr(line, 'Precio', 0) or 0)
                
                # 🔧 CORREZIONE DOPPIO CALCOLO IVA: Usa la funzione esistente che gestisce correttamente i prezzi
                # ✅ CORREZIONE: Passa id_iva_ticket invece di product.IdIva
                line_price_with_vat, line_price_without_vat, vat_rate = calculate_ticket_price_with_vat(
                    cliente.IdCliente, line.IdArticulo, ticket_price, id_iva_ticket if id_iva_ticket is not None else (product.IdIva if product else 1)
                )
                
                # Calcola informazioni sulla differenza prezzo per il logging
                listino_price = get_cliente_listino_price(cliente.IdCliente, line.IdArticulo, ticket_price)
                price_difference = listino_price - ticket_price if listino_price != ticket_price else 0
                has_custom_price = listino_price != ticket_price
                peso_value = float(line.Peso or 0)
                
                # Calculate amount based on product behavior
                comportamiento = getattr(line, 'comportamiento', 0)
                if comportamiento == 1:  # Weight-based product (kg)
                    line_amount = peso_value * line_price_without_vat
                    line_amount_with_vat = peso_value * line_price_with_vat  # 🔧 AGGIUNTO: Calcolo con IVA
                else:  # Unit-based product (pieces)
                    line_amount = peso_value * line_price_without_vat
                    line_amount_with_vat = peso_value * line_price_with_vat  # 🔧 AGGIUNTO: Calcolo con IVA
                
                # Apply rounding to line amounts
                line_amount = round_product_amount(line_amount)
                line_amount_with_vat = round_product_amount(line_amount_with_vat)  # 🔧 AGGIUNTO: Arrotondamento
                
                ticket_lines_data.append({
                    'id_linea_ticket': line.IdLineaTicket,  # Added for better tracking
                    'id_ticket': line.IdTicket,  # Added for verification
                    'id_articulo': line.IdArticulo,
                    'descripcion': line.Descripcion,
                    'peso': line.Peso,
                    'precio': line_price_with_vat,  # MODIFICATO: Mostra prezzo CON IVA nella preview
                    'precio_senza_iva': line_price_without_vat,  # Prezzo senza IVA per calcoli interni
                    'precio_con_iva': line_price_with_vat,  # Keep original price for reference (compatibilità)
                    'precio_standard': ticket_price,  # Prezzo standard del ticket originale
                    'precio_listino': listino_price,  # Prezzo applicato dal listino
                    'has_custom_price': has_custom_price,  # Se il prezzo è diverso da quello standard
                    'price_difference': price_difference,  # Differenza di prezzo
                    'importe': line_amount,
                    'importe_con_iva': line_amount_with_vat,  # 🔧 AGGIUNTO: Importo con IVA per la barra verde
                    'fecha_caducidad': line.FechaCaducidad,
                    'comportamiento': comportamiento,
                    'id_iva': id_iva_ticket if id_iva_ticket is not None else (product.IdIva if product else 1),  # ✅ CORRETTO: Usa ID IVA del ticket
                    'vat_rate': vat_rate,
                    'porcentaje_iva': porcentaje_iva_ticket if porcentaje_iva_ticket is not None else int(vat_rate * 100),  # ✅ CORRETTO: Usa percentuale IVA del ticket
                    'texto_lote': line.TextoLote  # Campo lotto del prodotto
                })
            
            # DEBUG: Final ticket data
            current_app.logger.info(f"🎯 DEBUG: Ticket {ticket.IdTicket} completato con {len(ticket_lines_data)} linee valide")
            
            # Add detailed summary for this ticket
            line_ids = [line_data['id_linea_ticket'] for line_data in ticket_lines_data]
            article_ids = [line_data['id_articulo'] for line_data in ticket_lines_data]
            current_app.logger.info(f"📝 DEBUG: Ticket {ticket.IdTicket} - Linee: {line_ids}")
            current_app.logger.info(f"📝 DEBUG: Ticket {ticket.IdTicket} - Articoli: {article_ids}")
            
            preview_data.append({
                'ticket': {
                    'IdTicket': ticket.IdTicket,
                    'NumTicket': ticket.NumTicket,
                    'Fecha': ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else None,
                    'IdEmpresa': ticket.IdEmpresa,
                    'IdTienda': ticket.IdTienda,
                    'IdBalanzaMaestra': ticket.IdBalanzaMaestra,
                    'IdBalanzaEsclava': ticket.IdBalanzaEsclava,
                    'TipoVenta': ticket.TipoVenta
                },
                'ticket_info': ticket_info,
                'lines': ticket_lines_data,
                'ticket_total': 0
            })
            
        else:
            current_app.logger.warning(f"⚠️  Ticket non trovato: ID={ticket_info['id_ticket']}, Empresa={ticket_info['id_empresa']}")
    
    # DEBUG: Final summary
    current_app.logger.info(f"📊 DEBUG: Elaborazione completata - {len(preview_data)} ticket nel preview")
    
    # Get all available tickets for adding more
    available_tickets = TicketHeader.query.filter(
        TicketHeader.Enviado == 0,
        ~TicketHeader.IdTicket.in_([t['id_ticket'] for t in selected_tickets])
    ).order_by(TicketHeader.Fecha.desc()).limit(50).all()
    
    # Ottieni informazioni listino del cliente se il modulo è abilitato
    listino_info = None
    listini_enabled = False
    has_dedicated_listino = False
    
    from app.modules_config import modules_manager
    listini_enabled = modules_manager.is_module_enabled('listini')
    
    if listini_enabled and cliente.IdListino:
        from app.models import ListinoPrezziHeader
        listino = ListinoPrezziHeader.query.get(cliente.IdListino)
        if listino:
            listino_info = {
                'id': listino.IdListino,
                'nome': listino.NomeListino,
                'descrizione': listino.Descrizione,
                'has_custom_prices': True
            }
            has_dedicated_listino = True
            current_app.logger.info(f"🏷️  Cliente {cliente.Nombre} ha listino personalizzato: {listino.NomeListino}")
        else:
            current_app.logger.warning(f"⚠️  Cliente {cliente.Nombre} ha IdListino={cliente.IdListino} ma listino non trovato")
    
    # Create form for final DDT creation
    create_form = DDTCreateForm()
    
    return render_template('ddt/preview.html',
                          cliente=cliente,
                          empresa=empresa,
                          preview_data=preview_data,
                          available_tickets=available_tickets,
                          create_form=create_form,
                          selected_tickets_json=tickets_data,
                          from_task=from_task,
                          from_warehouse=from_warehouse,
                          task_id=task_id,
                          listino_info=listino_info,
                          listini_enabled=listini_enabled,
                          has_dedicated_listino=has_dedicated_listino)

@ddt_bp.route('/api/update_ticket_line', methods=['POST'])
@login_required
def api_update_ticket_line():
    """API per aggiornare una linea di ticket nel database"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'Dati non forniti'}), 400
        
        # Validazione campi obbligatori
        required_fields = ['ticket_id', 'line_id', 'descripcion', 'peso', 'precio']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo {field} obbligatorio'}), 400
        
        ticket_id = int(data['ticket_id'])
        line_id = int(data['line_id'])
        
        # Trova la linea del ticket
        ticket_line = TicketLine.query.filter_by(
            IdTicket=ticket_id,
            IdLineaTicket=line_id
        ).first()
        
        if not ticket_line:
            return jsonify({'success': False, 'error': 'Linea del ticket non trovata'}), 404
        
        # Aggiorna i campi
        ticket_line.IdArticulo = int(data.get('id_articulo', ticket_line.IdArticulo))
        ticket_line.Descripcion = data['descripcion']
        ticket_line.Peso = float(data['peso'])
        ticket_line.Precio = float(data['precio'])
        ticket_line.comportamiento = int(data.get('comportamiento', 0))
        ticket_line.TextoLote = data.get('texto_lote', '')
        
        # Gestione IVA - aggiorna il prodotto associato se necessario
        if 'iva' in data and ticket_line.product:
            iva_value = int(data['iva'])
            # Converti il valore IVA in IdIva
            if iva_value == 4:
                ticket_line.product.IdIva = 1
            elif iva_value == 10:
                ticket_line.product.IdIva = 2
            elif iva_value == 22:
                ticket_line.product.IdIva = 3
            elif iva_value == 0:
                ticket_line.product.IdIva = 4
            
            current_app.logger.info(f"📊 IVA aggiornata per prodotto {ticket_line.IdArticulo}: {iva_value}% (IdIva: {ticket_line.product.IdIva})")
        
        # Gestione data di scadenza
        if data.get('fecha_caducidad'):
            try:
                from datetime import datetime
                fecha_caducidad = datetime.strptime(data['fecha_caducidad'], '%Y-%m-%d')
                ticket_line.FechaCaducidad = fecha_caducidad
            except ValueError:
                return jsonify({'success': False, 'error': 'Formato data non valido (YYYY-MM-DD)'}), 400
        else:
            ticket_line.FechaCaducidad = None
        
        # Ricalcola l'importo se non fornito
        if 'importe' in data and data['importe']:
            # Se l'importo è fornito esplicitamente, usalo
            importe = float(data['importe'])
        else:
            # Altrimenti calcolalo da peso * prezzo
            importe = float(data['peso']) * float(data['precio'])
        
        # Salva nel database
        db.session.commit()
        
        # Calcola il vat_rate attuale per la risposta
        vat_rate = 0
        if ticket_line.product and ticket_line.product.IdIva:
            if ticket_line.product.IdIva == 1:
                vat_rate = 0.04  # 4%
            elif ticket_line.product.IdIva == 2:
                vat_rate = 0.10  # 10%
            elif ticket_line.product.IdIva == 3:
                vat_rate = 0.22  # 22%
            elif ticket_line.product.IdIva == 4:
                vat_rate = 0     # 0%
        
        # Prepara i dati aggiornati per la risposta
        updated_line = {
            'id_linea_ticket': ticket_line.IdLineaTicket,
            'id_ticket': ticket_line.IdTicket,
            'id_articulo': ticket_line.IdArticulo,
            'descripcion': ticket_line.Descripcion,
            'peso': float(ticket_line.Peso) if ticket_line.Peso else 0,
            'precio': float(ticket_line.Precio) if ticket_line.Precio else 0,
            'importe': importe,
            'comportamiento': ticket_line.comportamiento,
            'fecha_caducidad': ticket_line.FechaCaducidad.isoformat() if ticket_line.FechaCaducidad else None,
            'texto_lote': ticket_line.TextoLote,
            'vat_rate': vat_rate
        }
        
        current_app.logger.info(f"✅ Linea ticket {line_id} del ticket {ticket_id} aggiornata con successo")
        
        return jsonify({
            'success': True,
            'message': 'Linea aggiornata con successo',
            'updated_line': updated_line
        })
        
    except ValueError as e:
        current_app.logger.error(f"❌ Errore di validazione nell'aggiornamento linea: {str(e)}")
        return jsonify({'success': False, 'error': f'Errore di validazione: {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error(f"❌ Errore nell'aggiornamento linea ticket: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Errore interno: {str(e)}'}), 500


def ensure_custom_product_exists():
    """Assicura che esista un prodotto con ID 999 per i prodotti personalizzati"""
    try:
        # Verifica se esiste già
        product_999 = Product.query.get(999)
        if not product_999:
            # Crea il prodotto di riferimento con ID 999
            product_999 = Product(
                IdArticulo=999,
                Descripcion="Prodotto Personalizzato",
                PrecioConIVA=1.00,
                IdFamilia=1,
                IdSubFamilia=1,
                IdIva=3,  # Default 22%
                TeclaDirecta=0,
                TaraFija=0
            )
            db.session.add(product_999)
            current_app.logger.info("Creato prodotto personalizzato con ID 999")
        
        # Verifica/crea anche il record Article per ID 999
        article_999 = Article.query.get(999)
        if not article_999:
            article_999 = Article(
                IdArticulo=999,
                Descripcion="Prodotto Personalizzato",
                Descripcion1="Prodotto creato manualmente",
                PrecioConIVA=1.00,
                PrecioSinIVA=0.82,  # Prezzo senza IVA al 22%
                IdFamilia=1,
                IdSubFamilia=1,
                IdIva=3,  # 22%
                IdTipo=1,  # Pesato
                IdDepartamento=1,
                IdSeccion=1,
                TeclaDirecta=0,
                TaraFija=0,
                Favorito=True,
                EnVenta=True,
                IncluirGestionStock=False,
                IdClase=1,
                IdEmpresa=1,
                Usuario="DBLogiX",
                Modificado=True,
                Operacion="A",
                Marca=1
            )
            db.session.add(article_999)
            current_app.logger.info("Creato articolo personalizzato con ID 999")
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nella creazione del prodotto personalizzato: {str(e)}")

@ddt_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Step 3: Create the DDT with the selected client and tickets"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        flash('Non hai i permessi per creare DDT. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('index'))
    
    # Get form data
    cliente_id = request.form.get('cliente_id')
    id_empresa = request.form.get('id_empresa', 1)
    tickets_data = request.form.get('tickets')
    manual_tickets_data = request.form.get('manual_tickets')  # Ticket manuali dal localStorage
    ticket_discounts_data = request.form.get('ticket_discounts')  # Sconti dei ticket dal localStorage
    ticket_modifications_data = request.form.get('ticket_modifications')  # 🔥 NUOVO: Modifiche prezzi dal localStorage
    note = request.form.get('note')
    creation_date_str = request.form.get('creation_date')  # Data creazione personalizzata

    # DEBUG: Log del parametro creation_date ricevuto
    current_app.logger.info(f"🔍 DEBUG CREATION DATE: creation_date_str = '{creation_date_str}'")
    current_app.logger.info(f"🔍 DEBUG CREATION DATE: request.form keys = {list(request.form.keys())}")
    
    # Gestione task
    from_task = request.form.get('from_task') == 'true'
    from_preview = request.form.get('from_preview') == 'true'
    from_warehouse = request.form.get('from_warehouse') == 'true'
    task_id = request.form.get('task_id')
    
    if not cliente_id:
        flash('Cliente mancante', 'danger')
        return redirect(url_for('ddt.new'))
    
    # Parse ticket data
    try:
        ticket_data = json.loads(tickets_data) if tickets_data else []
        manual_tickets = json.loads(manual_tickets_data) if manual_tickets_data else []
        ticket_discounts = json.loads(ticket_discounts_data) if ticket_discounts_data else {}
        ticket_modifications = json.loads(ticket_modifications_data) if ticket_modifications_data else {}  # 🔥 NUOVO: Modifiche dal localStorage
    except json.JSONDecodeError:
        flash('Formato dati ticket non valido', 'danger')
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))
    
    # Verifica che ci sia almeno un ticket (normale o manuale)
    if not ticket_data and not manual_tickets:
        flash('Nessun ticket selezionato', 'danger')
        current_app.logger.error("❌ ERRORE: Nessun ticket da processare - ticket_data e manual_tickets entrambi vuoti")
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))
    
    # DEBUG: Verifica immediata dei dati ricevuti
    current_app.logger.info(f"📥 DEBUG: Dati ricevuti dal form:")
    current_app.logger.info(f"    tickets_data (raw): {tickets_data}")
    current_app.logger.info(f"    manual_tickets_data (raw): {manual_tickets_data}")
    current_app.logger.info(f"    ticket_discounts_data (raw): {ticket_discounts_data}")
    current_app.logger.info(f"    ticket_modifications_data (raw): {ticket_modifications_data}")
    current_app.logger.info(f"    ticket_data (parsed): {ticket_data}")
    current_app.logger.info(f"    manual_tickets (parsed): {manual_tickets}")
    current_app.logger.info(f"    ticket_discounts (parsed): {ticket_discounts}")
    current_app.logger.info(f"    ticket_modifications (parsed): {ticket_modifications}")
    
    # DEBUG: Test specifico per gli sconti
    if ticket_discounts:
        current_app.logger.info(f"🎯 DEBUG: Sconti specifici trovati:")
        for ticket_id, discount in ticket_discounts.items():
            current_app.logger.info(f"    Ticket {ticket_id}: {discount}% di sconto")
    else:
        current_app.logger.info(f"🎯 DEBUG: Nessuno sconto applicato (ticket_discounts vuoto)")
    
    # DEBUG: Verifica che il dizionario sconti non sia None
    if ticket_discounts is None:
        current_app.logger.error(f"❌ ERRORE: ticket_discounts è None - imposto dizionario vuoto")
        ticket_discounts = {}

    # Get client and company info
    client = Client.query.get_or_404(int(cliente_id))
    empresa = Company.query.get_or_404(int(id_empresa))

    current_app.logger.info(f"🔍 DEBUG: Creazione DDT per cliente {client.Nombre}")
    current_app.logger.info(f"📋 DEBUG: {len(ticket_data)} ticket normali, {len(manual_tickets)} ticket manuali")
    
    # DEBUG: Log dati ticket per verifica
    current_app.logger.info(f"📝 DEBUG: Dati ticket normali: {ticket_data}")
    current_app.logger.info(f"✋ DEBUG: Dati ticket manuali: {manual_tickets}")

    # Assicura che esista il prodotto personalizzato per i ticket manuali
    if manual_tickets:
        ensure_custom_product_exists()

    # 🔥 NUOVO: Funzione helper per determinare il prezzo finale con priorità corretta
    def get_final_ticket_price(ticket_id, line_id, original_product_price, listino_price, current_db_price=None):
        """
        Determina il prezzo finale con la seguente priorità:
        1. localStorage modifications (ddt_ticket_modifications)
        2. Database modifications (se prezzo diverso da originale)
        3. Listino prezzi dedicato cliente
        4. Prezzo originale prodotto
        """
        # 1. 🔥 PRIMA PRIORITÀ: Controlla modifiche nel localStorage
        modification_key = f"{ticket_id}_{line_id}_precio"
        if modification_key in ticket_modifications:
            modification = ticket_modifications[modification_key]
            if modification and 'value' in modification:
                local_storage_price = float(modification['value'])
                current_app.logger.info(f"🔥 [DDT] PRIORITÀ 1 - localStorage: Usando prezzo modificato per articolo {line_id}: €{local_storage_price:.3f}")
                return local_storage_price

        # 2. SECONDA PRIORITÀ: Controlla modifiche nel database
        if current_db_price is not None:
            price_modified_in_db = abs(current_db_price - original_product_price) > 0.001
            if price_modified_in_db:
                current_app.logger.info(f"💰 [DDT] PRIORITÀ 2 - Database: Usando prezzo modificato per articolo {line_id}: €{current_db_price:.3f}")
                return current_db_price

        # 3. TERZA PRIORITÀ: Listino prezzi dedicato cliente
        if listino_price != original_product_price:
            current_app.logger.info(f"🏷️ [DDT] PRIORITÀ 3 - Listino: Usando prezzo del listino per articolo {line_id}: €{listino_price:.3f}")
            return listino_price

        # 4. QUARTA PRIORITÀ: Prezzo originale prodotto
        current_app.logger.info(f"📦 [DDT] PRIORITÀ 4 - Originale: Usando prezzo originale prodotto per articolo {line_id}: €{original_product_price:.3f}")
        return original_product_price

    # Start a transaction
    try:
        # Determina la data di creazione (personalizzata o attuale)
        if creation_date_str:
            try:
                # Parse della data nel formato YYYY-MM-DD
                creation_date = datetime.strptime(creation_date_str, '%Y-%m-%d')
                current_app.logger.info(f"📅 Usando data creazione personalizzata: {creation_date}")
            except ValueError as e:
                current_app.logger.warning(f"⚠️ Formato data non valido '{creation_date_str}', uso data attuale: {e}")
                creation_date = datetime.now()
        else:
            creation_date = datetime.now()
            current_app.logger.info(f"📅 Nessuna data personalizzata fornita, uso data attuale: {creation_date}")

        # Per retrocompatibilità, mantieni la variabile 'now' ma usala solo dove necessario
        now = creation_date

        # DEBUG: Log delle date per troubleshooting
        current_app.logger.info(f"📅 DEBUG DATE SETUP: creation_date = {creation_date}")
        current_app.logger.info(f"📅 DEBUG DATE SETUP: now = {now}")
        current_app.logger.info(f"📅 DEBUG DATE SETUP: datetime.now() = {datetime.now()}")
        # Get the last NumAlbaran and add 1 to make it sequential
        max_num_albaran = db.session.query(db.func.max(AlbaranCabecera.NumAlbaran)).scalar() or 0
        
        # Get the next IdAlbaran to avoid primary key conflicts
        # Imposta IdAlbaran a partire da 999999 e incrementa progressivamente
        max_id_albaran = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 999998
        if max_id_albaran < 999999:
            next_id_albaran = 999999
        else:
            next_id_albaran = max_id_albaran + 1
        
        # Ensure the primary key combination is unique
        existing_ddt = AlbaranCabecera.query.filter_by(
            IdAlbaran=next_id_albaran,
            IdEmpresa=id_empresa,
            IdTienda=1,
            IdBalanzaMaestra=1,
            IdBalanzaEsclava=-1
        ).first()
        
        if existing_ddt:
            # If somehow there's still a conflict, increment again
            next_id_albaran = max_id_albaran + 2
            current_app.logger.warning(f"⚠️ Primary key conflict detected, using IdAlbaran: {next_id_albaran}")
        
        current_app.logger.info(f"🆔 Creating DDT with IdAlbaran: {next_id_albaran}")
        current_app.logger.info(f"📅 DEBUG DDT CREATION: About to create DDT with Fecha = {now}")

        ddt = AlbaranCabecera(
            # Specifica esplicitamente IdAlbaran per evitare conflitti di chiave primaria
            IdAlbaran=next_id_albaran,
            NumAlbaran=max_num_albaran + 1,
            IdEmpresa=id_empresa,
            IdTienda=1,  # Valore predefinito
            IdBalanzaMaestra=1,  # Valore predefinito
            IdBalanzaEsclava=-1,  # Valore predefinito negativo

            # Dati azienda
            NombreEmpresa=empresa.NombreEmpresa,
            CIF_VAT_Empresa=empresa.CIF_VAT or "",
            DireccionEmpresa=empresa.Direccion or "",
            PoblacionEmpresa=empresa.Poblacion or "",
            CPEmpresa=empresa.CodPostal or "",
            TelefonoEmpresa=empresa.Telefono1 or "",
            ProvinciaEmpresa=empresa.Provincia or "",
            NombreTienda="Dibal S.A.",  # Valore predefinito
            NombreBalanzaMaestra="MASTER ETI",  # Valore predefinito
            NombreBalanzaEsclava="",  # Valore predefinito

            # Dati cliente
            IdCliente=cliente_id,
            NombreCliente=client.Nombre,
            DNICliente=client.DNI or "",
            EmailCliente=client.Email or "",
            DireccionCliente=client.Direccion or "",
            PoblacionCliente=client.Poblacion or "",
            ProvinciaCliente=client.Provincia or "",
            PaisCliente=client.Pais or "IT",
            CPCliente=client.CodPostal or "",
            TelefonoCliente=client.Telefono1 or "",
            ObservacionesCliente=client.Observaciones or "None",
            EANCliente=client.EANScanner or "",

            # Informazioni DDT
            Tipo="A",
            IdVendedor=1,  # Valore predefinito
            NombreVendedor="IL CAPO",  # Valore predefinito
            ReferenciaDocumento="",
            ObservacionesDocumento=note or "",
            TipoVenta=2,  # Valore predefinito
            
            # Date
            Fecha=now,
            FechaModificacion=now,
            
            # Totali (saranno calcolati successivamente)
            ImporteLineas=0.0,
            PorcDescuento=None,
            ImporteDescuento=None,
            ImporteRE=0.0,
            ImporteTotalSinRE=0.0,
            ImporteTotalSinIVAConDtoLConDtoTotalConRE=0.0,
            ImporteTotal=0.0,
            ImporteTotalSinIVAConDtoL=0.0,
            ImporteTotalSinIVAConDtoLConDtoTotal=0.0,
            ImporteTotalDelIVAConDtoLConDtoTotal=0.0,
            
            # Altri campi richiesti
            PreseleccionCliente=1,
            Enviado=0,
            NumLineas=len(ticket_data) + len(manual_tickets),
            CodigoBarras="",
            CodBarrasTalonCaja="",
            SerieLTicketErroneo=0,
            Modificado=1,
            Operacion="A",
            Usuario="DBLogiX",
            EstadoTicket="C",
            REAplicado=0,
            Version="4.7.0"  # Valore predefinito come nell'esempio
        )
        db.session.add(ddt)
        db.session.flush()  # Otteniamo l'ID del DDT
        
        current_app.logger.info(f"✅ Created AlbaranCabecera with ID: {ddt.IdAlbaran}")
        
        # Create AlbaranLinea (DDT lines) for each ticket
        line_count = 0
        total_ddt_amount = 0
        total_without_vat = 0
        total_vat = 0

        # PROCESSO TICKET NORMALI
        for ticket in ticket_data:
            current_app.logger.info(f"🎫 DEBUG: Elaborazione ticket normale {ticket['id_ticket']}")
            
            # Get ticket lines from the database
            ticket_header = TicketHeader.query.filter_by(
                IdTicket=ticket['id_ticket']
            ).first()
            
            if not ticket_header:
                current_app.logger.warning(f"⚠️  Ticket header non trovato per ID {ticket['id_ticket']}")
                continue
            
            lines = TicketLine.query.filter_by(
                IdTicket=ticket['id_ticket']
            ).all()
            
            current_app.logger.info(f"📋 DEBUG: Trovate {len(lines)} linee per ticket {ticket['id_ticket']}")
            
            # Create an AlbaranLinea for each product in the ticket
            for ticket_line in lines:
                line_count += 1
                product = Product.query.get(ticket_line.IdArticulo)
                
                if not product:
                    current_app.logger.warning(f"⚠️  Prodotto {ticket_line.IdArticulo} non trovato, riga saltata")
                    continue
                
                # Determine VAT rate
                vat_rate = 0
                if product.IdIva == 1:
                    vat_rate = 0.04  # 4%
                elif product.IdIva == 2:
                    vat_rate = 0.10  # 10%
                elif product.IdIva == 3:
                    vat_rate = 0.22  # 22%
                
                # Calculate prices - CORREZIONE PRIORITÀ: 1) Prezzo modificato dall'utente, 2) Listino cliente, 3) Prezzo originale prodotto
                ticket_price = float(ticket_line.Precio) if ticket_line.Precio is not None else 0.0

                # 🎯 OTTIENI IL PREZZO ORIGINALE DEL PRODOTTO DAL DATABASE DEGLI ARTICOLI
                original_product_price = 0.0
                try:
                    product = Product.query.get(ticket_line.IdArticulo)
                    if product and product.PrecioConIVA:
                        original_product_price = float(product.PrecioConIVA)
                        current_app.logger.info(f"🔍 DEBUG Articolo {ticket_line.IdArticulo} - Prezzo originale prodotto: €{original_product_price:.3f}")
                    else:
                        current_app.logger.warning(f"⚠️ Articolo {ticket_line.IdArticulo} senza prezzo originale, uso prezzo ticket: €{ticket_price:.3f}")
                        original_product_price = ticket_price
                except Exception as e:
                    current_app.logger.error(f"❌ Errore recupero prezzo originale prodotto {ticket_line.IdArticulo}: {str(e)}")
                    original_product_price = ticket_price

                # IMPORTANTE: Controlla se il prezzo è stato modificato dall'utente nella preview
                # Prima ricarica la linea dal database per ottenere eventuali modifiche
                from app.models import TicketLine as TicketLineModel
                current_ticket_line = TicketLineModel.query.filter_by(
                    IdTicket=ticket_line.IdTicket,
                    IdLineaTicket=ticket_line.IdLineaTicket
                ).first()

                # 🎯 CORREZIONE: Usa il prezzo ORIGINALE del prodotto per il listino, non quello del ticket che potrebbe essere modificato
                listino_price = get_cliente_listino_price(cliente_id, ticket_line.IdArticulo, original_product_price)

                # 🔥 NUOVA LOGICA PRIORITÀ PREZZI AGGIORNATA:
                # 1. localStorage modifications (ddt_ticket_modifications)
                # 2. Database modifications (se prezzo diverso da originale)
                # 3. Listino prezzi dedicato cliente
                # 4. Prezzo originale prodotto

                # Prepara i dati per la funzione helper
                current_db_price = None
                if current_ticket_line and current_ticket_line.Precio is not None:
                    current_db_price = float(current_ticket_line.Precio)

                current_app.logger.info(f"🔍 DEBUG Articolo {ticket_line.IdArticulo}:")
                current_app.logger.info(f"  - Prezzo attuale DB: €{current_db_price:.3f}" if current_db_price else "  - Prezzo attuale DB: None")
                current_app.logger.info(f"  - Prezzo originale prodotto: €{original_product_price:.3f}")
                current_app.logger.info(f"  - Prezzo listino: €{listino_price:.3f}")

                # 🔥 USA LA NUOVA FUNZIONE HELPER PER DETERMINARE IL PREZZO FINALE
                final_price = get_final_ticket_price(
                    ticket_id=ticket['id_ticket'],
                    line_id=ticket_line.IdLineaTicket,
                    original_product_price=original_product_price,
                    listino_price=listino_price,
                    current_db_price=current_db_price
                )

                # 🔥 CORREZIONE: Non usare calculate_ticket_price_with_vat() perché riapplica il listino
                # Calcola direttamente IVA e prezzo senza IVA dal prezzo finale già determinato

                # Determina l'aliquota IVA dal prodotto
                calculated_vat_rate = 0.04  # Default 4%
                if product.IdIva == 4:
                    calculated_vat_rate = 0.00  # 0% - Esente IVA
                elif product.IdIva == 1:
                    calculated_vat_rate = 0.04  # 4%
                elif product.IdIva == 2:
                    calculated_vat_rate = 0.10  # 10%
                elif product.IdIva == 3:
                    calculated_vat_rate = 0.22  # 22%

                # Il final_price è già CON IVA, calcola il prezzo senza IVA
                price_with_vat = final_price
                price_without_vat = final_price / (1 + calculated_vat_rate) if calculated_vat_rate > 0 else final_price
                current_app.logger.info(f"💰 Prezzo finale calcolato per articolo {ticket_line.IdArticulo}: CON IVA=€{price_with_vat:.3f}, SENZA IVA=€{price_without_vat:.3f}")
                
                # Log finale con informazioni sui prezzi utilizzati
                current_app.logger.info(f"💰 Prezzo finale per articolo {ticket_line.IdArticulo}: CON IVA=€{price_with_vat:.3f}, SENZA IVA=€{price_without_vat:.3f} (era €{ticket_price:.3f})")
                # Handle None value for Peso - use 1.0 as default if Peso is None
                peso_value = float(ticket_line.Peso) if ticket_line.Peso is not None else 1.0
                line_total = price_without_vat * peso_value
                line_vat = line_total * calculated_vat_rate  # 🔧 USA IL VAT_RATE CORRETTO
                
                # Applica sconto del ticket se presente PRIMA dell'arrotondamento
                ticket_id_str = str(ticket['id_ticket'])
                ticket_discount = float(ticket_discounts.get(ticket_id_str, 0))
                if ticket_discount > 0:
                    discount_factor = 1 - (ticket_discount / 100)
                    line_total = line_total * discount_factor
                    line_vat = line_vat * discount_factor
                    current_app.logger.info(f"💰 Applicato sconto {ticket_discount}% al ticket {ticket['id_ticket']}")
                    current_app.logger.info(f"   Totale scontato: {line_total:.6f}, IVA scontata: {line_vat:.6f}")
                
                # 🔧 CORREZIONE ARROTONDAMENTO: Non arrotondare qui per evitare errori cumulativi
                # Gli arrotondamenti avverranno solo sui totali finali del DDT
                current_app.logger.info(f"   Prima arrotondamento finale: Totale: {line_total:.6f}, IVA: {line_vat:.6f}")
                
                # Get product family, subfamily, class info
                product_article = Article.query.get(product.IdArticulo)
                
                # Create DDT line
                albaran_line = AlbaranLinea()
                albaran_line.IdLineaAlbaran = line_count
                albaran_line.IdEmpresa = ddt.IdEmpresa
                albaran_line.IdTienda = ddt.IdTienda
                albaran_line.IdBalanzaMaestra = ddt.IdBalanzaMaestra
                albaran_line.IdBalanzaEsclava = ddt.IdBalanzaEsclava
                albaran_line.IdAlbaran = ddt.IdAlbaran
                albaran_line.TipoVenta = ddt.TipoVenta
                
                # Dati prodotto - usa i dati dalla linea del ticket, non dal prodotto
                albaran_line.IdArticulo = ticket_line.IdArticulo
                
                # Genera descrizione base
                base_description = ticket_line.Descripcion or product.Descripcion
                
                # Aggiungi informazioni lotto se abilitato
                from services.utils import format_lot_for_ddt
                lot_text = format_lot_for_ddt(ticket_header, ticket_line)
                
                # Combina descrizione base con informazioni lotto
                albaran_line.Descripcion = base_description + lot_text
                albaran_line.Descripcion1 = getattr(product_article, 'Descripcion1', '') if product_article else ''
                albaran_line.Comportamiento = getattr(ticket_line, 'comportamiento', 0)  # Usa il valore dal ticket
                albaran_line.ComportamientoDevolucion = getattr(ticket_line, 'comportamiento_devolucion', 0)
                
                # Pesi e quantità - Handle None value for Peso
                albaran_line.Peso = peso_value  # Use the same peso_value calculated above
                albaran_line.Medida2 = "un"  # Default come nell'esempio

                # Prezzi e IVA
                albaran_line.Precio = price_with_vat  # Prezzo CON IVA come richiesto
                albaran_line.PrecioSinIVA = round_price_without_vat(price_without_vat)  # Arrotondamento commerciale a 2 decimali
                albaran_line.IdIVA = product.IdIva
                albaran_line.PorcentajeIVA = calculated_vat_rate * 100  # 🔧 USA IL VAT_RATE CORRETTO
                albaran_line.RecargoEquivalencia = 0.0
                
                # Importi - usa valori arrotondati solo per la visualizzazione nel DB
                albaran_line.Importe = round(line_total + line_vat, 2)  # Totale linea
                albaran_line.ImporteSinIVASinDtoL = round(line_total, 2)  # Arrotonda solo per DB
                albaran_line.ImporteDelIVAConDtoL = round(line_vat, 2)  # Arrotonda solo per DB
                
                # Informazioni aggiuntive dal prodotto
                albaran_line.IdClase = getattr(product_article, 'IdClase', None)
                albaran_line.NombreClase = "ARTICOLI"  # Default come nell'esempio
                albaran_line.IdFamilia = product.IdFamilia
                albaran_line.NombreFamilia = ""  # Da popolare se disponibile
                albaran_line.IdSeccion = getattr(product_article, 'IdSeccion', None)
                albaran_line.IdSubFamilia = product.IdSubFamilia
                albaran_line.IdDepartamento = getattr(product_article, 'IdDepartamento', None)
                
                # Gestisci il campo Texto1 in modo sicuro
                texto1_value = ""
                if hasattr(ticket_line, 'Texto1') and ticket_line.Texto1:
                    texto1_value = ticket_line.Texto1
                elif product_article and hasattr(product_article, 'Texto1') and product_article.Texto1:
                    texto1_value = product_article.Texto1
                albaran_line.Texto1 = texto1_value
                
                # Data di scadenza
                albaran_line.FechaCaducidad = ticket_line.FechaCaducidad
                
                # Campi di default
                albaran_line.EstadoLinea = 0
                albaran_line.EntradaManual = 0
                albaran_line.Tara = 0.0
                albaran_line.PrecioPorCienGramos = 0
                albaran_line.Descuento = ticket_discount if ticket_discount > 0 else 0.0
                albaran_line.TipoDescuento = 1
                albaran_line.Facturada = 0
                albaran_line.CantidadFacturada = 0.0
                albaran_line.CantidadFacturada2 = 0.0
                albaran_line.HayTaraAplicada = 0
                albaran_line.Modificado = 1
                albaran_line.Operacion = "A"
                albaran_line.Usuario = "DBLogiX"
                
                # Debug line info
                current_app.logger.info(f"📝 DEBUG: Linea DDT {line_count} - Ticket {ticket['id_ticket']}")
                current_app.logger.info(f"    IdArticulo: {albaran_line.IdArticulo}")
                current_app.logger.info(f"    Peso: {albaran_line.Peso}")
                current_app.logger.info(f"    Prezzo senza IVA: {albaran_line.PrecioSinIVA}")
                current_app.logger.info(f"    Sconto applicato: {albaran_line.Descuento}%")
                current_app.logger.info(f"    Totale senza IVA: {albaran_line.ImporteSinIVASinDtoL}")
                current_app.logger.info(f"    IVA: {albaran_line.ImporteDelIVAConDtoL}")
                
                db.session.add(albaran_line)
                
                # Accumula totali
                total_without_vat += line_total
                total_vat += line_vat
            
            # Aggiorna lo stato del ticket a 'processato'
            # Usiamo direttamente l'ID del ticket passato dal frontend
            ticket_header = TicketHeader.query.get(ticket['id_ticket'])
            if ticket_header:
                ticket_header.Enviado = 1
                current_app.logger.info(f"✅ Ticket {ticket['id_ticket']} impostato come elaborato")
            else:
                current_app.logger.warning(f"⚠️  Non è stato possibile trovare il ticket {ticket['id_ticket']} per aggiornarne lo stato")

        # PROCESSO TICKET MANUALI DAL LOCALSTORAGE
        for manual_ticket in manual_tickets:
            current_app.logger.info(f"✋ DEBUG: Elaborazione ticket manuale {manual_ticket['id_ticket']}")
            
            # Crea direttamente le righe AlbaranLinea per i ticket manuali
            for ticket_line in manual_ticket['lines']:
                line_count += 1
                
                # Calcola aliquota IVA
                id_iva = ticket_line.get('id_iva', 1)  # Default 4% per alimentari
                vat_rate = 0.04  # Default 4%
                if id_iva == 0:
                    vat_rate = 0.00  # 0% - Esente IVA
                elif id_iva == 1:
                    vat_rate = 0.04  # 4%
                elif id_iva == 2:
                    vat_rate = 0.10  # 10%
                elif id_iva == 3:
                    vat_rate = 0.22  # 22%
                
                # CORREZIONE FONDAMENTALE: Per i ticket manuali, il prezzo inserito dall'utente è GIÀ CON IVA
                # e l'IVA è quella selezionata dall'utente nel dropdown
                manual_price_with_vat = float(ticket_line['precio'])
                
                # Per i ticket manuali, NON controllare il listino - usa sempre il prezzo inserito
                current_app.logger.info(f"💰 Ticket manuale - Prezzo CON IVA inserito dall'utente: €{manual_price_with_vat:.3f} (IVA {vat_rate*100:.0f}%)")
                
                # Scorporo IVA dal prezzo inserito dall'utente
                price_without_vat = round_price_without_vat(manual_price_with_vat / (1 + vat_rate)) if vat_rate > 0 else manual_price_with_vat
                price_with_vat = manual_price_with_vat
                peso_value = float(ticket_line['peso'])
                line_total = price_without_vat * peso_value
                line_vat = line_total * vat_rate
                
                # Applica sconto del ticket manuale se presente PRIMA dell'arrotondamento
                manual_ticket_id_str = str(manual_ticket['id_ticket'])
                ticket_discount = float(ticket_discounts.get(manual_ticket_id_str, 0))
                if ticket_discount > 0:
                    discount_factor = 1 - (ticket_discount / 100)
                    line_total = line_total * discount_factor
                    line_vat = line_vat * discount_factor
                    current_app.logger.info(f"💰 Applicato sconto {ticket_discount}% al ticket manuale {manual_ticket['id_ticket']}")
                    current_app.logger.info(f"   Totale scontato: {line_total:.6f}, IVA scontata: {line_vat:.6f}")
                
                # 🔧 CORREZIONE ARROTONDAMENTO: Non arrotondare qui per evitare errori cumulativi
                # Gli arrotondamenti avverranno solo sui totali finali del DDT
                current_app.logger.info(f"   Prima arrotondamento finale: Totale: {line_total:.6f}, IVA: {line_vat:.6f}")
                
                # Crea riga DDT per ticket manuale
                albaran_line = AlbaranLinea()
                albaran_line.IdLineaAlbaran = line_count
                albaran_line.IdEmpresa = ddt.IdEmpresa
                albaran_line.IdTienda = ddt.IdTienda
                albaran_line.IdBalanzaMaestra = ddt.IdBalanzaMaestra
                albaran_line.IdBalanzaEsclava = ddt.IdBalanzaEsclava
                albaran_line.IdAlbaran = ddt.IdAlbaran
                albaran_line.TipoVenta = ddt.TipoVenta
                
                # Dati prodotto dal ticket manuale
                albaran_line.IdArticulo = 999  # ID prodotto personalizzato
                
                # Genera descrizione base per ticket manuale
                base_description = ticket_line['descripcion']
                
                # Per i ticket manuali, gestiamo il lotto se fornito dall'utente
                lotto_manuale = ticket_line.get('lotto', '').strip()
                if lotto_manuale:
                    # Se l'utente ha inserito un lotto, lo aggiungiamo alla descrizione e al campo TextoLote
                    albaran_line.Descripcion = f"{base_description} - LOTTO: {lotto_manuale}"
                    albaran_line.TextoLote = lotto_manuale
                    current_app.logger.info(f"📦 Lotto manuale aggiunto: {lotto_manuale}")
                else:
                    albaran_line.Descripcion = base_description
                    albaran_line.TextoLote = ""
                albaran_line.Descripcion1 = "Prodotto manuale"
                comportamiento = ticket_line.get('comportamiento', 1)
                albaran_line.Comportamiento = comportamiento
                albaran_line.ComportamientoDevolucion = 0
                
                # Pesi e quantità
                albaran_line.Peso = peso_value
                # Imposta l'unità di misura in base al tipo di articolo
                albaran_line.Medida2 = "kg" if comportamiento == 1 else "un"

                # Prezzi e IVA
                albaran_line.Precio = price_with_vat  # Prezzo CON IVA come richiesto
                albaran_line.PrecioSinIVA = round_price_without_vat(price_without_vat)  # Arrotondamento commerciale a 2 decimali
                albaran_line.IdIVA = id_iva
                albaran_line.PorcentajeIVA = vat_rate * 100
                albaran_line.RecargoEquivalencia = 0.0
                
                # Importi - usa valori arrotondati solo per la visualizzazione nel DB
                albaran_line.Importe = round(line_total + line_vat, 2)  # Totale linea
                albaran_line.ImporteSinIVASinDtoL = round(line_total, 2)  # Arrotonda solo per DB
                albaran_line.ImporteDelIVAConDtoL = round(line_vat, 2)  # Arrotonda solo per DB
                
                # Informazioni di default per prodotti manuali
                albaran_line.IdClase = 1
                albaran_line.NombreClase = "ARTICOLI"
                albaran_line.IdFamilia = 1
                albaran_line.NombreFamilia = "MANUALE"
                albaran_line.IdSubFamilia = 1
                albaran_line.NombreSubFamilia = "MANUALE"
                albaran_line.IdDepartamento = 1
                albaran_line.NombreDepartamento = "MANUALE"
                albaran_line.Texto1 = "Prodotto aggiunto manualmente"
                
                # Data di scadenza se presente
                if ticket_line.get('fecha_caducidad'):
                    try:
                        albaran_line.FechaCaducidad = datetime.strptime(ticket_line['fecha_caducidad'], '%Y-%m-%d')
                    except:
                        albaran_line.FechaCaducidad = None
                
                # Campi di default
                albaran_line.EstadoLinea = 0
                albaran_line.EntradaManual = 1  # Indica che è stato inserito manualmente
                albaran_line.Tara = 0.0
                albaran_line.PrecioPorCienGramos = 0
                albaran_line.Descuento = ticket_discount if ticket_discount > 0 else 0.0
                albaran_line.TipoDescuento = 1
                albaran_line.Facturada = 0
                albaran_line.CantidadFacturada = 0.0
                albaran_line.CantidadFacturada2 = 0.0
                albaran_line.HayTaraAplicada = 0
                albaran_line.Modificado = 1
                albaran_line.Operacion = "A"
                albaran_line.Usuario = "DBLogiX"
                
                # Debug line info
                current_app.logger.info(f"✋ DEBUG: Linea DDT manuale {line_count}")
                current_app.logger.info(f"    Descrizione: {albaran_line.Descripcion}")
                current_app.logger.info(f"    Peso: {albaran_line.Peso}")
                current_app.logger.info(f"    Prezzo senza IVA: {albaran_line.PrecioSinIVA}")
                current_app.logger.info(f"    Sconto applicato: {albaran_line.Descuento}%")
                current_app.logger.info(f"    Totale senza IVA: {albaran_line.ImporteSinIVASinDtoL}")
                current_app.logger.info(f"    IVA: {albaran_line.ImporteDelIVAConDtoL}")
                
                db.session.add(albaran_line)
                
                # Accumula totali
                total_without_vat += line_total
                total_vat += line_vat

        # 🔧 CORREZIONE ARROTONDAMENTO: Arrotonda solo i totali finali per evitare errori cumulativi
        total_without_vat = round(total_without_vat, 2)
        total_vat = round(total_vat, 2)
        total_ddt_amount = total_without_vat + total_vat
        
        current_app.logger.info(f"💰 TOTALI FINALI - CON IVA: €{total_ddt_amount:.2f}, SENZA IVA: €{total_without_vat:.2f}, IVA: €{total_vat:.2f}")
        
        # Aggiorna i totali del DDT
        ddt.NumLineas = line_count
        ddt.ImporteLineas = total_ddt_amount
        ddt.ImporteTotal = total_ddt_amount
        ddt.ImporteTotalSinIVAConDtoL = total_without_vat
        ddt.ImporteTotalDelIVAConDtoLConDtoTotal = total_vat
        ddt.ImporteTotalSinIVAConDtoLConDtoTotal = total_without_vat
        
        current_app.logger.info(f"💰 DEBUG: Totali DDT - Senza IVA: €{total_without_vat:.2f}, IVA: €{total_vat:.2f}, Totale: €{total_ddt_amount:.2f}")
        
        # DEBUG: Verifica che le righe siano state aggiunte alla sessione
        pending_albaran_lines = [obj for obj in db.session.new if isinstance(obj, AlbaranLinea)]
        current_app.logger.info(f"🔍 DEBUG: {len(pending_albaran_lines)} righe AlbaranLinea in attesa di commit")
        
        if len(pending_albaran_lines) == 0:
            current_app.logger.error("❌ ERRORE CRITICO: Nessuna riga AlbaranLinea in attesa di commit!")
            current_app.logger.error(f"📊 DEBUG: ticket_data={len(ticket_data)}, manual_tickets={len(manual_tickets)}")
            current_app.logger.error(f"📊 DEBUG: line_count={line_count}")
            raise Exception("Nessuna riga DDT creata - verifica i dati di input")
        
        # Aggiorna la tabella dat_albaran_max_num_albaran con il numero del DDT appena creato
        from app.models import AlbaranMaxNumAlbaran
        try:
            AlbaranMaxNumAlbaran.update_max_num_albaran(ddt.NumAlbaran)
            current_app.logger.info(f"✅ Aggiornata tabella dat_albaran_max_num_albaran con NumAlbaran: {ddt.NumAlbaran}")
        except Exception as e:
            current_app.logger.error(f"⚠️ Errore nell'aggiornamento di dat_albaran_max_num_albaran: {str(e)}")
        
        # Commit della transazione
        db.session.commit()

        # DEBUG: Verifica che la data sia stata salvata correttamente
        saved_ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt.IdAlbaran).first()
        if saved_ddt:
            current_app.logger.info(f"📅 DEBUG DDT SAVED: Data salvata nel DB - Fecha = {saved_ddt.Fecha}")
            current_app.logger.info(f"📅 DEBUG DDT SAVED: Data selezionata era - now = {now}")
            if saved_ddt.Fecha != now.replace(microsecond=0):  # Confronta ignorando microsecondi
                current_app.logger.warning(f"⚠️ DATA MISMATCH: Data salvata ({saved_ddt.Fecha}) != Data selezionata ({now})")
            else:
                current_app.logger.info(f"✅ DATA MATCH: Data salvata correttamente!")

        current_app.logger.info(f"🎉 DDT #{ddt.IdAlbaran} creato con successo!")
        current_app.logger.info(f"📊 Riepilogo: {len(ticket_data)} ticket normali + {len(manual_tickets)} ticket manuali = {line_count} righe totali")
        
        # SALVATAGGIO AUTOMATICO PDF DEL DDT
        try:
            save_ddt_pdf_automatically(ddt, client, empresa)
            current_app.logger.info(f"📄 PDF del DDT #{ddt.IdAlbaran} salvato automaticamente")
        except Exception as pdf_error:
            current_app.logger.error(f"⚠️  Errore nel salvataggio automatico PDF DDT #{ddt.IdAlbaran}: {str(pdf_error)}")
            import traceback
            current_app.logger.error(f"📄 Traceback errore PDF: {traceback.format_exc()}")
            # Non blocchiamo il processo per un errore di salvataggio PDF
        
        # Se il DDT è stato creato da un task, aggiorna il task con l'ID del DDT
        if from_task and task_id:
            from app.models import Task
            task = Task.query.get(task_id)
            if task:
                task.ddt_generated = True
                task.ddt_id = ddt.IdAlbaran
                db.session.commit()
                current_app.logger.info(f"📝 Task #{task.task_number} aggiornato con DDT #{ddt.IdAlbaran}")
            else:
                current_app.logger.warning(f"⚠️  Task {task_id} non trovato per l'associazione con DDT #{ddt.IdAlbaran}")
        
        flash(f'DDT #{ddt.IdAlbaran} creato con successo con {line_count} righe!', 'success')
        
        # Redirect based on source
        if from_task and task_id:
            flash(f'DDT #{ddt.IdAlbaran} generato dal task #{task_id}', 'success')
        else:
            flash(f'DDT #{ddt.IdAlbaran} generato dal warehouse', 'success')
        
        return redirect(url_for('ddt.detail', ddt_id=ddt.IdAlbaran))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore nella creazione del DDT: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Errore nella creazione del DDT: {str(e)}', 'danger')
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))

@ddt_bp.route('/create_invoice_only', methods=['POST'])
@login_required
def create_invoice_only():
    """Genera solo la fattura elettronica senza creare il DDT"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        return jsonify({'success': False, 'error': 'Non hai i permessi per creare fatture. Contatta l\'amministratore.'})
    
    # Get form data
    cliente_id = request.form.get('cliente_id')
    id_empresa = request.form.get('id_empresa', 1)
    tickets_data = request.form.get('tickets')
    manual_tickets_data = request.form.get('manual_tickets')
    ticket_discounts_data = request.form.get('ticket_discounts')
    ticket_modifications_data = request.form.get('ticket_modifications')  # 🔥 NUOVO: Modifiche prezzi dal localStorage
    note = request.form.get('note')
    creation_date_str = request.form.get('creation_date')  # Data creazione personalizzata
    
    if not cliente_id:
        return jsonify({'success': False, 'error': 'Cliente mancante'})
    
    # Parse ticket data
    try:
        ticket_data = json.loads(tickets_data) if tickets_data else []
        manual_tickets = json.loads(manual_tickets_data) if manual_tickets_data else []
        ticket_discounts = json.loads(ticket_discounts_data) if ticket_discounts_data else {}
        ticket_modifications = json.loads(ticket_modifications_data) if ticket_modifications_data else {}  # 🔥 NUOVO: Modifiche dal localStorage
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Formato dati ticket non valido'})
    
    # Verifica che ci sia almeno un ticket
    if not ticket_data and not manual_tickets:
        return jsonify({'success': False, 'error': 'Nessun ticket selezionato'})
    
    # Get client and company info
    client = Client.query.get_or_404(int(cliente_id))
    empresa = Company.query.get_or_404(int(id_empresa))
    
    try:
        # Determina la data di creazione (personalizzata o attuale)
        if creation_date_str:
            try:
                # Parse della data nel formato YYYY-MM-DD
                creation_date = datetime.strptime(creation_date_str, '%Y-%m-%d')
                current_app.logger.info(f"📅 [Fattura] Usando data creazione personalizzata: {creation_date}")
            except ValueError as e:
                current_app.logger.warning(f"⚠️ [Fattura] Formato data non valido '{creation_date_str}', uso data attuale: {e}")
                creation_date = datetime.now()
        else:
            creation_date = datetime.now()
            current_app.logger.info(f"📅 [Fattura] Nessuna data personalizzata fornita, uso data attuale: {creation_date}")

        # Per retrocompatibilità, mantieni la variabile 'now' ma usala solo dove necessario
        now = creation_date

            # Assicura che esista il prodotto personalizzato per i ticket manuali
        if manual_tickets:
            ensure_custom_product_exists()

        # 🔥 NUOVO: Funzione helper per determinare il prezzo finale con priorità corretta
        def get_final_ticket_price(ticket_id, line_id, original_product_price, listino_price, current_db_price=None):
            """
            Determina il prezzo finale con la seguente priorità:
            1. localStorage modifications (ddt_ticket_modifications)
            2. Database modifications (se prezzo diverso da originale)
            3. Listino prezzi dedicato cliente
            4. Prezzo originale prodotto
            """
            # 1. 🔥 PRIMA PRIORITÀ: Controlla modifiche nel localStorage
            modification_key = f"{ticket_id}_{line_id}_precio"
            if modification_key in ticket_modifications:
                modification = ticket_modifications[modification_key]
                if modification and 'value' in modification:
                    local_storage_price = float(modification['value'])
                    current_app.logger.info(f"🔥 [Fattura] PRIORITÀ 1 - localStorage: Usando prezzo modificato per articolo {line_id}: €{local_storage_price:.3f}")
                    return local_storage_price

            # 2. SECONDA PRIORITÀ: Controlla modifiche nel database
            if current_db_price is not None:
                price_modified_in_db = abs(current_db_price - original_product_price) > 0.001
                if price_modified_in_db:
                    current_app.logger.info(f"💰 [Fattura] PRIORITÀ 2 - Database: Usando prezzo modificato per articolo {line_id}: €{current_db_price:.3f}")
                    return current_db_price

            # 3. TERZA PRIORITÀ: Listino prezzi dedicato cliente
            if listino_price != original_product_price:
                current_app.logger.info(f"🏷️ [Fattura] PRIORITÀ 3 - Listino: Usando prezzo del listino per articolo {line_id}: €{listino_price:.3f}")
                return listino_price

            # 4. QUARTA PRIORITÀ: Prezzo originale prodotto
            current_app.logger.info(f"📦 [Fattura] PRIORITÀ 4 - Originale: Usando prezzo originale prodotto per articolo {line_id}: €{original_product_price:.3f}")
            return original_product_price

        # Genera la fattura elettronica direttamente dai dati dei ticket
        from modules.fattura_pa import create_fattura_pa_from_data
        
        # Prepara i dati per la generazione della fattura
        invoice_data = {
            'company': empresa,
            'client': client,
            'lines': [],
            'note': note,
            'date': creation_date  # Usa la data personalizzata invece di now
        }
        
        # Aggiungi le linee dai ticket normali
        for ticket in ticket_data:
            ticket_header = TicketHeader.query.filter_by(IdTicket=ticket['id_ticket']).first()
            if not ticket_header:
                continue
                
            ticket_lines = TicketLine.query.filter_by(IdTicket=ticket['id_ticket']).all()
            discount_percent = float(ticket_discounts.get(str(ticket['id_ticket']), 0))
            
            for line in ticket_lines:
                # CORREZIONE PRIORITÀ: 1) Prezzo modificato dall'utente, 2) Listino cliente, 3) Prezzo originale prodotto
                ticket_price = float(line.Precio or 0)

                # 🎯 OTTIENI IL PREZZO ORIGINALE DEL PRODOTTO DAL DATABASE DEGLI ARTICOLI
                original_product_price = 0.0
                try:
                    product = Product.query.get(line.IdArticulo)
                    if product and product.PrecioConIVA:
                        original_product_price = float(product.PrecioConIVA)
                        current_app.logger.info(f"🔍 [Fattura] DEBUG Articolo {line.IdArticulo} - Prezzo originale prodotto: €{original_product_price:.3f}")
                    else:
                        current_app.logger.warning(f"⚠️ [Fattura] Articolo {line.IdArticulo} senza prezzo originale, uso prezzo ticket: €{ticket_price:.3f}")
                        original_product_price = ticket_price
                except Exception as e:
                    current_app.logger.error(f"❌ [Fattura] Errore recupero prezzo originale prodotto {line.IdArticulo}: {str(e)}")
                    original_product_price = ticket_price

                # IMPORTANTE: Controlla se il prezzo è stato modificato dall'utente nella preview
                # Prima ricarica la linea dal database per ottenere eventuali modifiche
                from app.models import TicketLine as TicketLineModel
                current_ticket_line = TicketLineModel.query.filter_by(
                    IdTicket=line.IdTicket,
                    IdLineaTicket=line.IdLineaTicket
                ).first()

                # 🎯 CORREZIONE: Usa il prezzo ORIGINALE del prodotto per il listino, non quello del ticket che potrebbe essere modificato
                listino_price = get_cliente_listino_price(int(cliente_id), line.IdArticulo, original_product_price)

                # 🔥 NUOVA LOGICA PRIORITÀ PREZZI AGGIORNATA:
                # 1. localStorage modifications (ddt_ticket_modifications)
                # 2. Database modifications (se prezzo diverso da originale)
                # 3. Listino prezzi dedicato cliente
                # 4. Prezzo originale prodotto

                # Prepara i dati per la funzione helper
                current_db_price = None
                if current_ticket_line and current_ticket_line.Precio is not None:
                    current_db_price = float(current_ticket_line.Precio)

                current_app.logger.info(f"🔍 [Fattura] DEBUG Articolo {line.IdArticulo}:")
                current_app.logger.info(f"  - Prezzo attuale DB: €{current_db_price:.3f}" if current_db_price else "  - Prezzo attuale DB: None")
                current_app.logger.info(f"  - Prezzo originale prodotto: €{original_product_price:.3f}")
                current_app.logger.info(f"  - Prezzo listino: €{listino_price:.3f}")

                # 🔥 USA LA NUOVA FUNZIONE HELPER PER DETERMINARE IL PREZZO FINALE
                final_price = get_final_ticket_price(
                    ticket_id=ticket['id_ticket'],
                    line_id=line.IdLineaTicket,
                    original_product_price=original_product_price,
                    listino_price=listino_price,
                    current_db_price=current_db_price
                )
                
                # Applica sconto del ticket se presente
                if discount_percent > 0:
                    final_price = final_price * (1 - discount_percent / 100)

                quantity = float(line.Peso or 1)

                # 🔥 CORREZIONE: Calcola direttamente IVA dal prezzo finale già determinato
                # Determina l'aliquota IVA dal prodotto
                calculated_vat_rate = 0.04  # Default 4%
                if product.IdIva == 4:
                    calculated_vat_rate = 0.00  # 0% - Esente IVA
                elif product.IdIva == 1:
                    calculated_vat_rate = 0.04  # 4%
                elif product.IdIva == 2:
                    calculated_vat_rate = 0.10  # 10%
                elif product.IdIva == 3:
                    calculated_vat_rate = 0.22  # 22%

                # Il final_price è già CON IVA, calcola il prezzo senza IVA
                price_without_vat = final_price / (1 + calculated_vat_rate) if calculated_vat_rate > 0 else final_price
                price_without_vat = round_price_without_vat(price_without_vat)
                
                # Calcola il totale della linea senza IVA
                line_total_without_vat = quantity * price_without_vat
                line_total_without_vat = round_product_amount(line_total_without_vat)
                
                # Determina l'unità di misura - usa un valore di default poiché TicketLine non ha Medida2
                unita_misura = 'PZ'  # Default
                if product:
                    # Controlla il comportamento del prodotto per determinare l'unità
                    comportamiento = getattr(line, 'comportamiento', 0) or (product.Comportamiento if hasattr(product, 'Comportamiento') else 0)
                    if comportamiento == 0:  # Prodotto a peso
                        unita_misura = 'Kg'
                    else:  # Prodotto numerabile
                        unita_misura = 'PZ'
                
                invoice_data['lines'].append({
                    'descrizione': line.Descripcion or (product.Descripcion if product else 'Articolo'),
                    'quantita': quantity,
                    'unita_misura': unita_misura,
                    'prezzo_unitario': price_without_vat,
                    'prezzo_totale': line_total_without_vat,
                    'aliquota_iva': calculated_vat_rate * 100,  # Converti in percentuale per la fattura
                    'id_articolo': line.IdArticulo
                })
        
        # Aggiungi le linee dai ticket manuali
        for ticket in manual_tickets:
            discount_percent = float(ticket_discounts.get(str(ticket['id_ticket']), 0))
            
            for line_data in ticket['lines']:
                quantity = float(line_data.get('peso', 1))
                final_price = float(line_data.get('precio', 0))
                
                # Applica sconto del ticket se presente
                if discount_percent > 0:
                    final_price = final_price * (1 - discount_percent / 100)
                
                # Calcola IVA per ticket manuale
                id_iva = int(line_data.get('id_iva', 1))  # Default 4% per alimentari
                vat_rate = 4.0  # Default 4%
                if id_iva == 0:
                    vat_rate = 0.0  # 0% - Esente IVA
                elif id_iva == 1:
                    vat_rate = 4.0  # 4%
                elif id_iva == 2:
                    vat_rate = 10.0  # 10%
                elif id_iva == 3:
                    vat_rate = 22.0  # 22%
                
                # Calcola il prezzo senza IVA (il prezzo finale è già con IVA)
                price_without_vat = final_price / (1 + vat_rate / 100) if vat_rate > 0 else final_price
                price_without_vat = round_price_without_vat(price_without_vat)
                
                # Calcola il totale della linea senza IVA
                line_total_without_vat = quantity * price_without_vat
                line_total_without_vat = round_product_amount(line_total_without_vat)
                
                # Determina l'unità di misura per ticket manuale
                comportamiento = int(line_data.get('comportamiento', 1))
                unita_misura = 'Kg' if comportamiento == 0 else 'PZ'
                
                invoice_data['lines'].append({
                    'descrizione': line_data.get('descripcion', 'Prodotto Personalizzato'),
                    'quantita': quantity,
                    'unita_misura': unita_misura,
                    'prezzo_unitario': price_without_vat,
                    'prezzo_totale': line_total_without_vat,
                    'aliquota_iva': vat_rate * 100,  # Converti in percentuale per la fattura
                    'id_articolo': line_data.get('id_articulo', 999)
                })
        
        # Genera la fattura elettronica
        xml_data, error_message = create_fattura_pa_from_data(invoice_data)
        
        if xml_data is None:
            return jsonify({'success': False, 'error': f'Errore nella generazione della fattura: {error_message}'})
        
        # Salva il file XML della fattura
        import os
        
        # Crea la struttura delle cartelle: Fatture/{anno}
        invoice_year = now.year
        invoice_dir = os.path.join(current_app.root_path, 'Fatture', str(invoice_year))
        os.makedirs(invoice_dir, exist_ok=True)
        
        # Genera il nome del file
        client_name_clean = "".join(c for c in (client.Nombre or 'Cliente_Sconosciuto') if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        timestamp = now.strftime('%y%m%d%H%M')
        xml_filename = f"IT{empresa.CIF_VAT.replace('IT', '')}_FPR12_{timestamp}.xml"
        xml_path = os.path.join(invoice_dir, xml_filename)
        
        # Salva il file XML
        with open(xml_path, 'wb') as xml_file:
            xml_file.write(xml_data)
        
        current_app.logger.info(f"📄 Fattura elettronica generata: {xml_path}")
        
        # Salva la fattura nel database usando SOLO le tabelle di fattura
        from modules.fattura_pa import save_fattura_to_db
        try:
            fattura_db = save_fattura_to_db(invoice_data, xml_filename, xml_path, None)
            if fattura_db:
                current_app.logger.info(f"💾 Fattura salvata nel database: ID {fattura_db.IdFactura}")
                # Reindirizza alla vista database invece che al file
                invoice_url = url_for('fattura_pa.invoice_detail_db', fattura_id=fattura_db.IdFactura)
            else:
                # Fallback alla vista file se salvataggio DB fallisce
                invoice_url = url_for('fattura_pa.invoice_detail_page', filename=xml_filename)
        except Exception as e:
            current_app.logger.error(f"⚠️  Errore nel salvataggio database: {str(e)}")
            # Fallback alla vista file
            invoice_url = url_for('fattura_pa.invoice_detail_page', filename=xml_filename)
        
        # ✅ AGGIORNA STATO TICKET A 'PROCESSATO' DOPO GENERAZIONE FATTURA
        try:
            tickets_updated = 0
            
            # Aggiorna i ticket normali
            for ticket in ticket_data:
                ticket_header = TicketHeader.query.filter_by(IdTicket=ticket['id_ticket']).first()
                if ticket_header and ticket_header.Enviado != 1:  # Solo se non già processato
                    old_status = ticket_header.Enviado
                    ticket_header.Enviado = 1  # Stato 'Processato'
                    tickets_updated += 1
                    current_app.logger.info(f"📋 Ticket #{ticket_header.NumTicket} (ID: {ticket_header.IdTicket}) aggiornato da stato {old_status} a 'Processato' (1)")
            
            # Commit delle modifiche ai ticket
            db.session.commit()
            current_app.logger.info(f"✅ {tickets_updated} ticket aggiornati a stato 'Processato' dopo generazione fattura")
            
        except Exception as e:
            current_app.logger.error(f"⚠️  Errore nell'aggiornamento stato ticket: {str(e)}")
            # Non bloccare il processo se l'aggiornamento fallisce
            db.session.rollback()

        # 🔥 NUOVA LOGICA: CREAZIONE DELL'ALBARAN NEL DATABASE
        # Scrive i dati dei ticket nella tabella dat_albaran_linea come richiesto
        try:
            current_app.logger.info("🔥 [Fattura] Iniziando creazione Albaran per scrittura dati ticket...")

            # Ottieni il numero massimo di albaran e incrementa
            max_num_albaran = db.session.query(db.func.max(AlbaranCabecera.NumAlbaran)).scalar() or 0

            # Ottieni il prossimo IdAlbaran
            max_id_albaran = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 999998
            if max_id_albaran < 999999:
                next_id_albaran = 999999
            else:
                next_id_albaran = max_id_albaran + 1

            # Assicura unicità della chiave primaria
            existing_ddt = AlbaranCabecera.query.filter_by(
                IdAlbaran=next_id_albaran,
                IdEmpresa=id_empresa,
                IdTienda=1,
                IdBalanzaMaestra=1,
                IdBalanzaEsclava=-1
            ).first()

            if existing_ddt:
                next_id_albaran = max_id_albaran + 2
                current_app.logger.warning(f"⚠️ [Fattura] Primary key conflict, using IdAlbaran: {next_id_albaran}")

            current_app.logger.info(f"🆔 [Fattura] Creating Albaran with IdAlbaran: {next_id_albaran}")

            # Crea AlbaranCabecera
            albaran_cabecera = AlbaranCabecera(
                IdAlbaran=next_id_albaran,
                NumAlbaran=max_num_albaran + 1,
                IdEmpresa=id_empresa,
                IdTienda=1,
                IdBalanzaMaestra=1,
                IdBalanzaEsclava=-1,

                # Dati azienda
                NombreEmpresa=empresa.NombreEmpresa,
                CIF_VAT_Empresa=empresa.CIF_VAT or "",
                DireccionEmpresa=empresa.Direccion or "",
                PoblacionEmpresa=empresa.Poblacion or "",
                CPEmpresa=empresa.CodPostal or "",
                TelefonoEmpresa=empresa.Telefono1 or "",
                ProvinciaEmpresa=empresa.Provincia or "",
                NombreTienda="Dibal S.A.",
                NombreBalanzaMaestra="MASTER ETI",
                NombreBalanzaEsclava="",

                # Dati cliente
                IdCliente=cliente_id,
                NombreCliente=client.Nombre,
                DNICliente=client.DNI or "",
                EmailCliente=client.Email or "",
                DireccionCliente=client.Direccion or "",
                PoblacionCliente=client.Poblacion or "",
                ProvinciaCliente=client.Provincia or "",
                PaisCliente=client.Pais or "IT",
                CPCliente=client.CodPostal or "",
                TelefonoCliente=client.Telefono1 or "",
                ObservacionesCliente=client.Observaciones or "None",
                EANCliente=client.EANScanner or "",

                # Informazioni Albaran
                Tipo="A",
                IdVendedor=1,
                NombreVendedor="IL CAPO",
                ReferenciaDocumento="",
                ObservacionesDocumento=note or "",
                TipoVenta=2,

                # Date
                Fecha=now,
                FechaModificacion=now,

                # Totali (verranno calcolati)
                ImporteLineas=0.0,
                PorcDescuento=None,
                ImporteDescuento=None,
                ImporteRE=0.0,
                ImporteTotalSinRE=0.0,
                ImporteTotalSinIVAConDtoLConDtoTotalConRE=0.0,
                ImporteTotal=0.0,
                ImporteTotalSinIVAConDtoL=0.0,
                ImporteTotalSinIVAConDtoLConDtoTotal=0.0,
                ImporteTotalDelIVAConDtoLConDtoTotal=0.0,

                # Altri campi
                PreseleccionCliente=1,
                Enviado=0,
                NumLineas=0,  # Verrà aggiornato
                CodigoBarras="",
                CodBarrasTalonCaja="",
                SerieLTicketErroneo=0,
                Modificado=1,
                Operacion="A",
                Usuario="DBLogiX",
                EstadoTicket="C",
                REAplicado=0,
                Version="4.7.0"
            )

            db.session.add(albaran_cabecera)
            db.session.flush()
            current_app.logger.info(f"✅ [Fattura] Created AlbaranCabecera with ID: {albaran_cabecera.IdAlbaran}")

            # Crea AlbaranLinea per ogni linea dei ticket
            line_count = 0
            total_ddt_amount = 0
            total_without_vat = 0
            total_vat = 0

            # Elabora ticket normali
            for ticket in ticket_data:
                ticket_header = TicketHeader.query.filter_by(IdTicket=ticket['id_ticket']).first()
                if not ticket_header:
                    continue

                ticket_lines = TicketLine.query.filter_by(IdTicket=ticket['id_ticket']).all()
                discount_percent = float(ticket_discounts.get(str(ticket['id_ticket']), 0))

                for line in ticket_lines:
                    line_count += 1
                    product = Product.query.get(line.IdArticulo)

                    if not product:
                        current_app.logger.warning(f"⚠️ [Fattura] Product {line.IdArticulo} not found, skipping line")
                        continue

                    # Determina aliquota IVA
                    vat_rate = 0.04  # Default 4%
                    if product.IdIva == 4:
                        vat_rate = 0.00  # 0% - Esente IVA
                    elif product.IdIva == 1:
                        vat_rate = 0.04  # 4%
                    elif product.IdIva == 2:
                        vat_rate = 0.10  # 10%
                    elif product.IdIva == 3:
                        vat_rate = 0.22  # 22%

                    # Calcola prezzi usando la stessa logica della fattura
                    ticket_price = float(line.Precio or 0)

                    # Prezzo originale prodotto
                    original_product_price = 0.0
                    try:
                        if product and product.PrecioConIVA:
                            original_product_price = float(product.PrecioConIVA)
                        else:
                            original_product_price = ticket_price
                    except Exception as e:
                        current_app.logger.error(f"❌ [Fattura] Error getting original product price {line.IdArticulo}: {str(e)}")
                        original_product_price = ticket_price

                    # Prezzo listino cliente
                    listino_price = get_cliente_listino_price(int(cliente_id), line.IdArticulo, original_product_price)

                    # Determina prezzo finale usando la stessa logica
                    current_db_price = None
                    current_ticket_line = TicketLineModel.query.filter_by(
                        IdTicket=line.IdTicket,
                        IdLineaTicket=line.IdLineaTicket
                    ).first()
                    if current_ticket_line and current_ticket_line.Precio is not None:
                        current_db_price = float(current_ticket_line.Precio)

                    final_price = get_final_ticket_price(
                        ticket_id=ticket['id_ticket'],
                        line_id=line.IdLineaTicket,
                        original_product_price=original_product_price,
                        listino_price=listino_price,
                        current_db_price=current_db_price
                    )

                    # Calcola prezzo senza IVA
                    price_with_vat = final_price
                    price_without_vat = final_price / (1 + vat_rate) if vat_rate > 0 else final_price

                    # Calcola totali
                    peso_value = float(line.Peso) if line.Peso is not None else 1.0
                    line_total = price_without_vat * peso_value
                    line_vat = line_total * vat_rate

                    # Applica sconto ticket
                    if discount_percent > 0:
                        discount_factor = 1 - (discount_percent / 100)
                        line_total = line_total * discount_factor
                        line_vat = line_vat * discount_factor

                    # Crea AlbaranLinea
                    product_article = Article.query.get(product.IdArticulo)

                    # Gestisci descrizione con lotto
                    from services.utils import format_lot_for_ddt
                    base_description = line.Descripcion or product.Descripcion
                    lot_text = format_lot_for_ddt(ticket_header, line)
                    full_description = base_description + lot_text

                    albaran_linea = AlbaranLinea()
                    albaran_linea.IdLineaAlbaran = line_count
                    albaran_linea.IdEmpresa = albaran_cabecera.IdEmpresa
                    albaran_linea.IdTienda = albaran_cabecera.IdTienda
                    albaran_linea.IdBalanzaMaestra = albaran_cabecera.IdBalanzaMaestra
                    albaran_linea.IdBalanzaEsclava = albaran_cabecera.IdBalanzaEsclava
                    albaran_linea.IdAlbaran = albaran_cabecera.IdAlbaran
                    albaran_linea.TipoVenta = albaran_cabecera.TipoVenta

                    # Dati prodotto
                    albaran_linea.IdArticulo = line.IdArticulo
                    albaran_linea.Descripcion = full_description[:100] if len(full_description) > 100 else full_description
                    albaran_linea.Descripcion1 = getattr(product_article, 'Descripcion1', '') if product_article else ''
                    albaran_linea.Comportamiento = getattr(line, 'comportamiento', 0)
                    albaran_linea.ComportamientoDevolucion = getattr(line, 'comportamiento_devolucion', 0)

                    # Pesi e quantità
                    albaran_linea.Peso = peso_value
                    albaran_linea.Medida2 = "un"

                    # Prezzi e IVA
                    albaran_linea.Precio = price_with_vat  # Prezzo unitario CON IVA
                    albaran_linea.PrecioSinIVA = round_price_without_vat(price_without_vat)  # Arrotondamento commerciale a 2 decimali
                    albaran_linea.IdIVA = product.IdIva
                    albaran_linea.PorcentajeIVA = vat_rate * 100
                    albaran_linea.RecargoEquivalencia = 0.0

                    # Importi
                    albaran_linea.Importe = round(line_total + line_vat, 2)
                    albaran_linea.ImporteSinIVASinDtoL = round(line_total, 2)
                    albaran_linea.ImporteDelIVAConDtoL = round(line_vat, 2)

                    # Informazioni prodotto
                    albaran_linea.IdClase = getattr(product_article, 'IdClase', None)
                    albaran_linea.NombreClase = "ARTICOLI"
                    albaran_linea.IdFamilia = product.IdFamilia
                    albaran_linea.NombreFamilia = ""
                    albaran_linea.IdSeccion = getattr(product_article, 'IdSeccion', None)
                    albaran_linea.IdSubFamilia = product.IdSubFamilia
                    albaran_linea.IdDepartamento = getattr(product_article, 'IdDepartamento', None)
                    albaran_linea.NombreDepartamento = ""

                    # Testo1
                    texto1_value = ""
                    if hasattr(line, 'Texto1') and line.Texto1:
                        texto1_value = line.Texto1
                    elif product_article and hasattr(product_article, 'Texto1') and product_article.Texto1:
                        texto1_value = product_article.Texto1
                    albaran_linea.Texto1 = texto1_value

                    # Data scadenza
                    albaran_linea.FechaCaducidad = line.FechaCaducidad

                    # Campi default
                    albaran_linea.EstadoLinea = 0
                    albaran_linea.EntradaManual = 0
                    albaran_linea.Tara = 0.0
                    albaran_linea.PrecioPorCienGramos = 0
                    albaran_linea.Descuento = discount_percent if discount_percent > 0 else 0.0
                    albaran_linea.TipoDescuento = 1
                    albaran_linea.Facturada = 0
                    albaran_linea.CantidadFacturada = 0.0
                    albaran_linea.CantidadFacturada2 = 0.0
                    albaran_linea.HayTaraAplicada = 0
                    albaran_linea.Modificado = 1
                    albaran_linea.Operacion = "A"
                    albaran_linea.Usuario = "DBLogiX"

                    # Campo IdTicket come richiesto dall'utente
                    albaran_linea.IdTicket = ticket['id_ticket']

                    db.session.add(albaran_linea)

                    # Accumula totali
                    total_without_vat += line_total
                    total_vat += line_vat

            # Elabora ticket manuali
            for manual_ticket in manual_tickets:
                for ticket_line in manual_ticket['lines']:
                    line_count += 1

                    # Calcola IVA per ticket manuale
                    id_iva = ticket_line.get('id_iva', 1)
                    vat_rate = 0.04  # Default 4%
                    if id_iva == 0:
                        vat_rate = 0.00  # 0% - Esente IVA
                    elif id_iva == 1:
                        vat_rate = 0.04  # 4%
                    elif id_iva == 2:
                        vat_rate = 0.10  # 10%
                    elif id_iva == 3:
                        vat_rate = 0.22  # 22%

                    # Prezzo inserito dall'utente (già con IVA)
                    manual_price_with_vat = float(ticket_line['precio'])
                    price_without_vat = round_price_without_vat(manual_price_with_vat / (1 + vat_rate)) if vat_rate > 0 else manual_price_with_vat
                    price_with_vat = manual_price_with_vat
                    peso_value = float(ticket_line['peso'])
                    line_total = price_without_vat * peso_value
                    line_vat = line_total * vat_rate

                    # Applica sconto ticket manuale
                    manual_ticket_id_str = str(manual_ticket['id_ticket'])
                    discount_percent = float(ticket_discounts.get(manual_ticket_id_str, 0))
                    if discount_percent > 0:
                        discount_factor = 1 - (discount_percent / 100)
                        line_total = line_total * discount_factor
                        line_vat = line_vat * discount_factor

                    # Crea descrizione per ticket manuale
                    base_description = ticket_line['descripcion']
                    lotto_manuale = ticket_line.get('lotto', '').strip()
                    if lotto_manuale:
                        full_description = f"{base_description} - LOTTO: {lotto_manuale}"
                        texto_lote = lotto_manuale
                    else:
                        full_description = base_description
                        texto_lote = ""

                    # Crea AlbaranLinea per ticket manuale
                    albaran_linea = AlbaranLinea()
                    albaran_linea.IdLineaAlbaran = line_count
                    albaran_linea.IdEmpresa = albaran_cabecera.IdEmpresa
                    albaran_linea.IdTienda = albaran_cabecera.IdTienda
                    albaran_linea.IdBalanzaMaestra = albaran_cabecera.IdBalanzaMaestra
                    albaran_linea.IdBalanzaEsclava = albaran_cabecera.IdBalanzaEsclava
                    albaran_linea.IdAlbaran = albaran_cabecera.IdAlbaran
                    albaran_linea.TipoVenta = albaran_cabecera.TipoVenta

                    # Dati prodotto manuale
                    albaran_linea.IdArticulo = 999
                    albaran_linea.Descripcion = full_description[:100] if len(full_description) > 100 else full_description
                    albaran_linea.Descripcion1 = "Prodotto manuale"
                    albaran_linea.Comportamiento = ticket_line.get('comportamiento', 1)
                    albaran_linea.ComportamientoDevolucion = 0

                    # Pesi e quantità
                    albaran_linea.Peso = peso_value
                    albaran_linea.Medida2 = "kg" if ticket_line.get('comportamiento', 1) == 1 else "un"

                    # Prezzi e IVA
                    albaran_linea.Precio = price_with_vat  # Prezzo unitario CON IVA
                    albaran_linea.PrecioSinIVA = round_price_without_vat(price_without_vat)  # Arrotondamento commerciale a 2 decimali
                    albaran_linea.IdIVA = id_iva
                    albaran_linea.PorcentajeIVA = vat_rate * 100
                    albaran_linea.RecargoEquivalencia = 0.0

                    # Importi
                    albaran_linea.Importe = round(line_total + line_vat, 2)
                    albaran_linea.ImporteSinIVASinDtoL = round(line_total, 2)
                    albaran_linea.ImporteDelIVAConDtoL = round(line_vat, 2)

                    # Informazioni default per prodotti manuali
                    albaran_linea.IdClase = 1
                    albaran_linea.NombreClase = "ARTICOLI"
                    albaran_linea.IdFamilia = 1
                    albaran_linea.NombreFamilia = "MANUALE"
                    albaran_linea.IdSubFamilia = 1
                    albaran_linea.NombreSubFamilia = "MANUALE"
                    albaran_linea.IdDepartamento = 1
                    albaran_linea.NombreDepartamento = "MANUALE"
                    albaran_linea.Texto1 = "Prodotto aggiunto manualmente"
                    albaran_linea.TextoLote = texto_lote

                    # Data scadenza se presente
                    if ticket_line.get('fecha_caducidad'):
                        try:
                            from datetime import datetime
                            albaran_linea.FechaCaducidad = datetime.strptime(ticket_line['fecha_caducidad'], '%Y-%m-%d')
                        except:
                            albaran_linea.FechaCaducidad = None
                    else:
                        albaran_linea.FechaCaducidad = None

                    # Campi default
                    albaran_linea.EstadoLinea = 0
                    albaran_linea.EntradaManual = 1
                    albaran_linea.Tara = 0.0
                    albaran_linea.PrecioPorCienGramos = 0
                    albaran_linea.Descuento = discount_percent if discount_percent > 0 else 0.0
                    albaran_linea.TipoDescuento = 1
                    albaran_linea.Facturada = 0
                    albaran_linea.CantidadFacturada = 0.0
                    albaran_linea.CantidadFacturada2 = 0.0
                    albaran_linea.HayTaraAplicada = 0
                    albaran_linea.Modificado = 1
                    albaran_linea.Operacion = "A"
                    albaran_linea.Usuario = "DBLogiX"

                    # Campo IdTicket per ticket manuali
                    albaran_linea.IdTicket = manual_ticket['id_ticket']

                    db.session.add(albaran_linea)

                    # Accumula totali
                    total_without_vat += line_total
                    total_vat += line_vat

            # Aggiorna totali dell'AlbaranCabecera
            total_without_vat = round(total_without_vat, 2)
            total_vat = round(total_vat, 2)
            total_ddt_amount = total_without_vat + total_vat

            albaran_cabecera.NumLineas = line_count
            albaran_cabecera.ImporteLineas = total_ddt_amount
            albaran_cabecera.ImporteTotal = total_ddt_amount
            albaran_cabecera.ImporteTotalSinIVAConDtoL = total_without_vat
            albaran_cabecera.ImporteTotalDelIVAConDtoLConDtoTotal = total_vat
            albaran_cabecera.ImporteTotalSinIVAConDtoLConDtoTotal = total_without_vat

            # Aggiorna tabella max num albaran
            from app.models import AlbaranMaxNumAlbaran
            try:
                AlbaranMaxNumAlbaran.update_max_num_albaran(albaran_cabecera.NumAlbaran)
                current_app.logger.info(f"✅ [Fattura] Updated dat_albaran_max_num_albaran with NumAlbaran: {albaran_cabecera.NumAlbaran}")
            except Exception as e:
                current_app.logger.error(f"⚠️ [Fattura] Error updating dat_albaran_max_num_albaran: {str(e)}")

            # Commit dell'Albaran
            db.session.commit()

            current_app.logger.info(f"🎉 [Fattura] Albaran #{albaran_cabecera.IdAlbaran} created with {line_count} lines!")
            current_app.logger.info(f"📊 [Fattura] Albaran totals - Without VAT: €{total_without_vat:.2f}, VAT: €{total_vat:.2f}, Total: €{total_ddt_amount:.2f}")

        except Exception as e:
            current_app.logger.error(f"❌ [Fattura] Error creating Albaran: {str(e)}")
            import traceback
            current_app.logger.error(f"📄 [Fattura] Albaran creation traceback: {traceback.format_exc()}")
            # Non bloccare la generazione della fattura se la creazione dell'Albaran fallisce
            db.session.rollback()

        return jsonify({
            'success': True,
            'message': f'Fattura elettronica generata con successo: {xml_filename}',
            'invoice_url': invoice_url
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore nella generazione della fattura: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Errore nella generazione della fattura: {str(e)}'})

def save_ddt_pdf_automatically(ddt, cliente, empresa):
    """Salva automaticamente il PDF del DDT nella cartella DDT organizzata per anni"""
    import os
    
    try:
        # Genera il PDF
        pdf_data = generate_ddt_pdf(ddt, cliente, empresa)
        
        # Ottieni l'anno corrente dalla data del DDT
        ddt_year = ddt.Fecha.year if ddt.Fecha else datetime.now().year
        
        # Crea la struttura delle cartelle: DDT/{anno}
        ddt_dir = os.path.join(current_app.root_path, 'DDT', str(ddt_year))
        os.makedirs(ddt_dir, exist_ok=True)
        
        # Genera il nome del file seguendo il pattern: DDT_{ID}_{NomeCliente}.pdf
        client_name_clean = "".join(c for c in (cliente.Nombre or 'Cliente_Sconosciuto') if c.isalnum() or c in (' ', '-', '_')).replace(' ', '_')
        pdf_filename = f"DDT_{ddt.IdAlbaran}_{client_name_clean}.pdf"
        pdf_path = os.path.join(ddt_dir, pdf_filename)
        
        # Salva il PDF
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_data)
        
        current_app.logger.info(f"📄 PDF salvato: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore nel salvataggio automatico PDF DDT: {str(e)}")
        raise e

@ddt_bp.route('/<int:ddt_id>', methods=['GET'])
@login_required
def detail(ddt_id):
    """Show detailed information about a DDT"""
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    
    # Recupera il cliente associato al DDT
    cliente = Client.query.get(ddt.IdCliente)
    
    # Recupera l'azienda associata al DDT
    empresa = Company.query.get(ddt.IdEmpresa)
    
    # Get lines from this DDT
    lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
    
    # Calcola i totali per il template
    total_without_vat = 0
    total_vat = 0
    total = 0
    
    for line in lines:
        total_without_vat += float(line.ImporteSinIVASinDtoL or 0)
        total_vat += float(line.ImporteDelIVAConDtoL or 0)
    
    total = total_without_vat + total_vat
    
    # Creazione dell'oggetto totals
    totals = {
        'total_without_vat': total_without_vat,
        'total_vat': total_vat,
        'total': total
    }
    
    # Raggruppa le linee per ticket per una visualizzazione migliore
    from collections import defaultdict
    lines_by_ticket = defaultdict(list)
    for line in lines:
        # Since IdTicket is no longer available, group all lines together
        ticket_id = 'Tutte le righe'
        lines_by_ticket[ticket_id].append(line)
    
    # Print per debug
    for ticket_id, ticket_lines in lines_by_ticket.items():
        print(f"Ticket {ticket_id} ha {len(ticket_lines)} linee")
    
    # Calculate the number of total items
    total_items = len(lines)
    
    # Get current datetime for print version
    now = datetime.now()
    
    # Check if it's a print request
    is_print = request.args.get('print') == 'true'
    
    # Render template with both options (linee in sequenza o raggruppate)
    return render_template('ddt/detail.html', 
                          ddt=ddt, 
                          cliente=cliente,
                          empresa=empresa,
                          lines=lines,
                          lines_by_ticket=lines_by_ticket,
                          totals=totals,
                          total_items=total_items,
                          now=now,
                          is_print=is_print)

@ddt_bp.route('/<int:ddt_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(ddt_id):
    """Delete a DDT and all its lines"""
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    
    try:
        # Start transaction
        current_app.logger.info(f"🗑️  Eliminazione DDT #{ddt_id} iniziata")
        
        # Verifica se questo DDT era stato generato da un task
        from app.models import Task
        task_with_ddt = Task.query.filter_by(ddt_id=ddt_id).first()
        
        # Recupera tutte le linee del DDT
        albaran_lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
        
        # Note: IdTicket field has been removed from albaran lines
        # Ticket reset functionality is now disabled since we can't identify associated tickets
        current_app.logger.info(f"📋 DDT #{ddt_id}: {len(albaran_lines) if albaran_lines else 0} righe totali")
        
        # Reset stato dei ticket - DISABLED (IdTicket field no longer available)
        reset_tickets_count = 0
        
        # Se il DDT era generato da un task, aggiorna lo stato del task
        if task_with_ddt:
            current_app.logger.info(f"📝 DDT #{ddt_id} era associato al Task #{task_with_ddt.task_number}")
            
            # Reset dello stato del task
            task_with_ddt.ddt_generated = False
            task_with_ddt.ddt_id = None
            task_with_ddt.status = 'completed'  # Mantiene completed ma senza DDT
            
            # Aggiorna il progresso del task
            task_with_ddt.update_progress()
            
            current_app.logger.info(f"✅ Task #{task_with_ddt.task_number} aggiornato: DDT rimosso, stato reset")
            
            flash_message = f'DDT #{ddt_id} eliminato. Task #{task_with_ddt.task_number} aggiornato e {reset_tickets_count} ticket reimpostati.'
        else:
            flash_message = f'DDT #{ddt_id} eliminato e {reset_tickets_count} ticket reimpostati come pendenti.'
        
        # Elimina il DDT (le linee verranno eliminate automaticamente per cascade)
        db.session.delete(ddt)
        db.session.commit()
        
        current_app.logger.info(f"🎉 DDT #{ddt_id} eliminato con successo")
        
        flash(flash_message, 'success')
        return redirect(url_for('ddt.index'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore nell'eliminazione DDT #{ddt_id}: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        flash(f'Errore durante eliminazione: {str(e)}', 'danger')
        return redirect(url_for('ddt.detail', ddt_id=ddt_id))

@ddt_bp.route('/api/clients/search')
@login_required
def client_search():
    """API endpoint for searching clients (autocomplete)"""
    term = request.args.get('term', '')
    
    if not term or len(term) < 3:
        return jsonify([])
    
    # Search for clients
    clients = Client.query.filter(Client.Nombre.ilike(f'%{term}%')).order_by(Client.Nombre).limit(20).all()
    
    # Format results for Select2
    results = [{
        'id': client.IdCliente,
        'text': f"{client.Nombre} ({client.IdCliente})",
        'nombre': client.Nombre,
        'direccion': client.Direccion or '',
        'dni': client.DNI or ''
    } for client in clients]
    
    # Debug output to console
    print(f"Client search for '{term}' returned {len(results)} results")
    
    return jsonify(results)

@ddt_bp.route('/api/clients/all')
@login_required
def get_all_clients():
    """API endpoint for getting all clients"""
    try:
        # Get all clients ordered by name
        clients = Client.query.order_by(Client.Nombre).all()
        
        # Format results for the client grid
        results = [{
            'id': client.IdCliente,
            'nombre': client.Nombre or 'Nome non disponibile',
            'direccion': client.Direccion or '',
            'dni': client.DNI or '',
            'telefono1': client.Telefono1 or '',
            'email': client.Email or '',
            'poblacion': client.Poblacion or '',
            'cod_postal': client.CodPostal or ''
        } for client in clients]
        
        print(f"Loaded {len(results)} clients for grid display")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error loading clients: {str(e)}")
        return jsonify([]), 500

@ddt_bp.route('/<int:ddt_id>/export', methods=['POST', 'GET'])
@login_required
def export(ddt_id):
    """Export DDT as PDF"""
    # Per richieste GET, creiamo un form fittizio
    if request.method == 'GET':
        form = DDTExportForm(format='pdf')
    else:
        form = DDTExportForm()
        
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    
    # Per richieste GET, validiamo automaticamente
    if request.method == 'GET' or form.validate_on_submit():
        # Generate PDF 
        try:
            # Load client and company info
            cliente = Client.query.get(ddt.IdCliente)
            empresa = Company.query.get(ddt.IdEmpresa)
            
            # Generate PDF
            pdf_data = generate_ddt_pdf(ddt, cliente, empresa)
            
            return send_file(
                io.BytesIO(pdf_data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'DDT_{ddt_id}.pdf'
            )
        
        except Exception as e:
            flash(f'Errore durante l\'esportazione del DDT: {str(e)}', 'danger')
    
    return redirect(url_for('ddt.detail', ddt_id=ddt_id))

def generate_ddt_pdf(ddt, cliente, empresa):
    """Generate a stunning, professional PDF document for the DDT with exceptional layout"""
    buffer = io.BytesIO()
    
    # Create the PDF document with optimized margins
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=80*mm,  # Slightly increased for better header
        bottomMargin=40*mm,  # Optimized for footer with signatures
        title=f"DDT #{ddt.IdAlbaran}",
        author=empresa.NombreEmpresa if empresa else "DBLogiX"
    )
    
    # Original sophisticated color palette - restored
    primary_color = colors.HexColor('#1a365d')      # Deep professional blue
    secondary_color = colors.HexColor('#2d5a7b')    # Lighter blue
    accent_color = colors.HexColor('#e53e3e')       # Elegant red accent
    success_color = colors.HexColor('#38a169')      # Success green
    text_primary = colors.HexColor('#2d3748')       # Primary text
    text_secondary = colors.HexColor('#4a5568')     # Secondary text
    text_muted = colors.HexColor('#718096')         # Muted text
    border_light = colors.HexColor('#e2e8f0')       # Light borders
    background_light = colors.HexColor('#f7fafc')   # Light background
    background_accent = colors.HexColor('#ebf8ff')  # Accent background
    white = colors.white
    
    # Premium typography system with improved sizes
    styles = getSampleStyleSheet()
    
    # Document Title - More prominent
    styles.add(ParagraphStyle(
        name='DocumentTitle',
        parent=styles['Normal'],
        fontSize=22,
        alignment=1,  # center aligned
        textColor=white,
        spaceAfter=2*mm,
        fontName='Helvetica-Bold',
        leading=24
    ))
    
    # Document Subtitle - Refined
    styles.add(ParagraphStyle(
        name='DocumentSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=1,  # center aligned
        textColor=white,
        spaceAfter=1*mm,
        fontName='Helvetica',
        leading=13
    ))
    
    # Section Headers - Premium styling
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        spaceAfter=2*mm,
        spaceBefore=1*mm,
        leading=12
    ))
    
    # Company Information - Professional
    styles.add(ParagraphStyle(
        name='CompanyInfo',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_primary,
        fontName='Helvetica',
        leading=12,  # Increased line spacing
        spaceAfter=1*mm  # More space between lines
    ))
    
    # Company Name - Distinguished
    styles.add(ParagraphStyle(
        name='CompanyName',
        parent=styles['Normal'],
        fontSize=10,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        spaceAfter=2*mm,  # More space after company name
        leading=12
    ))
    
    # Table Headers - Premium design
    styles.add(ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=8,
        alignment=1,
        textColor=white,
        fontName='Helvetica-Bold',
        leading=10
    ))
    
    # Table Cells - Clean and readable
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_primary,
        fontName='Helvetica',
        alignment=1,
        leading=10
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellLeft',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_primary,
        fontName='Helvetica',
        alignment=0,
        leading=10
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellRight',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_primary,
        fontName='Helvetica',
        alignment=2,
        leading=10
    ))
    
    # Transport Information - Elegant
    styles.add(ParagraphStyle(
        name='TransportInfo',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_primary,
        fontName='Helvetica',
        leading=10
    ))
    
    # Summary Style - More prominent
    styles.add(ParagraphStyle(
        name='SummaryLabel',
        parent=styles['Normal'],
        fontSize=9,
        textColor=text_primary,
        fontName='Helvetica-Bold',
        alignment=2,
        leading=11
    ))
    
    styles.add(ParagraphStyle(
        name='SummaryValue',
        parent=styles['Normal'],
        fontSize=10,
        textColor=primary_color,
        fontName='Helvetica-Bold',
        alignment=2,
        leading=12
    ))
    
    # Collect all elements
    elements = []
    
    # === PREMIUM PRODUCTS TABLE ===
    products_data = []
    
    # Sophisticated table header
    header_style = [
        Paragraph("<b>COD.</b>", styles['TableHeader']),
        Paragraph("<b>DESCRIZIONE ARTICOLO</b>", styles['TableHeader']),
        Paragraph("<b>U.M.</b>", styles['TableHeader']),
        Paragraph("<b>QUANTITÀ</b>", styles['TableHeader']),
        Paragraph("<b>PREZZO</b>", styles['TableHeader']),
        Paragraph("<b>SCONTO</b>", styles['TableHeader']),
        Paragraph("<b>IVA</b>", styles['TableHeader']),
        Paragraph("<b>IMPORTO</b>", styles['TableHeader']),
    ]
    products_data.append(header_style)
    
    # Get product lines
    lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
    
    total_amount = 0
    total_quantity = 0
    subtotal_without_vat = 0
    total_vat = 0
    
    for line in lines:
        # Extract data with safe defaults
        code = str(line.IdArticulo or '')
        description = line.Descripcion or 'N/A'
        
        # Determine correct unit based on product behavior
        comportamiento = getattr(line, 'Comportamiento', 0)
        if comportamiento == 1:  # Weight-based product
            unit = 'kg'
        else:  # Unit-based product
            unit = 'un'
        
        quantity = float(line.Peso or 0)
        price = float(line.PrecioSinIVA or 0)
        discount_percent = float(line.Descuento or 0)
        vat_rate = float(line.PorcentajeIVA or 0)
        line_total_without_vat = float(line.ImporteSinIVASinDtoL or 0)
        line_vat = float(line.ImporteDelIVAConDtoL or 0)
        line_total = line_total_without_vat + line_vat
        
        total_amount += line_total
        total_quantity += quantity
        subtotal_without_vat += line_total_without_vat
        total_vat += line_vat
        
        # Format discount display
        discount_display = f"{discount_percent:.0f}%" if discount_percent > 0 else "-"
        
        # Format quantity based on product type
        if comportamiento == 1:  # Weight-based product
            quantity_display = f"{quantity:.3f}"
        else:  # Unit-based product
            quantity_display = f"{quantity:.0f}"
        
        # Create elegant table rows
        products_data.append([
            Paragraph(code if code != '999' else '', styles['TableCell']),
            Paragraph(description, styles['TableCellLeft']),
            Paragraph(unit, styles['TableCell']),
            Paragraph(quantity_display, styles['TableCellRight']),
            Paragraph(f"€ {price:.2f}", styles['TableCellRight']),
            Paragraph(discount_display, styles['TableCell']),
            Paragraph(f"{vat_rate:.0f}%", styles['TableCell']),
            Paragraph(f"<b>€ {line_total:.2f}</b>", styles['TableCellRight']),
        ])
    
    # Create sophisticated products table with updated column widths
    col_widths = [16*mm, 78*mm, 11*mm, 18*mm, 18*mm, 12*mm, 11*mm, 20*mm]
    products_table = Table(products_data, colWidths=col_widths, repeatRows=1)
    
    # Apply modern table styling
    table_style = [
        # Header styling - elegant gradient
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        
        # Data rows - clean styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),   # Code column
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Description column
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),   # Unit column
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),    # Quantity column
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),    # Price column
        ('ALIGN', (5, 1), (5, -1), 'CENTER'),   # Discount column
        ('ALIGN', (6, 1), (6, -1), 'CENTER'),   # VAT column
        ('ALIGN', (7, 1), (7, -1), 'RIGHT'),    # Total column
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 1), (-1, -1), 4),
        ('RIGHTPADDING', (0, 1), (-1, -1), 4),
        
        # Modern borders
        ('LINEBELOW', (0, 0), (-1, 0), 1, primary_color),
        ('GRID', (0, 1), (-1, -1), 0.5, border_light),
        ('LINEBEFORE', (0, 0), (0, -1), 1, primary_color),
        ('LINEAFTER', (-1, 0), (-1, -1), 1, primary_color),
        ('LINEBELOW', (0, -1), (-1, -1), 1, primary_color),
    ]
    
    # Add subtle alternating row colors
    for i in range(1, len(products_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), background_light))
    
    products_table.setStyle(TableStyle(table_style))
    elements.append(products_table)
    elements.append(Spacer(1, 8*mm))
    
    # === DISCOUNT SUMMARY (if any discounts applied) ===
    total_discount_amount = 0
    lines_with_discount = 0
    
    # Calculate total discount savings
    for line in lines:
        discount_percent = float(line.Descuento or 0)
        if discount_percent > 0:
            lines_with_discount += 1
            price = float(line.PrecioSinIVA or 0)
            quantity = float(line.Peso or 0)
            
            # Calculate original amount (without discount)
            original_subtotal = price * quantity
            # Apply correct rounding to original subtotal
            original_subtotal = round_product_amount(original_subtotal)
            
            # Calculate discount on subtotal (before VAT) - FIXED: Only show discount on base amount
            discount_amount_subtotal = original_subtotal * (discount_percent / 100)
            discount_amount_subtotal = round_product_amount(discount_amount_subtotal)
            
            # Only add the discount on the subtotal (excluding VAT on discount)
            # This is the correct way to show discounts in commercial documents
            total_discount_amount += discount_amount_subtotal
    
    # Add discount summary if there are discounts
    if total_discount_amount > 0:
        discount_summary_data = [
            [
                Paragraph(f"<b>Sconti applicati su {lines_with_discount} articoli</b>", styles['SummaryLabel']),
                Paragraph(f"<b>- € {total_discount_amount:.2f}</b>", ParagraphStyle(
                    name='DiscountValue',
                    parent=styles['SummaryValue'],
                    textColor=colors.HexColor('#e53e3e')  # Red color for discount
                ))
            ]
        ]
        
        discount_summary_table = Table(discount_summary_data, colWidths=[40*mm, 30*mm])
        discount_summary_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff5f5')),  # Light red background
            ('GRID', (0, 0), (-1, -1), 0.5, border_light),
            ('ROUNDEDCORNERS', [3, 3, 3, 3]),
        ]))
        
        # Right align the discount summary
        discount_summary_container = Table([[discount_summary_table]], colWidths=[doc.width])
        discount_summary_container.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (0, 0), 'TOP'),
        ]))
        
        elements.append(discount_summary_container)
        elements.append(Spacer(1, 5*mm))
    
    # === IMPROVED FINANCIAL SUMMARY ===
    # Create a more prominent summary box
    summary_data = [
        [
            Paragraph("<b>Subtotale (esclusa IVA)</b>", styles['SummaryLabel']),
            Paragraph(f"<b>€ {subtotal_without_vat:.2f}</b>", styles['SummaryValue'])
        ],
        [
            Paragraph("<b>Totale IVA</b>", styles['SummaryLabel']),
            Paragraph(f"<b>€ {total_vat:.2f}</b>", styles['SummaryValue'])
        ],
        [
            Paragraph("<b>TOTALE GENERALE</b>", styles['SummaryLabel']),
            Paragraph(f"<b>€ {total_amount:.2f}</b>", styles['SummaryValue'])
        ]
    ]
    
    summary_table = Table(summary_data, colWidths=[40*mm, 30*mm])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 1), background_light),
        ('BACKGROUND', (0, 2), (-1, 2), background_accent),
        ('LINEABOVE', (0, 2), (-1, 2), 1, success_color),
        ('LINEBELOW', (0, 2), (-1, 2), 1, success_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_light),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
    ]))
    
    # Right align the summary
    summary_container = Table([[summary_table]], colWidths=[doc.width])
    summary_container.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
    ]))
    
    elements.append(summary_container)
    elements.append(Spacer(1, 10*mm))
    
    # === COMPACT TRANSPORT CONDITIONS ===
    # Calculate number of packages (colli) based on system configuration
    articles_per_package = SystemConfig.get_config('articles_per_package', 5)
    
    # Count articles excluding "trasporto" items
    total_articles = 0
    for line in lines:
        description = (line.Descripcion or '').lower()
        if 'trasporto' not in description:
            total_articles += 1
    
    # Calculate number of packages
    num_packages = max(1, (total_articles + articles_per_package - 1) // articles_per_package)  # Round up division
    
    transport_data = [
        [
            Paragraph("<b>Causale trasporto:</b> Vendita", styles['TransportInfo']),
            Paragraph("<b>Trasporto a cura:</b> Mittente", styles['TransportInfo'])
        ],
        [
            Paragraph("<b>Aspetto esteriore beni:</b> Confezioni integre", styles['TransportInfo']),
            Paragraph(f"<b>Numero colli:</b> {num_packages}", styles['TransportInfo'])
        ],
        [
            Paragraph("<b>Data e ora partenza:</b> _______________", styles['TransportInfo']),
            Paragraph("<b>Data e ora arrivo:</b> _______________", styles['TransportInfo'])
        ]
    ]
    
    transport_table = Table(transport_data, colWidths=[doc.width/2 - 5*mm, doc.width/2 - 5*mm])
    transport_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BACKGROUND', (0, 0), (-1, -1), background_light),
        ('GRID', (0, 0), (-1, -1), 0.5, border_light),
        ('ROUNDEDCORNERS', [2, 2, 2, 2]),
    ]))
    
    elements.append(transport_table)
    
    # === PREMIUM HEADER AND FOOTER FUNCTIONS ===
    def draw_premium_header_footer(canvas, doc):
        canvas.saveState()
        
        # === CLEAN HEADER WITH WHITE BACKGROUND ===
        header_height = 80*mm
        
        # White background for entire document
        canvas.setFillColor(white)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        
        # === LOGO AND TITLE SECTION ===
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'uploads', 'logos', 'LogoDDT.png')
        logo_width = 50*mm
        logo_height = 25*mm
        
        if os.path.exists(logo_path):
            try:
                canvas.drawImage(logo_path, doc.leftMargin, A4[1] - 30*mm, 
                               width=logo_width, height=logo_height, mask='auto')
            except:
                # Fallback elegant company name
                canvas.setFont('Helvetica-Bold', 20)
                canvas.setFillColor(primary_color)
                canvas.drawString(doc.leftMargin, A4[1] - 20*mm, 
                                empresa.NombreEmpresa if empresa else "DBLogiX")
        else:
            # Elegant company name design
            canvas.setFont('Helvetica-Bold', 20)
            canvas.setFillColor(primary_color)
            canvas.drawString(doc.leftMargin, A4[1] - 20*mm, 
                            empresa.NombreEmpresa if empresa else "DBLogiX")
        
        # Document title section
        title_width = 95*mm  # Slightly increased width
        title_height = 25*mm
        title_x = A4[0] - doc.rightMargin - title_width
        title_y = A4[1] - 30*mm
        
        # Create background for title
        canvas.setFillColor(primary_color)
        canvas.roundRect(title_x, title_y, title_width, title_height, 4*mm, fill=1, stroke=0)
        
        # Document title with smaller font to fit better
        canvas.setFont('Helvetica-Bold', 16)  # Reduced from 18 to 16
        canvas.setFillColor(white)
        title_text = "DOCUMENTO DI TRASPORTO"
        text_width = canvas.stringWidth(title_text, 'Helvetica-Bold', 16)
        canvas.drawString(title_x + (title_width - text_width)/2, title_y + 12*mm, title_text)
        
        # Document number and date
        canvas.setFont('Helvetica', 10)
        subtitle_text = f"N° {ddt.IdAlbaran} del {ddt.Fecha.strftime('%d/%m/%Y') if ddt.Fecha else 'N/A'}"
        subtitle_width = canvas.stringWidth(subtitle_text, 'Helvetica', 10)
        canvas.drawString(title_x + (title_width - subtitle_width)/2, title_y + 6*mm, subtitle_text)
        
        # === CLEAN COMPANY AND CLIENT BOXES (NO BORDERS) ===
        box_y = A4[1] - 75*mm
        box_height = 38*mm  # Increased height for more space
        
        # Company information (left) - no borders, more spacing
        if empresa:
            company_box_width = 80*mm
            company_x = doc.leftMargin
            
            # Company header
            canvas.setFont('Helvetica-Bold', 10)
            canvas.setFillColor(primary_color)
            canvas.drawString(company_x, box_y + box_height - 8*mm, "MITTENTE")
            
            # Company details with more spacing
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(text_primary)
            y_offset = box_y + box_height - 16*mm
            canvas.drawString(company_x, y_offset, empresa.NombreEmpresa)
            
            canvas.setFont('Helvetica', 8)
            y_offset -= 10  # Increased spacing between lines
            if empresa.Direccion:
                canvas.drawString(company_x, y_offset, empresa.Direccion)
                y_offset -= 10
            city_postal = f"{empresa.CodPostal or ''} {empresa.Poblacion or ''}".strip()
            if city_postal:
                canvas.drawString(company_x, y_offset, city_postal)
                y_offset -= 10
            if empresa.CIF_VAT:
                canvas.drawString(company_x, y_offset, f"P.IVA: {empresa.CIF_VAT}")
                y_offset -= 10
            if empresa.Telefono1:
                canvas.drawString(company_x, y_offset, f"Tel: {empresa.Telefono1}")
        
        # Client information (right) - no borders, more spacing
        if cliente:
            client_box_width = 80*mm
            client_x = A4[0] - doc.rightMargin - client_box_width
            
            # Client header
            canvas.setFont('Helvetica-Bold', 10)
            canvas.setFillColor(primary_color)
            canvas.drawString(client_x, box_y + box_height - 8*mm, "DESTINATARIO")
            
            # Client details with more spacing
            canvas.setFont('Helvetica-Bold', 9)
            canvas.setFillColor(text_primary)
            y_offset = box_y + box_height - 16*mm
            canvas.drawString(client_x, y_offset, cliente.Nombre)
            
            canvas.setFont('Helvetica', 8)
            y_offset -= 10  # Increased spacing between lines
            if cliente.Direccion:
                canvas.drawString(client_x, y_offset, cliente.Direccion)
                y_offset -= 10
            city_postal = f"{cliente.CodPostal or ''} {cliente.Poblacion or ''}".strip()
            if city_postal:
                canvas.drawString(client_x, y_offset, city_postal)
                y_offset -= 10
            if cliente.DNI:
                canvas.drawString(client_x, y_offset, f"P.IVA/CF: {cliente.DNI}")
                y_offset -= 10
            if cliente.Telefono1:
                canvas.drawString(client_x, y_offset, f"Tel: {cliente.Telefono1}")
        
        # === CLEAN FOOTER WITH SIGNATURES (NO SEPARATOR LINES) ===
        footer_height = 40*mm
        
        # === ELEGANT SIGNATURE FIELDS ===
        signature_y = 25*mm
        signature_width = 70*mm
        
        # Left signature (VETTORE)
        left_sig_x = doc.leftMargin + 10*mm
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(primary_color)
        canvas.drawString(left_sig_x, signature_y + 8*mm, "FIRMA DEL VETTORE")
        
        # Elegant signature box for vettore
        canvas.setStrokeColor(border_light)
        canvas.setLineWidth(1)
        canvas.rect(left_sig_x, signature_y, signature_width, 6*mm, fill=0, stroke=1)
        
        # Right signature (DESTINATARIO)
        right_sig_x = A4[0] - doc.rightMargin - signature_width - 10*mm
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(primary_color)
        canvas.drawString(right_sig_x, signature_y + 8*mm, "FIRMA DEL DESTINATARIO")
        
        # Elegant signature box for destinatario
        canvas.setStrokeColor(border_light)
        canvas.setLineWidth(1)
        canvas.rect(right_sig_x, signature_y, signature_width, 6*mm, fill=0, stroke=1)
        
        # Document info footer
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(text_muted)
        footer_text = f"DDT #{ddt.IdAlbaran} • Generato il {datetime.now().strftime('%d/%m/%Y alle ore %H:%M')} • DBLogiX Professional"
        canvas.drawString(doc.leftMargin, 8*mm, footer_text)
        
        # Page number
        page_num = canvas.getPageNumber()
        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(primary_color)
        page_text = f"Pagina {page_num}"
        page_width = canvas.stringWidth(page_text, 'Helvetica-Bold', 8)
        canvas.drawString(A4[0] - doc.rightMargin - page_width, 8*mm, page_text)
        
        canvas.restoreState()
    
    # Build the premium document
    doc.build(elements, onFirstPage=draw_premium_header_footer, onLaterPages=draw_premium_header_footer)
    
    # Get the PDF content
    pdf_content = buffer.getvalue()
    buffer.close()
    
    return pdf_content

# Utility function for calculating VAT rate from IdIva
def get_vat_rate(id_iva):
    if id_iva == 1:
        return 0.04  # 4%
    elif id_iva == 2:
        return 0.10  # 10%
    elif id_iva == 3:
        return 0.22  # 22%
    else:
        return 0  # Default 

@ddt_bp.route('/ticket_details/<int:ticket_id>/<int:empresa_id>', methods=['GET'])
@login_required
@cross_origin()
def ticket_details(ticket_id, empresa_id):
    """API endpoint to get ticket details for the modal view"""
    try:
        print(f"Fetching ticket details for ticket_id={ticket_id}, empresa_id={empresa_id}")
        
        ticket = TicketHeader.query.filter_by(IdTicket=ticket_id, IdEmpresa=empresa_id).first()
        
        if not ticket:
            print(f"Ticket not found: ticket_id={ticket_id}, empresa_id={empresa_id}")
            return jsonify({"success": False, "error": "Ticket non trovato"})
        
        # Get unique ticket lines to avoid duplicates
        lines_query = """
            SELECT DISTINCT 
                tl.IdArticulo,
                tl.Descripcion,
                tl.Peso,
                tl.comportamiento,
                tl.Precio
            FROM dat_ticket_linea tl
            LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
            WHERE tl.IdTicket = :ticket_id
            ORDER BY tl.IdArticulo
        """
        
        lines_result = db.session.execute(text(lines_query), {'ticket_id': ticket_id})
        print(f"Found ticket lines for ticket {ticket_id}")
        
        # Format response data
        ticket_data = {
            "success": True,
            "ticket": {
                "id": ticket.IdTicket,
                "date": ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else 'N/A',
                "num_lines": 0  # Will be calculated
            },
            "items": []
        }
        
        # Add product details for each unique line
        unique_products = {}
        for row in lines_result:
            try:
                id_articulo = row[0]
                descripcion = row[1]
                peso = row[2]
                comportamiento = row[3] or 0
                precio = row[4]
                
                # Skip if we already processed this article
                if id_articulo in unique_products:
                    print(f"Skipping duplicate IdArticulo {id_articulo} in ticket {ticket_id}")
                    continue
                
                # Mark this article as processed
                unique_products[id_articulo] = True
                
                ticket_data["items"].append({
                    "id": id_articulo,
                    "description": descripcion or 'Descrizione non disponibile',
                    "quantity": f"{peso} {'unità' if comportamiento == 0 else 'Kg'}" if peso is not None else "N/A",
                    "price": f"€ {precio}" if precio is not None else "N/A"
                })
            except Exception as e:
                print(f"Error processing line with IdArticulo {id_articulo}: {str(e)}")
                continue
        
        # Update the actual number of unique lines
        ticket_data["ticket"]["num_lines"] = len(ticket_data["items"])
        
        print(f"Returning ticket data with {len(ticket_data['items'])} unique items")
        return jsonify(ticket_data)
    
    except Exception as e:
        print(f"Error in ticket_details: {str(e)}")
        return jsonify({"success": False, "error": f"Errore durante il caricamento del ticket: {str(e)}"})

@ddt_bp.route('/search_tickets', methods=['POST'])
@login_required
def search_tickets():
    """API endpoint to search for tickets by client ID"""
    client_id = request.form.get('client_id')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    
    if not client_id:
        return jsonify({"success": False, "error": "Client ID is required"})
    
    if not from_date or not to_date:
        return jsonify({"success": False, "error": "Date range is required"})
    
    try:
        from_date = datetime.strptime(from_date, '%Y-%m-%d')
        to_date = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)  # Include full day
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format"})
    
    # Query for tickets for this client not already processed
    tickets = TicketHeader.query.filter(
        TicketHeader.Fecha.between(from_date, to_date),
        TicketHeader.IdCliente == client_id,
        TicketHeader.Enviado == 0  # Solo ticket pendenti
    ).order_by(TicketHeader.Fecha.desc()).all()
    
    # Format response
    result = []
    for ticket in tickets:
        # Get ticket lines
        lines = TicketLine.query.filter_by(IdTicket=ticket.IdTicket).all()
        
        ticket_lines = []
        for line in lines:
            product = Product.query.get(line.IdArticulo)
            if not product:
                continue
                
            ticket_lines.append({
                "id": line.IdLinea,
                "descripcion": product.Descripcion,
                "peso": float(line.Peso) if line.Peso is not None else 0,
                "comportamiento": line.comportamiento,
                "precio": float(line.Precio) if line.Precio is not None else 0
            })
        
        result.append({
            "id": ticket.IdTicket,
            "id_empresa": ticket.IdEmpresa,
            "id_tienda": ticket.IdTienda,
            "id_balanza_maestra": ticket.IdBalanzaMaestra,
            "id_balanza_esclava": ticket.IdBalanzaEsclava,
            "tipo_venta": ticket.TipoVenta,
            "num_ticket": ticket.NumTicket,
            "fecha": ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else 'N/A',
            "lines": ticket_lines
        })
    
    return jsonify(result)

@ddt_bp.route('/inittest', methods=['GET'])
def inittest():
    """Initialize test tables and data - only for development"""
    
    # Manualmente aggiungiamo la colonna IdTicket alla tabella dat_albaran_linea se non esiste già
    try:
        # Verifichiamo se la colonna esiste già
        sql_check = """
        SELECT COUNT(*) AS column_exists 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'dat_albaran_linea' 
        AND COLUMN_NAME = 'IdTicket';
        """
        
        result = db.session.execute(text(sql_check)).fetchone()
        column_exists = result[0]
        
        if column_exists == 0:
            # La colonna non esiste, la aggiungiamo
            sql_add_column = """
            ALTER TABLE dat_albaran_linea 
            ADD COLUMN IdTicket BIGINT NULL AFTER EstadoLinea;
            """
            db.session.execute(text(sql_add_column))
            db.session.commit()
            return jsonify({"success": True, "message": "Colonna IdTicket aggiunta correttamente."})
        else:
            return jsonify({"success": True, "message": "Colonna IdTicket già esistente."})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}) 

@ddt_bp.route('/api/preview/add_ticket', methods=['POST'])
@login_required
def api_add_ticket_to_preview():
    """API to add a ticket to DDT preview"""
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    empresa_id = data.get('empresa_id', 1)
    cliente_id = data.get('cliente_id')  # Aggiunto per utilizzare i prezzi del listino
    
    if not ticket_id:
        return jsonify({'success': False, 'message': 'ID ticket mancante'})
    
    if not cliente_id:
        return jsonify({'success': False, 'message': 'ID cliente mancante'})
    
    # Get ticket info
    ticket = TicketHeader.query.filter_by(
        IdTicket=ticket_id,
        IdEmpresa=empresa_id
    ).first()
    
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket non trovato'})
    
    if ticket.Enviado != 0:
        return jsonify({'success': False, 'message': 'Ticket già processato'})
    
    # Get ticket lines with their real IDs - IMPORTANTE: Includiamo sempre IdLineaTicket
    lines_query = """
        SELECT 
            tl.IdLineaTicket,
            tl.IdArticulo,
            tl.Descripcion,
            tl.Peso,
            tl.FechaCaducidad,
            tl.Precio,
            tl.comportamiento
        FROM dat_ticket_linea tl
        LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
        WHERE tl.IdTicket = :ticket_id
        ORDER BY tl.IdLineaTicket
    """
    
    lines_result = db.session.execute(text(lines_query), {'ticket_id': ticket_id})
    
    ticket_total = 0
    ticket_lines_data = []
    unique_products = {}
    
    for row in lines_result:
        id_linea_ticket = row[0]  # IMPORTANTE: ID reale della linea dal database
        id_articulo = row[1]
        descripcion = row[2]
        peso = float(row[3] or 0)
        fecha_caducidad = row[4]
        precio = float(row[5] or 0)
        comportamiento = row[6] or 0
        
        # 🔧 CORREZIONE DOPPIO CALCOLO IVA: Usa la funzione esistente che gestisce correttamente i prezzi
        from app.models import Product
        product = Product.query.get(id_articulo)
        id_iva = product.IdIva if product else 1
        
        # Usa la funzione corretta che sa gestire prezzi GIÀ CON IVA
        precio_con_iva, precio_senza_iva, vat_rate = calculate_ticket_price_with_vat(
            cliente_id, id_articulo, precio, id_iva
        )
        
        current_app.logger.info(f"🔍 API Add Ticket - Articolo {id_articulo}: Originale=€{precio:.3f}, Con IVA=€{precio_con_iva:.3f}, Senza IVA=€{precio_senza_iva:.3f}")
        
        line_amount = peso * precio_senza_iva  # Usa prezzo senza IVA per i calcoli
        line_amount_with_vat = peso * precio_con_iva  # 🔧 AGGIUNTO: Calcolo con IVA per la barra verde
        ticket_total += line_amount
        # Nota: ticket_total_with_vat verrà calcolato nel frontend dalla risposta JSON
        
        ticket_lines_data.append({
            'id_linea_ticket': id_linea_ticket,  # IMPORTANTE: Includi sempre l'ID reale della linea
            'id_articulo': id_articulo,
            'descripcion': descripcion,
            'peso': peso,
            'precio': precio_con_iva,  # Mostra prezzo CON IVA nella preview
            'precio_senza_iva': precio_senza_iva,  # Prezzo senza IVA per calcoli interni
            'precio_con_iva': precio_con_iva,  # Keep original price for reference (compatibilità)
            'importe': line_amount,
            'importe_con_iva': line_amount_with_vat,  # 🔧 AGGIUNTO: Importo con IVA per la barra verde
            'comportamiento': comportamiento,
            'vat_rate': vat_rate,
            'porcentaje_iva': int(vat_rate * 100),  # Percentuale IVA per il frontend
            'fecha_caducidad': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None
        })
        
        current_app.logger.info(f"✅ Linea {id_linea_ticket} aggiunta per ticket {ticket_id}: {descripcion}")
    
    return jsonify({
        'success': True,
        'ticket': {
            'id_ticket': ticket.IdTicket,
            'num_ticket': ticket.NumTicket,
            'fecha': ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else '',
            'lines': ticket_lines_data,
            'total': ticket_total,
            'id_empresa': ticket.IdEmpresa,
            'id_tienda': ticket.IdTienda or 1,
            'id_balanza_maestra': ticket.IdBalanzaMaestra or 1,
            'id_balanza_esclava': ticket.IdBalanzaEsclava or -1,
            'tipo_venta': ticket.TipoVenta or 2
        }
    })

@ddt_bp.route('/api/preview/remove_ticket', methods=['POST'])
@login_required
def api_remove_ticket_from_preview():
    """API to remove a ticket from DDT preview and optionally from task"""
    data = request.get_json()
    ticket_id = data.get('ticket_id')
    from_task = data.get('from_task', False)  # Indica se viene da un task
    task_id = data.get('task_id')  # ID della task specifica (se disponibile)
    
    if not ticket_id:
        return jsonify({'success': False, 'message': 'ID ticket mancante'})
    
    try:
        # Trova il ticket e resetta il suo stato
        ticket = TicketHeader.query.get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket non trovato'})
        
        # Se il ticket viene da una task, gestisci la rimozione dalla task
        if from_task:
            current_app.logger.info(f"🎯 Rimozione ticket #{ticket.NumTicket} da task DDT preview")
            
            # Trova il TaskTicket associato se non è stato fornito task_id
            if not task_id:
                from app.models import TaskTicket, Task
                task_ticket = TaskTicket.query.filter_by(ticket_id=ticket_id).first()
                if task_ticket:
                    task_id = task_ticket.task_id
                    current_app.logger.info(f"🔍 Trovato ticket nella task ID: {task_id}")
            
            if task_id:
                from app.models import TaskTicket, Task, TaskTicketScan
                
                # Verifica che la task esista e non abbia già generato un DDT
                task = Task.query.get(task_id)
                if task and task.ddt_generated and task.ddt_id:
                    return jsonify({
                        'success': False, 
                        'message': f'Impossibile rimuovere il ticket da un task con DDT #{task.ddt_id} già generato.'
                    })
                
                # Trova e rimuovi il TaskTicket
                task_ticket = TaskTicket.query.filter_by(
                    task_id=task_id, 
                    ticket_id=ticket_id
                ).first()
                
                if task_ticket:
                    current_app.logger.info(f"🗑️ Rimozione TaskTicket ID: {task_ticket.id}")
                    
                    # Rimuovi tutti i scan associati a questo TaskTicket
                    TaskTicketScan.query.filter_by(task_ticket_id=task_ticket.id).delete()
                    
                    # Rimuovi il TaskTicket
                    db.session.delete(task_ticket)
                    
                    # Aggiorna il progresso della task
                    if task:
                        task.update_progress()
                        
                        # Verifica se la task è ora vuota (senza ticket)
                        remaining_tickets = TaskTicket.query.filter_by(task_id=task_id).count()
                        current_app.logger.info(f"📊 Ticket rimanenti nella task {task.task_number}: {remaining_tickets}")
                        
                        if remaining_tickets == 0:
                            current_app.logger.info(f"🚨 Task {task.task_number} è ora vuota - eliminazione automatica")
                            
                            # Elimina le notifiche della task
                            from app.models import TaskNotification
                            TaskNotification.query.filter_by(task_id=task_id).delete()
                            
                            # Elimina la task vuota
                            task_number = task.task_number
                            db.session.delete(task)
                            
                            current_app.logger.info(f"✅ Task {task_number} eliminata automaticamente (vuota)")
                            
                            # Resetta lo stato del ticket solo se la task è stata eliminata
                            ticket.Enviado = 0
                            db.session.commit()
                            
                            return jsonify({
                                'success': True, 
                                'message': f'Ticket rimosso dalla task {task_number}. Task eliminata (vuota).',
                                'task_deleted': True,
                                'task_number': task_number
                            })
                        else:
                            current_app.logger.info(f"📋 Task {task.task_number} mantiene {remaining_tickets} ticket")
                    
                    current_app.logger.info(f"📋 Ticket #{ticket.NumTicket} rimosso dalla task ID: {task_id}")
                else:
                    current_app.logger.warning(f"⚠️ TaskTicket non trovato per ticket {ticket_id} nella task {task_id}")
        
        # Resetta sempre lo stato del ticket (se non è stato già fatto sopra)
        if ticket.Enviado != 0:
            ticket.Enviado = 0  # Reset to not sent/processed
            current_app.logger.info(f"🔄 Ticket #{ticket.NumTicket} rimosso dalla preview DDT - stato reimpostato a Enviado = 0")
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Ticket rimosso dal preview e stato reimpostato',
            'task_deleted': False
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nella rimozione ticket dalla preview: {str(e)}")
        return jsonify({'success': False, 'message': f'Errore durante la rimozione: {str(e)}'})

@ddt_bp.route('/api/preview/search_tickets', methods=['GET'])
@login_required
def api_search_tickets_for_preview():
    """API to search available tickets for adding to DDT preview - organized by products"""
    cliente_id = request.args.get('cliente_id')
    query = request.args.get('q', '').strip()
    limit = int(request.args.get('limit', 50))
    
    if not cliente_id:
        return jsonify({'success': False, 'message': 'Cliente ID richiesto'})
    
    # Query ottimizzata per ottenere ticket raggruppati per prodotto - INCLUDE IdLineaTicket
    optimized_query = """
        SELECT 
            tc.IdTicket,
            tc.NumTicket,
            tc.Fecha,
            tc.IdEmpresa,
            tc.IdTienda,
            tc.IdBalanzaMaestra,
            tc.IdBalanzaEsclava,
            tc.TipoVenta,
            tc.CodigoBarras,
            tl.IdLineaTicket,
            tl.IdArticulo,
            tl.Descripcion,
            tl.Peso,
            tl.comportamiento,
            tl.FechaCaducidad,
            tl.Precio,
            p.IdFamilia,
            p.IdSubFamilia,
            p.IdIva,
            COALESCE(i.PorcentajeIVA, 0) as porcentaje_iva
        FROM dat_ticket_cabecera tc
        INNER JOIN dat_ticket_linea tl ON tc.IdTicket = tl.IdTicket
        LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
        LEFT JOIN dat_iva i ON p.IdIva = i.IdIva
        WHERE tc.Enviado = 0
        ORDER BY tc.Fecha DESC, tl.IdLineaTicket
        LIMIT :limit
    """
    
    # Esegui la query ottimizzata
    result = db.session.execute(text(optimized_query), {'limit': limit})
    
    # Organize tickets by products - raggruppa i dati per IdArticulo
    products_map = {}
    
    for row in result:
        # Estrai i dati dalla riga
        id_ticket = row[0]
        num_ticket = row[1]
        fecha = row[2]
        id_empresa = row[3]
        id_tienda = row[4] or 1
        id_balanza_maestra = row[5] or 1
        id_balanza_esclava = row[6] or -1
        tipo_venta = row[7] or 2
        codigo_barras = row[8] or ''
        id_linea_ticket = row[9]  # IMPORTANTE: ID reale della linea
        id_articulo = row[10]
        descripcion = row[11]
        peso = float(row[12] or 0)
        comportamiento = row[13] or 0
        fecha_caducidad = row[14]
        precio_originale = float(row[15] or 0)
        id_familia = row[16]
        id_subfamilia = row[17]
        id_iva = row[18]  # ID dell'aliquota IVA
        porcentaje_iva = row[19]  # Percentuale IVA calcolata
        
        # CORREZIONE BUG IVA: Usa la nuova funzione helper per calcolo corretto
        precio_con_iva, precio_senza_iva, vat_rate = calculate_ticket_price_with_vat(
            int(cliente_id), id_articulo, precio_originale, id_iva
        )
        precio = precio_con_iva  # Usa il prezzo CON IVA per la visualizzazione
        
        current_app.logger.info(f"🔍 Search Tickets - Articolo {id_articulo}: Originale=€{precio_originale:.3f}, Con IVA=€{precio_con_iva:.3f}")
        
        # Group by product (IdArticulo)
        if id_articulo not in products_map:
            products_map[id_articulo] = {
                'id_articulo': id_articulo,
                'descripcion': descripcion,
                'comportamiento': comportamiento,
                'precio_base': precio_con_iva,
                'id_familia': id_familia,
                'id_subfamilia': id_subfamilia,
                'id_iva': id_iva,
                'porcentaje_iva': porcentaje_iva,
                'tickets': [],
                'total_weight': 0,
                'total_value': 0,
                'tickets_count': 0
            }
        
        # Add ticket info to product
        products_map[id_articulo]['tickets'].append({
            'IdTicket': id_ticket,
            'num_ticket': num_ticket,
            'fecha_formateada': fecha.strftime('%d/%m/%Y %H:%M') if fecha else '',
            'FechaHora': fecha.strftime('%d/%m/%Y %H:%M') if fecha else '',  # For compatibility
            'peso_total': peso,
            'fecha_caducidad': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None,
            'fecha_caducidad_formateada': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None,
            'importe_total': peso * precio_senza_iva,  # CORREZIONE: Usa prezzo senza IVA per totali
            'codigo_producto': f"{id_articulo}",
            'id_empresa': id_empresa,
            'id_tienda': id_tienda,
            'id_balanza_maestra': id_balanza_maestra,
            'id_balanza_esclava': id_balanza_esclava,
            'tipo_venta': tipo_venta,
            'codigo_barras': codigo_barras,
            'lines': [{
                'id_linea_ticket': id_linea_ticket,  # IMPORTANTE: ID reale della linea
                'id_articulo': id_articulo,
                'descripcion': descripcion,
                'peso': peso,
                'precio': precio_con_iva,  # CORREZIONE: Usa prezzo CON IVA corretto
                'precio_senza_iva': precio_senza_iva,  # Aggiungi anche prezzo senza IVA
                'precio_con_iva': precio_con_iva,  # Per compatibilità
                'porcentaje_iva': int(vat_rate * 100),  # Percentuale IVA per il frontend
                'vat_rate': vat_rate,  # Aliquota IVA
                'comportamiento': comportamiento,
                'importe': peso * precio_senza_iva,  # CORREZIONE: Usa prezzo senza IVA per calcoli
                'importe_con_iva': peso * precio_con_iva  # 🔧 AGGIUNTO: Importo con IVA per coerenza
            }]
        })
        
        # Update totals per prodotto
        products_map[id_articulo]['total_weight'] += peso
        products_map[id_articulo]['total_value'] += peso * precio_senza_iva  # CORREZIONE: Usa prezzo senza IVA
        products_map[id_articulo]['tickets_count'] += 1
    
    # Convert to list and sort by product name
    products = list(products_map.values())
    products.sort(key=lambda x: x['descripcion'])
    
    # Apply product filter if provided
    if query and not query.isdigit():
        products = [p for p in products if query.lower() in p['descripcion'].lower()]
    
    return jsonify({'success': True, 'products': products})

@ddt_bp.route('/api/preview/create_ticket', methods=['POST'])
@login_required
def api_create_manual_ticket():
    """API to create a manual ticket data for localStorage (no DB write)"""
    data = request.get_json()
    
    # Validazione dati richiesti
    required_fields = ['cliente_id', 'empresa_id', 'products']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'success': False, 'message': f'Campo {field} mancante'})
    
    cliente_id = data.get('cliente_id')
    empresa_id = data.get('empresa_id', 1)
    products = data.get('products', [])
    
    if not products:
        return jsonify({'success': False, 'message': 'Almeno un prodotto è richiesto'})
    
    try:
        # Genera un ID ticket temporaneo unico (negativo per distinguerlo dai ticket reali)
        import time
        temp_ticket_id = -int(time.time())  # ID negativo basato su timestamp
        temp_num_ticket = f"MAN{abs(temp_ticket_id)}"  # Numero ticket manuale
        
        # Prepara le righe del ticket per localStorage
        ticket_lines_data = []
        total_ticket = 0
        
        for idx, product_data in enumerate(products, 1):
            peso = float(product_data.get('peso', 1))
            descripcion = product_data.get('descripcion', 'Prodotto Personalizzato')
            precio_con_iva = float(product_data.get('precio', 1.00))
            id_iva = int(product_data.get('id_iva', 3))  # Default 22%
            fecha_caducidad = product_data.get('fecha_caducidad')
            
            # Calcola aliquota IVA
            vat_rate = 0.04  # Default 4%
            if id_iva == 0:
                vat_rate = 0.00  # 0% - Esente IVA
            elif id_iva == 1:
                vat_rate = 0.04  # 4%
            elif id_iva == 2:
                vat_rate = 0.10  # 10%
            elif id_iva == 3:
                vat_rate = 0.22  # 22%
            
            # Scorporo IVA dal prezzo per coerenza con i ticket normali
            precio_sin_iva = round_price_without_vat(precio_con_iva / (1 + vat_rate)) if vat_rate > 0 else precio_con_iva
            
            # Calcola importo linea usando il prezzo senza IVA
            importe = peso * precio_sin_iva
            total_ticket += importe
            
            # Prepara dati per localStorage (simula una TicketLine)
            ticket_lines_data.append({
                'id_linea_ticket': f"temp_{temp_ticket_id}_{idx}",  # ID temporaneo
                'id_ticket': temp_ticket_id,
                'id_articulo': 999,  # Usa sempre ID 999 per prodotti personalizzati
                'descripcion': descripcion,
                'peso': float(peso),
                'precio': precio_sin_iva,  # Prezzo senza IVA per coerenza
                'precio_con_iva': precio_con_iva,  # Mantieni anche il prezzo originale
                'importe': importe,
                'fecha_caducidad': fecha_caducidad,
                'id_iva': id_iva,
                'vat_rate': vat_rate,  # Aggiungi aliquota IVA
                'comportamiento': product_data.get('comportamiento', 1),
                'is_manual': True  # Flag per identificare ticket manuali
            })
        
        # Prepara risposta con i dati del ticket per localStorage
        return jsonify({
            'success': True,
            'message': 'Ticket manuale creato (solo localStorage)',
            'ticket': {
                'id_ticket': temp_ticket_id,
                'num_ticket': temp_num_ticket,
                'fecha': datetime.now().strftime('%d/%m/%Y %H:%M'),
                'lines': ticket_lines_data,
                'total': total_ticket,
                'id_empresa': empresa_id,
                'id_tienda': 1,
                'id_balanza_maestra': 1,
                'id_balanza_esclava': -1,
                'tipo_venta': 2,
                'is_manual': True  # Flag per identificare ticket manuali
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nella creazione dei dati ticket manuale: {str(e)}")
        return jsonify({'success': False, 'message': f'Errore durante la creazione: {str(e)}'}) 

@ddt_bp.route('/api/products/search', methods=['GET'])
@login_required
def api_search_products():
    """API to search products for manual ticket creation"""
    query = request.args.get('q', '').strip()
    cliente_id = request.args.get('cliente_id')  # Aggiungi cliente_id per prezzi listino
    
    if len(query) < 2:
        return jsonify({'success': True, 'products': []})
    
    # Cerca prodotti per descrizione o ID
    products_query = Product.query
    
    if query.isdigit():
        # Ricerca per ID articolo
        products_query = products_query.filter(Product.IdArticulo == int(query))
    else:
        # Ricerca per descrizione
        products_query = products_query.filter(Product.Descripcion.like(f'%{query}%'))
    
    products = products_query.limit(20).all()
    
    # Formatta risultati
    results = []
    for product in products:
        results.append({
            'id': product.IdArticulo,
            'descripcion': product.Descripcion,
            'precio': float(product.PrecioConIVA or 0),
            'ean': product.EANScanner or '',
            'famiglia': product.IdFamilia,
            'subfamiglia': product.IdSubFamilia,
            'iva': product.IdIva
        })
    
    return jsonify({'success': True, 'products': results}) 

@ddt_bp.route('/debug/verify_data', methods=['GET'])
@login_required
def debug_verify_data():
    """Debug function to verify IdTicket-IdArticulo integrity"""
    try:
        # Get some recent tickets
        recent_tickets = TicketHeader.query.order_by(TicketHeader.Fecha.desc()).limit(10).all()
        
        verification_results = []
        
        for ticket in recent_tickets:
            # Get lines for this ticket
            lines = TicketLine.query.filter_by(IdTicket=ticket.IdTicket).all()
            
            ticket_info = {
                'ticket_id': ticket.IdTicket,
                'num_ticket': ticket.NumTicket,
                'fecha': ticket.Fecha.strftime('%Y-%m-%d %H:%M:%S') if ticket.Fecha else 'N/A',
                'lines_count': len(lines),
                'lines': []
            }
            
            for line in lines:
                product = Product.query.get(line.IdArticulo)
                line_info = {
                    'id_linea_ticket': line.IdLineaTicket,
                    'id_ticket': line.IdTicket,
                    'id_articulo': line.IdArticulo,
                    'descripcion': line.Descripcion,
                    'peso': float(line.Peso) if line.Peso else 0,
                    'product_found': product is not None,
                    'product_desc': product.Descripcion if product else 'N/A'
                }
                ticket_info['lines'].append(line_info)
            
            verification_results.append(ticket_info)
        
        return jsonify({
            'success': True,
            'verification_results': verification_results
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nella verifica dati: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ddt_bp.route('/debug/check_duplicates', methods=['GET'])
@login_required
def debug_check_duplicates():
    """Debug function to check for duplicate or inconsistent data"""
    try:
        # Check for ticket lines with the same IdTicket and IdArticulo but different descriptions
        query = """
        SELECT 
            t1.IdTicket,
            t1.IdArticulo,
            COUNT(*) as count_lines,
            GROUP_CONCAT(DISTINCT t1.Descripcion) as descriptions,
            GROUP_CONCAT(DISTINCT t1.IdLineaTicket) as line_ids
        FROM dat_ticket_linea t1
        GROUP BY t1.IdTicket, t1.IdArticulo
        HAVING COUNT(*) > 1 OR COUNT(DISTINCT t1.Descripcion) > 1
        ORDER BY t1.IdTicket DESC
        LIMIT 20
        """
        
        result = db.session.execute(text(query))
        duplicates = []
        
        for row in result:
            duplicates.append({
                'id_ticket': row[0],
                'id_articulo': row[1],
                'count_lines': row[2],
                'descriptions': row[3],
                'line_ids': row[4]
            })
        
        # Check for orphaned ticket lines (lines without valid ticket)
        orphaned_query = """
        SELECT tl.IdLineaTicket, tl.IdTicket, tl.IdArticulo, tl.Descripcion
        FROM dat_ticket_linea tl
        LEFT JOIN dat_ticket_cabecera tc ON tl.IdTicket = tc.IdTicket
        WHERE tc.IdTicket IS NULL
        LIMIT 10
        """
        
        orphaned_result = db.session.execute(text(orphaned_query))
        orphaned_lines = []
        
        for row in orphaned_result:
            orphaned_lines.append({
                'id_linea_ticket': row[0],
                'id_ticket': row[1],
                'id_articulo': row[2],
                'descripcion': row[3]
            })
        
        # Check for duplicate DDT primary keys
        ddt_duplicates_query = """
        SELECT IdAlbaran, IdEmpresa, IdTienda, IdBalanzaMaestra, IdBalanzaEsclava, COUNT(*) as count
        FROM dat_albaran_cabecera 
        GROUP BY IdAlbaran, IdEmpresa, IdTienda, IdBalanzaMaestra, IdBalanzaEsclava
        HAVING COUNT(*) > 1
        """
        
        ddt_duplicates_result = db.session.execute(text(ddt_duplicates_query))
        ddt_duplicates = []
        
        for row in ddt_duplicates_result:
            ddt_duplicates.append({
                'id_albaran': row[0],
                'id_empresa': row[1],
                'id_tienda': row[2],
                'id_balanza_maestra': row[3],
                'id_balanza_esclava': row[4],
                'count': row[5]
            })
        
        # Get current max IdAlbaran
        max_id_albaran = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 0
        
        return jsonify({
            'success': True,
            'duplicates': duplicates,
            'orphaned_lines': orphaned_lines,
            'ddt_duplicates': ddt_duplicates,
            'max_id_albaran': max_id_albaran
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel controllo duplicati: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ddt_bp.route('/debug/check_ddt_integrity', methods=['GET'])
@login_required
@admin_required
def debug_check_ddt_integrity():
    """Debug endpoint specifically for DDT integrity checks and fixes"""
    try:
        # 1. Check for duplicate DDT primary keys
        duplicate_ddts_query = """
        SELECT IdAlbaran, IdEmpresa, IdTienda, IdBalanzaMaestra, IdBalanzaEsclava, COUNT(*) as count,
               GROUP_CONCAT(NumAlbaran) as num_albarans,
               GROUP_CONCAT(NombreCliente) as clients
        FROM dat_albaran_cabecera 
        GROUP BY IdAlbaran, IdEmpresa, IdTienda, IdBalanzaMaestra, IdBalanzaEsclava
        HAVING COUNT(*) > 1
        """
        
        duplicate_ddts = db.session.execute(text(duplicate_ddts_query)).fetchall()
        
        # 2. Get next available IdAlbaran
        max_id_albaran = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 0
        next_id_albaran = max_id_albaran + 1
        
        # 3. Check DDT statistics
        ddt_stats_query = """
        SELECT 
            COUNT(*) as total_ddts,
            MIN(IdAlbaran) as min_id,
            MAX(IdAlbaran) as max_id,
            COUNT(DISTINCT IdAlbaran) as unique_ids,
            COUNT(DISTINCT CONCAT(IdAlbaran,'-',IdEmpresa,'-',IdTienda,'-',IdBalanzaMaestra,'-',IdBalanzaEsclava)) as unique_combinations
        FROM dat_albaran_cabecera
        """
        
        ddt_stats = db.session.execute(text(ddt_stats_query)).fetchone()
        
        # 4. Check for potential issues in future DDT creation
        test_combination_query = """
        SELECT COUNT(*) as exists_count
        FROM dat_albaran_cabecera
        WHERE IdAlbaran = %s AND IdEmpresa = 1 AND IdTienda = 1 AND IdBalanzaMaestra = 1 AND IdBalanzaEsclava = -1
        """
        
        test_exists = db.session.execute(text(test_combination_query), (next_id_albaran,)).fetchone()
        
        # 5. Get recent DDTs for analysis
        recent_ddts_query = """
        SELECT IdAlbaran, NumAlbaran, IdEmpresa, IdTienda, IdBalanzaMaestra, IdBalanzaEsclava, 
               NombreCliente, Fecha
        FROM dat_albaran_cabecera
        ORDER BY Fecha DESC
        LIMIT 10
        """
        
        recent_ddts = db.session.execute(text(recent_ddts_query)).fetchall()
        
        return jsonify({
            'success': True,
            'duplicate_ddts': [
                {
                    'id_albaran': row[0],
                    'id_empresa': row[1], 
                    'id_tienda': row[2],
                    'id_balanza_maestra': row[3],
                    'id_balanza_esclava': row[4],
                    'count': row[5],
                    'num_albarans': row[6],
                    'clients': row[7]
                } for row in duplicate_ddts
            ],
            'next_available_id': next_id_albaran,
            'next_id_would_conflict': test_exists[0] > 0 if test_exists else False,
            'ddt_statistics': {
                'total_ddts': ddt_stats[0] if ddt_stats else 0,
                'min_id': ddt_stats[1] if ddt_stats else 0,
                'max_id': ddt_stats[2] if ddt_stats else 0,
                'unique_ids': ddt_stats[3] if ddt_stats else 0,
                'unique_combinations': ddt_stats[4] if ddt_stats else 0,
                'has_duplicates': (ddt_stats[0] != ddt_stats[4]) if ddt_stats else False
            },
            'recent_ddts': [
                {
                    'id_albaran': row[0],
                    'num_albaran': row[1],
                    'id_empresa': row[2],
                    'id_tienda': row[3],
                    'id_balanza_maestra': row[4],
                    'id_balanza_esclava': row[5],
                    'cliente': row[6],
                    'fecha': str(row[7]) if row[7] else None
                } for row in recent_ddts
            ]
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore nel controllo integrità DDT: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@ddt_bp.route('/debug/test_discounts', methods=['GET'])
@login_required
def debug_test_discounts():
    """Debug function to test discount functionality"""
    try:
        # Simula dati di test per gli sconti
        test_ticket_discounts = {
            "123": 20.0,
            "456": 15.5,
            "789": 10.0
        }
        
        # Test 1: Verifica conversione JSON
        json_test = json.dumps(test_ticket_discounts)
        parsed_test = json.loads(json_test)
        
        # Test 2: Verifica lookup degli sconti
        test_results = []
        for ticket_id_str, expected_discount in test_ticket_discounts.items():
            ticket_discount = float(parsed_test.get(ticket_id_str, 0))
            test_results.append({
                'ticket_id': ticket_id_str,
                'expected_discount': expected_discount,
                'parsed_discount': ticket_discount,
                'match': ticket_discount == expected_discount
            })
        
        # Test 3: Verifica calcoli degli sconti
        original_price = 100.0
        for discount_percent in [10, 20, 30]:
            discount_factor = 1 - (discount_percent / 100)
            discounted_price = original_price * discount_factor
            test_results.append({
                'test_type': 'calculation',
                'original_price': original_price,
                'discount_percent': discount_percent,
                'discount_factor': discount_factor,
                'discounted_price': discounted_price
            })
        
        # Test 4: Verifica DDT recenti con sconti
        recent_ddts = AlbaranCabecera.query.order_by(AlbaranCabecera.Fecha.desc()).limit(5).all()
        ddt_discount_data = []
        
        for ddt in recent_ddts:
            lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
            lines_with_discounts = [line for line in lines if line.Descuento and line.Descuento > 0]
            
            ddt_discount_data.append({
                'ddt_id': ddt.IdAlbaran,
                'total_lines': len(lines),
                'lines_with_discounts': len(lines_with_discounts),
                'discount_details': [
                    {
                        'line_id': line.IdLineaAlbaran,
                        'discount': float(line.Descuento or 0),
                        'description': line.Descripcion,
                        'total_original': float(line.ImporteSinIVASinDtoL or 0),
                        'vat_original': float(line.ImporteDelIVAConDtoL or 0)
                    } for line in lines_with_discounts
                ]
            })
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'json_test': {
                'original': test_ticket_discounts,
                'serialized': json_test,
                'parsed': parsed_test
            },
            'discount_lookup_tests': test_results,
            'recent_ddts_with_discounts': ddt_discount_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel test degli sconti: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@ddt_bp.route('/debug/simulate_discount_ddt', methods=['POST'])
@login_required
def debug_simulate_discount_ddt():
    """Debug function to simulate DDT creation with predefined discounts"""
    try:
        # Simula i dati che dovrebbero arrivare dal form
        simulated_form_data = {
            'cliente_id': '1',  # Usa il primo cliente disponibile
            'id_empresa': '1',
            'tickets': '[]',  # Nessun ticket normale
            'manual_tickets': '[{"id_ticket": -9999, "lines": [{"descripcion": "Prodotto Test Sconto", "peso": 2.0, "precio": 50.0, "id_iva": 3, "comportamiento": 1}], "total": 100.0}]',
            'ticket_discounts': '{"-9999": 20.0}',  # 20% di sconto sul ticket manuale
            'note': 'Test DDT con sconto 20%'
        }
        
        current_app.logger.info(f"🧪 DEBUG: Simulazione DDT con sconti")
        current_app.logger.info(f"    Dati simulati: {simulated_form_data}")
        
        # Parse dei dati come nel vero endpoint
        ticket_data = json.loads(simulated_form_data['tickets']) if simulated_form_data['tickets'] else []
        manual_tickets = json.loads(simulated_form_data['manual_tickets']) if simulated_form_data['manual_tickets'] else []
        ticket_discounts = json.loads(simulated_form_data['ticket_discounts']) if simulated_form_data['ticket_discounts'] else {}
        
        current_app.logger.info(f"🧪 DEBUG: Parsing completato")
        current_app.logger.info(f"    ticket_discounts: {ticket_discounts}")
        
        # Verifica che il cliente esista
        client = Client.query.first()
        if not client:
            return jsonify({'success': False, 'error': 'Nessun cliente trovato nel database'})
        
        empresa = Company.query.first()
        if not empresa:
            return jsonify({'success': False, 'error': 'Nessuna azienda trovata nel database'})
        
        # Simula il processo di creazione come nel vero endpoint
        manual_ticket = manual_tickets[0]
        ticket_line = manual_ticket['lines'][0]
        
        # Simula il calcolo degli sconti
        manual_ticket_id_str = str(manual_ticket['id_ticket'])
        ticket_discount = float(ticket_discounts.get(manual_ticket_id_str, 0))
        
        current_app.logger.info(f"🧪 DEBUG: Calcolo sconto")
        current_app.logger.info(f"    manual_ticket_id_str: {manual_ticket_id_str}")
        current_app.logger.info(f"    ticket_discount: {ticket_discount}")
        
        # Calcola prezzi
        id_iva = ticket_line.get('id_iva', 3)  # Default 22%
        vat_rate = 0.22 if id_iva == 3 else 0.10 if id_iva == 2 else 0.04
        
        price_with_vat = float(ticket_line['precio'])
        price_without_vat = round_price_without_vat(price_with_vat / (1 + vat_rate)) if vat_rate > 0 else price_with_vat
        peso_value = float(ticket_line['peso'])
        line_total = price_without_vat * peso_value
        line_vat = line_total * vat_rate
        
        original_line_total = line_total
        original_line_vat = line_vat
        
        # Applica sconto
        if ticket_discount > 0:
            discount_factor = 1 - (ticket_discount / 100)
            line_total = line_total * discount_factor
            line_vat = line_vat * discount_factor
        
        result = {
            'success': True,
            'simulation_data': {
                'manual_ticket_id': manual_ticket_id_str,
                'ticket_discount_percent': ticket_discount,
                'original_totals': {
                    'line_total': original_line_total,
                    'line_vat': original_line_vat,
                    'total_with_vat': original_line_total + original_line_vat
                },
                'discounted_totals': {
                    'line_total': line_total,
                    'line_vat': line_vat,
                    'total_with_vat': line_total + line_vat
                },
                'savings': {
                    'amount': (original_line_total + original_line_vat) - (line_total + line_vat),
                    'percentage': ticket_discount
                }
            },
            'parsing_results': {
                'ticket_discounts_raw': simulated_form_data['ticket_discounts'],
                'ticket_discounts_parsed': ticket_discounts,
                'lookup_test': {
                    'key_searched': manual_ticket_id_str,
                    'value_found': ticket_discount,
                    'keys_available': list(ticket_discounts.keys())
                }
            }
        }
        
        current_app.logger.info(f"🧪 DEBUG: Simulazione completata con successo")
        current_app.logger.info(f"    Risultato: {result}")
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Errore nella simulazione DDT con sconti: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@ddt_bp.route('/api/tickets/all')
@login_required
def get_all_tickets():
    """API endpoint for getting all available tickets with detailed information"""
    try:
        # Get all pending tickets
        tickets = TicketHeader.query.filter(
            TicketHeader.Enviado == 0
        ).order_by(TicketHeader.Fecha.desc()).all()
        
        results = []
        for ticket in tickets:
            # Get ticket lines and calculate totals - GROUP BY to avoid duplicates
            lines_query = """
                SELECT DISTINCT 
                    tl.IdArticulo,
                    tl.Descripcion,
                    tl.Peso,
                    tl.comportamiento,
                    tl.Precio
                FROM dat_ticket_linea tl
                LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
                WHERE tl.IdTicket = :ticket_id
                ORDER BY tl.IdArticulo
            """
            
            lines_result = db.session.execute(text(lines_query), {'ticket_id': ticket.IdTicket})
            
            total_amount = 0
            total_weight = 0
            products_preview = []
            unique_products = {}  # Track unique products to avoid duplicates
            
            for row in lines_result:
                id_articulo = row[0]
                descripcion = row[1]
                peso = float(row[2] or 0)
                comportamiento = row[3] or 0
                precio = float(row[4] or 0)
                
                # Skip if we already processed this article
                if id_articulo in unique_products:
                    current_app.logger.warning(f"⚠️ Duplicate IdArticulo {id_articulo} found in ticket {ticket.IdTicket}")
                    continue
                
                # Mark this article as processed
                unique_products[id_articulo] = True
                
                line_total = peso * precio
                total_amount += line_total
                total_weight += peso
                
                # Add to products preview (first 3 unique products)
                if len(products_preview) < 3:
                    products_preview.append({
                        'descripcion': descripcion,
                        'peso': peso,
                        'precio': precio,
                        'comportamiento': comportamiento
                    })
            
            total_items = len(unique_products)  # Count unique products only
            
            # Get the last product as a sample
            last_product = None
            if products_preview:
                last_product = products_preview[-1]['descripcion']
            
            results.append({
                'id_ticket': ticket.IdTicket,
                'num_ticket': ticket.NumTicket,
                'fecha': ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else '',
                'fecha_iso': ticket.Fecha.strftime('%Y-%m-%d') if ticket.Fecha else '',
                'id_empresa': ticket.IdEmpresa,
                'id_tienda': ticket.IdTienda or 1,
                'id_balanza_maestra': ticket.IdBalanzaMaestra or 1,
                'id_balanza_esclava': ticket.IdBalanzaEsclava or -1,
                'tipo_venta': ticket.TipoVenta or 2,
                'status': ticket.status_text,
                'status_class': ticket.status_class,
                'total_items': total_items,
                'total_amount': round(total_amount, 2),
                'total_weight': round(total_weight, 3),
                'products_preview': products_preview,
                'last_product': last_product,
                'codigo_barras': ticket.CodigoBarras or ''
            })
        
        print(f"Loaded {len(results)} tickets with detailed information (duplicates removed)")
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Error loading tickets: {str(e)}")
        current_app.logger.error(f"Error in get_all_tickets: {str(e)}")
        return jsonify([]), 500



@ddt_bp.route('/test_pdf_save', methods=['GET'])
@login_required
@admin_required
def test_pdf_save():
    """Test function to verify automatic PDF saving works correctly"""
    try:
        # Get the most recent DDT for testing
        latest_ddt = AlbaranCabecera.query.order_by(AlbaranCabecera.IdAlbaran.desc()).first()
        
        if not latest_ddt:
            flash('Nessun DDT trovato per il test', 'warning')
            return redirect(url_for('ddt.index'))
        
        # Get client and company info
        cliente = Client.query.get(latest_ddt.IdCliente)
        empresa = Company.query.get(latest_ddt.IdEmpresa)
        
        if not cliente:
            cliente = type('Client', (), {
                'Nombre': latest_ddt.NombreCliente or 'Cliente_Test',
                'IdCliente': latest_ddt.IdCliente
            })()
        
        if not empresa:
            empresa = Company.query.first()
            if not empresa:
                empresa = type('Company', (), {
                    'NombreEmpresa': 'DBLogiX Test',
                    'IdEmpresa': 1
                })()
        
        # Test the automatic save function
        current_app.logger.info(f"🧪 TEST: Iniziando test salvataggio PDF per DDT #{latest_ddt.IdAlbaran}")
        
        pdf_path = save_ddt_pdf_automatically(latest_ddt, cliente, empresa)
        
        if pdf_path:
            flash(f'✅ Test completato! PDF salvato in: {pdf_path}', 'success')
            current_app.logger.info(f"🧪 TEST: PDF salvato con successo in {pdf_path}")
        else:
            flash('❌ Test fallito: PDF non salvato', 'danger')
            current_app.logger.error(f"🧪 TEST: Errore - PDF non salvato")
        
        return redirect(url_for('ddt.detail', ddt_id=latest_ddt.IdAlbaran))
        
    except Exception as e:
        import traceback
        error_msg = f"Errore nel test PDF: {str(e)}"
        tb_msg = f"Traceback: {traceback.format_exc()}"
        
        current_app.logger.error(f"🧪 TEST FALLITO: {error_msg}")
        current_app.logger.error(f"🧪 TEST TRACEBACK: {tb_msg}")
        
        flash(f'❌ Test fallito: {error_msg}', 'danger')
        return redirect(url_for('ddt.index'))

# ========== NUOVE FUNZIONI DDT ==========

@ddt_bp.route('/renumber_ddts', methods=['POST'])
@login_required
@admin_required
def renumber_ddts():
    """
    Imposta il numero da cui partiranno i prossimi DDT.
    Se imposto 150, il prossimo DDT avrà ID 150.
    """
    try:
        data = request.get_json()
        new_start_number = data.get('new_start_number')
        
        if not new_start_number or new_start_number <= 0:
            return jsonify({
                'success': False,
                'message': 'Il numero deve essere maggiore di 0'
            })
        
        # Verifica che il numero sia valido (non già esistente)
        existing_ddt = AlbaranCabecera.query.filter_by(IdAlbaran=new_start_number).first()
        if existing_ddt:
            return jsonify({
                'success': False,
                'message': f'Il numero {new_start_number} esiste già. Scegli un numero diverso.'
            })
        
        # Imposta l'AUTO_INCREMENT della tabella
        db.session.execute(text(f"ALTER TABLE dat_albaran_cabecera AUTO_INCREMENT = {new_start_number}"))
        db.session.commit()
        
        # Verifica che l'AUTO_INCREMENT sia stato impostato correttamente
        result = db.session.execute(text("SHOW TABLE STATUS LIKE 'dat_albaran_cabecera'")).fetchone()
        current_auto_increment = result[10] if result else None  # Auto_increment è la colonna 11 (indice 10)
        
        current_app.logger.info(f"✅ AUTO_INCREMENT impostato a {new_start_number}. Valore attuale: {current_auto_increment}")
        
        if current_auto_increment != new_start_number:
            current_app.logger.warning(f"⚠️ AUTO_INCREMENT non corrisponde: richiesto {new_start_number}, attuale {current_auto_increment}")
        
        return jsonify({
            'success': True,
            'message': f'Numerazione impostata correttamente. Il prossimo DDT avrà ID {new_start_number}',
            'next_ddt_number': new_start_number,
            'actual_auto_increment': current_auto_increment
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore nella rinumerazione DDT: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'impostazione: {str(e)}'
        })


@ddt_bp.route('/reset_all_ddts', methods=['POST'])
@login_required
@admin_required
def reset_all_ddts():
    """
    Elimina tutti i DDT dal database.
    Il prossimo DDT partirà da ID 1.
    """
    try:
        # Conta i DDT esistenti
        ddt_count = AlbaranCabecera.query.count()
        
        if ddt_count == 0:
            return jsonify({
                'success': False,
                'message': 'Non ci sono DDT da eliminare'
            })
        
        current_app.logger.info(f"🗑️  Iniziando eliminazione di {ddt_count} DDT dal database")
        
        # Elimina tutti i DDT (le linee vengono eliminate automaticamente per foreign key cascade)
        lines_deleted = db.session.execute(text("DELETE FROM dat_albaran_linea")).rowcount
        headers_deleted = db.session.execute(text("DELETE FROM dat_albaran_cabecera")).rowcount
        
        # Reset AUTO_INCREMENT a 1
        db.session.execute(text("ALTER TABLE dat_albaran_cabecera AUTO_INCREMENT = 1"))
        db.session.execute(text("ALTER TABLE dat_albaran_linea AUTO_INCREMENT = 1"))
        
        db.session.commit()
        
        current_app.logger.info(f"✅ Azzeramento completato: {headers_deleted} DDT e {lines_deleted} linee eliminate")
        current_app.logger.info(f"🔄 AUTO_INCREMENT resettato a 1. Il prossimo DDT avrà ID 1")
        
        return jsonify({
            'success': True,
            'message': f'Azzeramento completato! Eliminati {headers_deleted} DDT e {lines_deleted} linee. Il prossimo DDT partirà da ID 1.',
            'deleted_ddts': headers_deleted,
            'deleted_lines': lines_deleted
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore nell'azzeramento DDT: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'azzeramento: {str(e)}'
        })

def get_vat_rate_from_line(line):
    """Recupera l'aliquota IVA da una linea, gestendo sia oggetti che dict."""
    if hasattr(line, 'PorcentajeIVA'):
        return float(getattr(line, 'PorcentajeIVA') or 0)
    if hasattr(line, 'porcentaje_iva'):
        return float(getattr(line, 'porcentaje_iva') or 0)
    if isinstance(line, dict):
        return float(line.get('PorcentajeIVA') or line.get('porcentaje_iva') or line.get('iva') or 0)
    return 0

def update_ticket_line_in_database(ticket_id, line_id, field, value):
    """
    Aggiorna una linea specifica del ticket nel database
    Restituisce True se il salvataggio è andato a buon fine
    """
    try:
        current_app.logger.info(f"🔍 Tentativo aggiornamento linea DB: ticket={ticket_id}, linea={line_id}, campo={field}, valore={value}")

        # SICUREZZA: Controlla se è un ticket manuale (ID negativo) - non dovrebbe mai accadere
        if ticket_id < 0:
            current_app.logger.error(f"❌ SICUREZZA: Tentativo di salvare ticket manuale ({ticket_id}) nel database!")
            return False

        # Import necessario per la sezione speciale IVA
        from app.models import TicketLine, db
        
        # Mappa i nomi dei campi dal frontend al database
        field_mapping = {
            'descrizione': 'Descripcion',
            'codice': 'IdArticulo',
            'peso_quantita': 'Peso',
            'prezzo_unitario': 'Precio',
            'prezzo_totale': 'Importe',  # Importo totale con IVA
            'importo_iva': None,  # Campo virtuale, gestito separatamente
            'data_scadenza': 'FechaCaducidad',
            'id_iva': 'IdIVA',  # Ora gestito direttamente nella linea del ticket
            'porcentaje_iva': 'PorcentajeIVA',  # Ora gestito direttamente nella linea del ticket
            'texto_lote': 'TextoLote',
            'comportamiento': 'comportamiento',
            'precio_sin_iva': 'PrecioSinIVA',  # Prezzo senza IVA nella linea del ticket
            'ImporteSinIVASinDtoL': 'ImporteSinIVASinDtoL'  # 🔥 NUOVO: Imponibile senza IVA
        }
        
        db_field = field_mapping.get(field)
        
        # Gestione speciale per prezzo_totale (ora esiste il campo Importe nel DB)
        if field == 'prezzo_totale':
            current_app.logger.info(f"💰 CAMPO IMPORTO TOTALE: valore={value}, salvato nel campo Importe del database")
            # Ora il campo esiste nel DB, quindi proseguiamo con il salvataggio normale
        
        # Gestione speciale per importo_iva (campo virtuale)
        if field == 'importo_iva':
            current_app.logger.info(f"💡 Campo importo_iva: campo virtuale, salvataggio in session per visualizzazione")
            return True  # Campo virtuale, gestito lato frontend
        
        # Gestione speciale per campo precio_sin_iva - campo che esiste nella tabella ma potrebbe non essere nel modello
        if field == 'precio_sin_iva':
            current_app.logger.info(f"🎯 GESTIONE SPECIALE PRECIO_SIN_IVA: valore={value}")

            # Trova la linea del ticket
            ticket_line = TicketLine.query.filter_by(
                IdTicket=ticket_id,
                IdLineaTicket=line_id
            ).first()

            if ticket_line:
                try:
                    # Prova prima il metodo standard setattr
                    old_value = getattr(ticket_line, 'PrecioSinIVA', None)
                    setattr(ticket_line, 'PrecioSinIVA', float(value))

                    current_app.logger.info(f"🎯 AGGIORNAMENTO PRECIO_SIN_IVA: {old_value} → {value}")

                    # Salva immediatamente le modifiche alla linea del ticket
                    db.session.commit()
                    current_app.logger.info(f"💾 PrecioSinIVA salvato nella linea ticket: {value}")

                    # Aggiorna anche l'articolo collegato se necessario
                    if ticket_line.IdArticulo:
                        try:
                            update_article_precio_sin_iva_from_ticket_line(ticket_id, line_id, field, value)
                        except Exception as art_error:
                            current_app.logger.warning(f"⚠️ Errore aggiornamento articolo per PrecioSinIVA: {str(art_error)}")
                            # Non fallire se non riusciamo ad aggiornare l'articolo

                    return True

                except Exception as e:
                    current_app.logger.error(f"❌ Errore salvataggio PrecioSinIVA: {str(e)}")
                    # Rollback in caso di errore
                    try:
                        db.session.rollback()
                    except:
                        pass
                    return False
            else:
                current_app.logger.error(f"❌ Linea ticket non trovata per PrecioSinIVA: ticket={ticket_id}, linea={line_id}")
                return False

        # 🔥 Gestione speciale per campo ImporteSinIVASinDtoL - campo che esiste nella tabella
        if field == 'ImporteSinIVASinDtoL':
            current_app.logger.info(f"💰 GESTIONE SPECIALE IMPONIBILE SENZA IVA: valore={value}")

            # Trova la linea del ticket
            ticket_line = TicketLine.query.filter_by(
                IdTicket=ticket_id,
                IdLineaTicket=line_id
            ).first()

            if ticket_line:
                try:
                    # Salva direttamente nel campo ImporteSinIVASinDtoL
                    old_value = getattr(ticket_line, 'ImporteSinIVASinDtoL', None)
                    setattr(ticket_line, 'ImporteSinIVASinDtoL', float(value))

                    current_app.logger.info(f"💰 AGGIORNAMENTO IMPONIBILE SENZA IVA: {old_value} → {value}")

                    # Salva immediatamente le modifiche alla linea del ticket
                    db.session.commit()
                    current_app.logger.info(f"💾 ImporteSinIVASinDtoL salvato nella linea ticket: {value}")

                    return True

                except Exception as e:
                    current_app.logger.error(f"❌ Errore salvataggio ImporteSinIVASinDtoL: {str(e)}")
                    # Rollback in caso di errore
                    try:
                        db.session.rollback()
                    except:
                        pass
                    return False
            else:
                current_app.logger.error(f"❌ Linea ticket non trovata per ImporteSinIVASinDtoL: ticket={ticket_id}, linea={line_id}")
                return False

        # Gestione speciale per campi IVA - aggiorna anche l'articolo collegato
        if field in ['id_iva', 'porcentaje_iva']:
            current_app.logger.info(f"🎯 GESTIONE SPECIALE IVA: campo={field}, valore={value}")

            # Prima aggiorna la linea del ticket con entrambi i valori (IdIVA e PorcentajeIVA)
            if field == 'id_iva':
                # Converti IdIVA in PorcentajeIVA
                # 1 = 4%, 2 = 10%, 3 = 22%, 4 = Esente (0%)
                id_to_percentage = {1: 4.00, 2: 10.00, 3: 22.00, 4: 0.00}
                porcentaje_value = id_to_percentage.get(int(value), 4.00)
                current_app.logger.info(f"🔄 Conversione IVA: IdIVA {value} → PorcentajeIVA {porcentaje_value}%")

                # Trova la linea del ticket e aggiorna entrambi i campi
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=ticket_id,
                    IdLineaTicket=line_id
                ).first()

                if ticket_line:
                    old_id_iva = ticket_line.IdIVA
                    old_porcentaje = ticket_line.PorcentajeIVA

                    ticket_line.IdIVA = int(value)
                    ticket_line.PorcentajeIVA = porcentaje_value

                    current_app.logger.info(f"🎯 AGGIORNAMENTO DIRETTO IVA LINEA: IdIVA {old_id_iva}→{value}, PorcentajeIVA {old_porcentaje}→{porcentaje_value}")

                    # Salva immediatamente le modifiche alla linea del ticket
                    db.session.commit()
                    current_app.logger.info(f"💾 IVA linea ticket salvata: IdIVA={value}, PorcentajeIVA={porcentaje_value}")

            elif field == 'porcentaje_iva':
                # Converti PorcentajeIVA in IdIVA
                percentage_to_id = {4.00: 1, 10.00: 2, 22.00: 3, 0.00: 4}
                id_value = percentage_to_id.get(float(value), 1)

                # Trova la linea del ticket e aggiorna entrambi i campi
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=ticket_id,
                    IdLineaTicket=line_id
                ).first()

                if ticket_line:
                    old_id_iva = ticket_line.IdIVA
                    old_porcentaje = ticket_line.PorcentajeIVA

                    ticket_line.IdIVA = id_value
                    ticket_line.PorcentajeIVA = float(value)

                    current_app.logger.info(f"🎯 AGGIORNAMENTO DIRETTO IVA LINEA: PorcentajeIVA {old_porcentaje}→{value}, IdIVA {old_id_iva}→{id_value}")

                    # Salva immediatamente le modifiche alla linea del ticket
                    db.session.commit()
                    current_app.logger.info(f"💾 IVA linea ticket salvata: IdIVA={id_value}, PorcentajeIVA={value}")

            # Poi aggiorna anche l'articolo collegato per mantenere la consistenza
            current_app.logger.info(f"🔄 Ora aggiorno anche l'articolo collegato...")
            update_article_iva_from_ticket_line(ticket_id, line_id, field, value)
            current_app.logger.info(f"✅ Articolo aggiornato per consistenza")

            # IMPORTANTE: Ritorna True perché abbiamo già gestito completamente l'IVA
            return True

        # Gestione speciale per prezzo senza IVA - aggiorna anche l'articolo collegato
        if field == 'precio_sin_iva':
            # Prima aggiorna la linea del ticket
            # Il salvataggio normale della linea avverrà dopo questo controllo

            # Poi aggiorna anche l'articolo collegato per mantenere la consistenza
            update_article_precio_sin_iva_from_ticket_line(ticket_id, line_id, value)

        
        if db_field is None:
            current_app.logger.error(f"❌ Campo non mappato: {field}")
            return False
        
        # VERO SALVATAGGIO NEL DATABASE (TicketLine già importato sopra)
        
        # Trova la linea del ticket nel database
        ticket_line = TicketLine.query.filter_by(
            IdTicket=ticket_id,
            IdLineaTicket=line_id
        ).first()
        
        if not ticket_line:
            current_app.logger.error(f"❌ Linea ticket non trovata: ticket={ticket_id}, linea={line_id}")
            return False
        
        current_app.logger.info(f"✅ Linea ticket trovata: {ticket_line}")
        
        # Aggiorna il campo specificato
        current_app.logger.info(f"🔍 Tentativo aggiornamento campo {db_field} nel modello TicketLine")
        current_app.logger.info(f"🔍 Campo {db_field} esiste nel modello: {hasattr(ticket_line, db_field)}")

        if hasattr(ticket_line, db_field):
            old_value = getattr(ticket_line, db_field)
            setattr(ticket_line, db_field, value)

            current_app.logger.info(f"💾 AGGIORNAMENTO REALE: {db_field} da {old_value} a {value}")

            # Log specifico per IVA della linea del ticket
            if db_field in ['IdIVA', 'PorcentajeIVA']:
                current_app.logger.info(f"🎯 IVA LINEA TICKET: {db_field} = {value} (ticket={ticket_id}, linea={line_id})")

            # Log specifico per campo Importe
            if db_field == 'Importe':
                current_app.logger.info(f"💰 IMPORTO TOTALE LINEA: {db_field} = {value} (ticket={ticket_id}, linea={line_id})")

            # Salva nel database
            db.session.commit()

            # Verifica che il salvataggio sia andato a buon fine
            db.session.refresh(ticket_line)
            new_value = getattr(ticket_line, db_field)

            current_app.logger.info(f"✅ Linea ticket salvata nel database: {db_field} = {new_value}")

            if db_field in ['IdIVA', 'PorcentajeIVA']:
                current_app.logger.info(f"🎯 CONFERMA IVA LINEA: {db_field} confermato a {new_value}")

            if db_field == 'Importe':
                current_app.logger.info(f"💰 CONFERMA IMPORTO: {db_field} confermato a {new_value}")

            return True
            
        else:
            current_app.logger.error(f"❌ Campo {db_field} non esiste nel modello TicketLine")
            # Lista tutti i campi disponibili per debug
            available_fields = [attr for attr in dir(ticket_line) if not attr.startswith('_') and not callable(getattr(ticket_line, attr))]
            current_app.logger.info(f"ℹ️ Campi disponibili nel modello TicketLine: {available_fields}")
            return False
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore aggiornamento linea ticket: {str(e)}")
        # Rollback in caso di errore
        try:
            db.session.rollback()
        except:
            pass
        return False

def update_article_precio_sin_iva_from_ticket_line(ticket_id, line_id, field, value):
    """
    Aggiorna il prezzo senza IVA dell'articolo collegato quando viene modificato nella linea del ticket.
    Questa funzione mantiene la consistenza tra il prezzo nella linea del ticket e nell'articolo.
    """
    try:
        from app.models import TicketLine, Product

        current_app.logger.info(f"🔍 Aggiornamento articolo PrecioSinIVA da ticket: ticket={ticket_id}, linea={line_id}, campo={field}, valore={value}")

        # Trova la linea del ticket per ottenere l'IdArticulo
        ticket_line = TicketLine.query.filter_by(
            IdTicket=ticket_id,
            IdLineaTicket=line_id
        ).first()

        if not ticket_line:
            current_app.logger.warning(f"⚠️ Linea ticket non trovata per aggiornamento articolo: {ticket_id}.{line_id}")
            return

        if not ticket_line.IdArticulo:
            current_app.logger.warning(f"⚠️ Articolo non collegato alla linea ticket: {ticket_id}.{line_id}")
            return

        # Trova l'articolo collegato
        product = Product.query.filter_by(IdArticulo=ticket_line.IdArticulo).first()

        if not product:
            current_app.logger.warning(f"⚠️ Articolo non trovato: IdArticulo={ticket_line.IdArticulo}")
            return

        # Aggiorna il prezzo senza IVA dell'articolo
        old_precio_sin_iva = getattr(product, 'PrecioSinIVA', None)
        product.PrecioSinIVA = float(value)

        from app.models import db
        db.session.commit()

        current_app.logger.info(f"✅ Articolo aggiornato: PrecioSinIVA {old_precio_sin_iva} → {value} per articolo {product.IdArticulo}")

    except Exception as e:
        current_app.logger.error(f"❌ Errore aggiornamento articolo PrecioSinIVA: {str(e)}")
        # Non rilanciare l'errore per non bloccare il salvataggio della linea del ticket
        raise

def update_article_iva_from_ticket_line(ticket_id, line_id, field, value):
    """
    Aggiorna l'IVA dell'articolo collegato alla linea del ticket
    Restituisce True se il salvataggio è andato a buon fine
    """
    try:
        current_app.logger.info(f"🔍 Aggiornamento IVA articolo da ticket: ticket={ticket_id}, linea={line_id}, campo={field}, valore={value}")
        current_app.logger.info(f"📊 Tipo valore ricevuto: {type(value)}")
        
        from app.models import TicketLine, Article, db
        
        # Trova la linea del ticket per ottenere l'IdArticulo
        ticket_line = TicketLine.query.filter_by(
            IdTicket=ticket_id,
            IdLineaTicket=line_id
        ).first()
        
        if not ticket_line:
            current_app.logger.error(f"❌ Linea ticket non trovata: ticket={ticket_id}, linea={line_id}")
            return False
        
        if not ticket_line.IdArticulo:
            current_app.logger.error(f"❌ Linea ticket non ha articolo collegato: ticket={ticket_id}, linea={line_id}")
            return False
        
        # Trova l'articolo
        article = Article.query.filter_by(IdArticulo=ticket_line.IdArticulo).first()
        
        if not article:
            current_app.logger.error(f"❌ Articolo non trovato: {ticket_line.IdArticulo}")
            return False
        
        current_app.logger.info(f"✅ Articolo trovato: {article.IdArticulo} - {article.Descripcion}")
        
        # Converti il valore IVA se necessario
        old_iva = article.IdIva
        if field == 'id_iva':
            # I valori che arrivano sono già ID corretti dal frontend
            # 1 = 4%, 2 = 10%, 3 = 22%, 4 = Esente IVA
            article.IdIva = int(value)
            current_app.logger.info(f"💾 Aggiornamento IdIva articolo {article.IdArticulo}: {old_iva} → {value} (ID già corretto)")
        elif field == 'porcentaje_iva':
            # porcentaje_iva: 4, 10, 22 -> id_iva: 1, 2, 3
            percentage_to_id = {4: 1, 10: 2, 22: 3}
            id_iva = percentage_to_id.get(int(value), 1)  # Default a 4% se valore non riconosciuto
            article.IdIva = id_iva
            current_app.logger.info(f"💾 Aggiornamento IdIva articolo {article.IdArticulo} da percentuale {value}% → IdIva {id_iva} (era {old_iva})")
        
        # Salva le modifiche
        db.session.commit()

        # Verifica che il salvataggio sia andato a buon fine
        db.session.refresh(article)
        current_app.logger.info(f"✅ IVA articolo {article.IdArticulo} aggiornata con successo: IdIva={old_iva} → {article.IdIva}")

        # Log di conferma per debugging
        if old_iva != article.IdIva:
            current_app.logger.info(f"🎯 CONFERMA: IVA articolo {article.IdArticulo} cambiata da {old_iva} a {article.IdIva}")
        else:
            current_app.logger.warning(f"⚠️ ATTENZIONE: IVA articolo {article.IdArticulo} non è cambiata (rimane {article.IdIva})")
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore durante l'aggiornamento IVA articolo: {str(e)}")
        # Rollback in caso di errore
        try:
            db.session.rollback()
        except:
            pass
        return False

def update_ticket_header_in_database(ticket_id, field, value):
    """
    Aggiorna l'header del ticket nel database
    Restituisce True se il salvataggio è andato a buon fine
    """
    try:
        current_app.logger.info(f"🔍 Tentativo aggiornamento header DB: ticket={ticket_id}, campo={field}, valore={value}")

        # SICUREZZA: Controlla se è un ticket manuale (ID negativo) - non dovrebbe mai accadere
        if ticket_id < 0:
            current_app.logger.error(f"❌ SICUREZZA: Tentativo di salvare ticket manuale ({ticket_id}) nel database!")
            return False

        # VERO SALVATAGGIO NEL DATABASE
        from app.models import TicketHeader, db
        
        # Trova il ticket header
        ticket = TicketHeader.query.filter_by(IdTicket=ticket_id).first()
        
        if not ticket:
            current_app.logger.error(f"❌ Ticket header non trovato: {ticket_id}")
            return False
        
        current_app.logger.info(f"✅ Ticket header trovato: {ticket}")
        
        # Per ora gestiamo solo alcuni campi header generici
        if field == 'total_ticket':
            # Il totale del ticket non è memorizzato direttamente nell'header
            # viene calcolato dalla somma delle linee
            current_app.logger.info(f"💡 Totale ticket viene calcolato dalle linee, non memorizzato in header")
            return True
        else:
            current_app.logger.warning(f"⚠️ Campo header non gestito: {field}")
            return True  # Non errore, semplicemente non gestito
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore aggiornamento ticket header: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return False

@ddt_bp.route('/api/update_ticket_price', methods=['POST'])
@login_required
def api_update_ticket_price():
    """API to update the total price of a ticket in preview mode"""
    try:
        data = request.get_json()
        ticket_id = data.get('ticket_id')
        new_price = data.get('new_price')
        
        # Validazione input
        if not ticket_id:
            return jsonify({'success': False, 'message': 'ID ticket mancante'})
        
        if new_price is None or new_price < 0:
            return jsonify({'success': False, 'message': 'Prezzo non valido'})
        
        # Verifica che il ticket esista
        ticket = TicketHeader.query.get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket non trovato'})
        
        # Per ora, salviamo il prezzo modificato in sessione o in una tabella temporanea
        # In questo caso, utilizziamo la sessione Flask per mantenere i prezzi modificati
        from flask import session
        
        if 'modified_ticket_prices' not in session:
            session['modified_ticket_prices'] = {}
        
        session['modified_ticket_prices'][str(ticket_id)] = float(new_price)
        session.modified = True
        
        current_app.logger.info(f"💰 Prezzo ticket #{ticket_id} aggiornato a €{new_price:.2f}")
        
        return jsonify({
            'success': True, 
            'message': 'Prezzo aggiornato con successo',
            'ticket_id': ticket_id,
            'new_price': new_price
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore aggiornamento prezzo ticket: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Errore interno: {str(e)}'
        }), 500

@ddt_bp.route('/api/get_modified_prices', methods=['GET'])
@login_required
def api_get_modified_prices():
    """API to get all modified ticket prices from session"""
    from flask import session
    
    modified_prices = session.get('modified_ticket_prices', {})
    return jsonify({
        'success': True,
        'modified_prices': modified_prices
    })

@ddt_bp.route('/api/clear_modified_prices', methods=['POST'])
@login_required
def api_clear_modified_prices():
    """API to clear all modified ticket prices from session"""
    from flask import session
    
    if 'modified_ticket_prices' in session:
        del session['modified_ticket_prices']
        session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Prezzi modificati cancellati'
    })

@ddt_bp.route('/api/get_manual_ticket_modifications', methods=['GET'])
@login_required
def api_get_manual_ticket_modifications():
    """API to retrieve manual ticket modifications from session"""
    from flask import session

    try:
        manual_modifications = session.get('manual_ticket_modifications', {})

        current_app.logger.info(f"🔍 Recupero modifiche ticket manuali: {len(manual_modifications)} modifiche trovate")

        return jsonify({
            'success': True,
            'modifications': manual_modifications,
            'count': len(manual_modifications)
        })

    except Exception as e:
        current_app.logger.error(f"❌ Errore nel recupero modifiche ticket manuali: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore nel recupero delle modifiche'
        }), 500

@ddt_bp.route('/api/update_ticket_field', methods=['POST'])
@login_required
def api_update_ticket_field():
    """API to update any field of a ticket line in preview mode"""
    from flask import session
    
    try:
        # Log della richiesta ricevuta
        current_app.logger.info(f"🔍 DEBUG: Richiesta update_ticket_field ricevuta")
        current_app.logger.info(f"🔍 DEBUG: Content-Type: {request.content_type}")
        current_app.logger.info(f"🔍 DEBUG: Raw data: {request.get_data()}")
        
        data = request.get_json()
        current_app.logger.info(f"🔍 DEBUG: Parsed JSON data: {data}")
        
        if not data:
            current_app.logger.error(f"❌ DEBUG: Dati non forniti o JSON non valido")
            return jsonify({
                'success': False,
                'message': 'Dati non forniti'
            }), 400
        
        ticket_id = data.get('ticket_id')
        line_id = data.get('line_id')
        field = data.get('field')
        value = data.get('value')
        
        # Log dei parametri estratti
        current_app.logger.info(f"🔍 DEBUG: Parametri estratti:")
        current_app.logger.info(f"  - ticket_id: {ticket_id} (type: {type(ticket_id)})")
        current_app.logger.info(f"  - line_id: {line_id} (type: {type(line_id)})")
        current_app.logger.info(f"  - field: {field} (type: {type(field)})")
        current_app.logger.info(f"  - value: {value} (type: {type(value)})")
        
        if not all([ticket_id, field, value is not None]):
            current_app.logger.error(f"❌ DEBUG: Parametri mancanti - ticket_id: {ticket_id}, field: {field}, value: {value}")
            return jsonify({
                'success': False,
                'message': 'Parametri mancanti: ticket_id, field e value sono richiesti'
            }), 400
        
        # Validate field name
        allowed_fields = ['descrizione', 'codice', 'peso_quantita', 'prezzo_unitario', 'prezzo_totale', 'importo_iva', 'data_scadenza', 'id_iva', 'porcentaje_iva', 'texto_lote', 'comportamiento', 'precio_sin_iva', 'ImporteSinIVASinDtoL']

        current_app.logger.info(f"🔍 CAMPI PERMESSI: {allowed_fields}")
        current_app.logger.info(f"🔍 CAMPO RICEVUTO: '{field}'")
        current_app.logger.info(f"🔍 DEBUG: Validazione campo '{field}' contro campi permessi: {allowed_fields}")
        
        if field not in allowed_fields:
            current_app.logger.error(f"❌ DEBUG: Campo non valido: '{field}'. Campi permessi: {allowed_fields}")
            return jsonify({
                'success': False,
                'message': f'Campo non valido: {field}. Campi permessi: {", ".join(allowed_fields)}'
            }), 400
        
        # Initialize session storage for modified fields
        if 'modified_ticket_fields' not in session:
            session['modified_ticket_fields'] = {}
        
        # Create unique key for this field
        field_key = f"{ticket_id}_{line_id}_{field}" if line_id else f"{ticket_id}_{field}"
        
        # Validate and convert value based on field type
        current_app.logger.info(f"🔍 PRIMA DELLA VALIDAZIONE: field={field}, value={value} (type: {type(value)})")

        if field in ['prezzo_unitario', 'prezzo_totale', 'importo_iva']:
            try:
                value = float(value)
                if value < 0:
                    return jsonify({
                        'success': False,
                        'message': 'Il prezzo non può essere negativo'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Prezzo non valido'
                }), 400
        elif field == 'peso_quantita':
            try:
                value = float(value)
                if value <= 0:
                    return jsonify({
                        'success': False,
                        'message': 'Peso/quantità deve essere maggiore di zero'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Peso/quantità non valido'
                }), 400
        elif field in ['descrizione', 'codice']:
            value = str(value).strip()
            if not value:
                return jsonify({
                    'success': False,
                    'message': f'{field.capitalize()} non può essere vuoto'
                }), 400
        elif field == 'data_scadenza':
            # Validate date format if provided
            if value:
                try:
                    from datetime import datetime as dt
                    dt.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return jsonify({
                        'success': False,
                        'message': 'Formato data non valido (YYYY-MM-DD)'
                    }), 400
        elif field in ['id_iva', 'porcentaje_iva']:
            try:
                value = int(value)
                if field == 'id_iva':
                    # I valori che arrivano sono già ID corretti dal frontend
                    # 1 = 4%, 2 = 10%, 3 = 22%, 4 = Esente IVA
                    if value not in [1, 2, 3, 4]:
                        return jsonify({
                            'success': False,
                            'message': 'IVA non valida. Valori permessi: ID 1 (4%), 2 (10%), 3 (22%), 4 (Esente)'
                        }), 400
                    current_app.logger.info(f"✅ IVA ID ricevuto: {value} (1=4%, 2=10%, 3=22%, 4=Esente)")
                elif field == 'porcentaje_iva' and value not in [4, 10, 22]:
                    return jsonify({
                        'success': False,
                        'message': 'Percentuale IVA non valida. Valori permessi: 4, 10, 22'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Valore IVA non valido'
                }), 400
        elif field == 'comportamiento':
            try:
                value = int(value)
                if value not in [0, 1]:
                    return jsonify({
                        'success': False,
                        'message': 'Comportamiento non valido. Valori permessi: 0 (unità), 1 (peso)'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': 'Valore comportamiento non valido'
                }), 400
        elif field == 'texto_lote':
            # Campo testo libero, accetta qualsiasi stringa
            value = str(value).strip()

        current_app.logger.info(f"🔍 DOPO LA VALIDAZIONE: field={field}, value={value} (type: {type(value)})")

        # CONTROLLA SE È UN TICKET MANUALE (ID negativo)
        try:
            ticket_id_int = int(ticket_id)
            is_manual_ticket = ticket_id_int < 0
        except (ValueError, TypeError):
            current_app.logger.error(f"❌ ID ticket non valido: {ticket_id} (type: {type(ticket_id)})")
            return jsonify({
                'success': False,
                'message': 'ID ticket non valido'
            }), 400

        current_app.logger.info(f"🔍 TIPO TICKET: {'MANUALE (localStorage)' if is_manual_ticket else 'DATABASE'} - ID: {ticket_id_int}")

        if is_manual_ticket:
            # GESTIONE TICKET MANUALE - SALVATAGGIO SOLO IN SESSION
            current_app.logger.info(f"💾 Salvataggio ticket manuale in session: {field} = {value}")

            # Salva in session per i ticket manuali
            if 'manual_ticket_modifications' not in session:
                session['manual_ticket_modifications'] = {}

            field_key = f"{ticket_id_int}_{line_id}_{field}" if line_id else f"{ticket_id_int}_{field}"
            from datetime import datetime as dt
            session['manual_ticket_modifications'][field_key] = {
                'ticket_id': ticket_id_int,
                'line_id': line_id,
                'field': field,
                'value': value,
                'timestamp': dt.now().isoformat(),
                'saved_to_db': False,
                'is_manual': True
            }
            session.modified = True

            current_app.logger.info(f"✅ Campo {field} salvato in session per ticket manuale {ticket_id_int}, linea {line_id}: {value}")

            return jsonify({
                'success': True,
                'message': f'{field.replace("_", " ").title()} salvato in session (ticket manuale)',
                'ticket_id': ticket_id_int,
                'line_id': line_id,
                'field': field,
                'value': value,
                'saved_to_db': False,
                'is_manual': True
            })

        # SALVATAGGIO DIRETTO NEL DATABASE (solo per ticket non manuali)
        try:
            current_app.logger.info(f"💾 Salvataggio diretto nel database: {field} = {value}")

            if line_id:
                # Aggiorna una linea specifica del ticket
                success = update_ticket_line_in_database(ticket_id_int, line_id, field, value)
            else:
                # Aggiorna il ticket header (es. totale ticket)
                success = update_ticket_header_in_database(ticket_id_int, field, value)
            
            if success:
                current_app.logger.info(f"✅ Campo {field} salvato nel database per ticket {ticket_id_int}, linea {line_id}: {value}")

                # Mantieni traccia in sessione per debug (opzionale)
                if 'db_saved_fields' not in session:
                    session['db_saved_fields'] = {}

                field_key = f"{ticket_id_int}_{line_id}_{field}" if line_id else f"{ticket_id_int}_{field}"
                from datetime import datetime as dt
                session['db_saved_fields'][field_key] = {
                    'ticket_id': ticket_id_int,
                    'line_id': line_id,
                    'field': field,
                    'value': value,
                    'timestamp': dt.now().isoformat(),
                    'saved_to_db': True
                }
                session.modified = True
                
                return jsonify({
                    'success': True,
                    'message': f'{field.replace("_", " ").title()} salvato nel database',
                    'ticket_id': ticket_id_int,
                    'line_id': line_id,
                    'field': field,
                    'value': value,
                    'saved_to_db': True
                })
            else:
                current_app.logger.error(f"❌ Errore nel salvataggio del campo {field} nel database")
                return jsonify({
                    'success': False,
                    'message': 'Errore nel salvataggio del campo nel database'
                }), 500
                
        except Exception as db_error:
            current_app.logger.error(f"❌ Errore database durante salvataggio: {str(db_error)}")
            return jsonify({
                'success': False,
                'message': f'Errore database: {str(db_error)}'
            }), 500
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore aggiornamento campo ticket: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }), 500

@ddt_bp.route('/api/get_modified_fields', methods=['GET'])
@login_required
def api_get_modified_fields():
    """API to get all modified ticket fields from session"""
    from flask import session
    
    modified_fields = session.get('modified_ticket_fields', {})
    return jsonify({
        'success': True,
        'modified_fields': modified_fields
    })

@ddt_bp.route('/api/sync_modifications', methods=['POST'])
@login_required
def api_sync_modifications():
    """API to sync all modifications from localStorage to database"""
    from flask import session
    
    try:
        data = request.get_json()
        if not data or 'modifications' not in data:
            return jsonify({
                'success': False,
                'message': 'Dati delle modifiche non forniti'
            }), 400
        
        modifications = data['modifications']
        
        if not modifications:
            return jsonify({
                'success': False,
                'message': 'Nessuna modifica da sincronizzare'
            })
        
        # Raggruppa le modifiche per ticket
        ticket_modifications = {}
        for mod_key, mod_data in modifications.items():
            ticket_id = mod_data['ticketId']
            if ticket_id not in ticket_modifications:
                ticket_modifications[ticket_id] = []
            ticket_modifications[ticket_id].append(mod_data)
        
        # Applica le modifiche al database
        success_count = 0
        error_count = 0
        
        for ticket_id, mods in ticket_modifications.items():
            try:
                # Qui implementiamo la logica di aggiornamento del database
                # Per ora salviamo in sessione come backup
                if 'synced_modifications' not in session:
                    session['synced_modifications'] = {}
                
                session['synced_modifications'][ticket_id] = mods
                session.modified = True
                
                success_count += len(mods)
                current_app.logger.info(f"✅ Sincronizzate {len(mods)} modifiche per ticket {ticket_id}")
                
            except Exception as e:
                error_count += len(mods)
                current_app.logger.error(f"❌ Errore sincronizzazione ticket {ticket_id}: {str(e)}")
        
        if error_count == 0:
            return jsonify({
                'success': True,
                'message': f'Tutte le {success_count} modifiche sincronizzate con successo'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Sincronizzate {success_count} modifiche, {error_count} errori'
            }), 207
            
    except Exception as e:
        current_app.logger.error(f"❌ Errore generale sincronizzazione: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Errore interno del server'
        }), 500


@ddt_bp.route('/api/preview/refresh_ticket_data', methods=['GET'])
@login_required
def api_refresh_ticket_data():
    """API per ottenere i dati più aggiornati dei ticket per un cliente"""
    try:
        cliente_id = request.args.get('cliente_id')
        if not cliente_id:
            return jsonify({
                'success': False,
                'error': 'ID cliente richiesto'
            }), 400
        
        # Log della richiesta
        current_app.logger.info(f"🔄 Refresh dati ticket per cliente {cliente_id}")
        
        # Recupera i ticket più recenti dal database
        # Utilizziamo la stessa logica della preview
        from sqlalchemy import text
        
        # Query per ottenere tutti i ticket attivi per il cliente
        query = text("""
            SELECT DISTINCT 
                t.IdTicket,
                t.NumTicket,
                t.Fecha,
                t.id_empresa,
                tl.IdLineaTicket as id_linea_ticket,
                tl.IdArticulo as id_articulo,
                tl.Descripcion as descripcion,
                tl.Peso as peso,
                tl.Precio as precio,
                (tl.Peso * tl.Precio) as importe,
                tl.comportamiento,
                tl.FechaCaducidad as fecha_caducidad,
                tl.TextoLote as texto_lote,
                COALESCE(a.IdIva, 1) as id_iva
            FROM Ticket t
            INNER JOIN TicketLine tl ON t.IdTicket = tl.IdTicket
            LEFT JOIN Articulo a ON tl.IdArticulo = a.IdArticulo
            WHERE t.IdCliente = :cliente_id
            AND t.Estado = 'A'
            AND tl.Peso > 0
            ORDER BY t.IdTicket DESC, tl.IdLineaTicket
            LIMIT 200
        """)
        
        result = db.session.execute(query, {'cliente_id': cliente_id})
        rows = result.fetchall()
        
        # Raggruppa i risultati per ticket
        tickets_dict = {}
        for row in rows:
            ticket_id = row.IdTicket
            
            if ticket_id not in tickets_dict:
                tickets_dict[ticket_id] = {
                    'ticket': {
                        'IdTicket': row.IdTicket,
                        'NumTicket': row.NumTicket,
                        'Fecha': row.Fecha.strftime('%Y-%m-%d %H:%M:%S') if row.Fecha else '',
                        'id_empresa': row.id_empresa
                    },
                    'lines': [],
                    'ticket_total': 0
                }
            
            # Aggiungi la linea
            line_data = {
                'id_linea_ticket': row.id_linea_ticket,
                'id_articulo': row.id_articulo,
                'descripcion': row.descripcion or 'Prodotto',
                'peso': float(row.peso) if row.peso else 0,
                'precio': float(row.precio) if row.precio else 0,
                'importe': float(row.importe) if row.importe else 0,
                'comportamiento': int(row.comportamiento) if row.comportamiento else 0,
                'fecha_caducidad': row.fecha_caducidad.strftime('%Y-%m-%d') if row.fecha_caducidad else None,
                'texto_lote': row.texto_lote or '',
                'vat_rate': get_vat_rate_from_iva_id(row.id_iva)
            }
            
            tickets_dict[ticket_id]['lines'].append(line_data)
            tickets_dict[ticket_id]['ticket_total'] += line_data['importe']
        
        # Converti in lista
        preview_data = list(tickets_dict.values())
        
        current_app.logger.info(f"✅ Refresh completato: {len(preview_data)} ticket trovati")
        
        return jsonify({
            'success': True,
            'preview_data': preview_data,
            'count': len(preview_data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"❌ Errore refresh dati ticket: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': 'Errore interno del server',
            'details': str(e) if current_app.debug else None
        }), 500

def get_vat_rate_from_iva_id(iva_id):
    """Converte l'ID IVA nel rate corrispondente"""
    iva_mapping = {
        1: 0.04,  # 4%
        2: 0.10,  # 10%
        3: 0.22,  # 22%
        4: 0.00   # 0%
    }
    return iva_mapping.get(iva_id, 0.04)  # Default 4%

@ddt_bp.route('/api/clear_modified_fields', methods=['POST'])
@login_required
def api_clear_modified_fields():
    """API to clear all modified ticket fields from session"""
    from flask import session
    
    if 'modified_ticket_fields' in session:
        del session['modified_ticket_fields']
        session.modified = True
    
    return jsonify({
        'success': True,
        'message': 'Campi modificati cancellati'
    })

@ddt_bp.route('/api/check_article_iva/<int:article_id>', methods=['GET'])
@login_required
def api_check_article_iva(article_id):
    """API to check the current IVA value of an article (for debugging)"""
    try:
        from app.models import Article

        article = Article.query.filter_by(IdArticulo=article_id).first()

        if not article:
            return jsonify({
                'success': False,
                'message': f'Articolo {article_id} non trovato'
            }), 404

        return jsonify({
            'success': True,
            'article_id': article.IdArticulo,
            'descripcion': article.Descripcion,
            'current_iva': article.IdIva,
            'iva_description': {
                1: '4%',
                2: '10%',
                3: '22%',
                4: 'Esente IVA'
            }.get(article.IdIva, 'Sconosciuto')
        })

    except Exception as e:
        current_app.logger.error(f"❌ Errore controllo IVA articolo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }), 500

@ddt_bp.route('/api/check_ticket_line_iva/<int:ticket_id>/<int:line_id>', methods=['GET'])
@login_required
def api_check_ticket_line_iva(ticket_id, line_id):
    """API to check the current IVA value of a ticket line (for debugging)"""
    try:
        from app.models import TicketLine

        ticket_line = TicketLine.query.filter_by(
            IdTicket=ticket_id,
            IdLineaTicket=line_id
        ).first()

        if not ticket_line:
            return jsonify({
                'success': False,
                'message': f'Linea ticket {line_id} del ticket {ticket_id} non trovata'
            }), 404

        return jsonify({
            'success': True,
            'ticket_id': ticket_line.IdTicket,
            'line_id': ticket_line.IdLineaTicket,
            'article_id': ticket_line.IdArticulo,
            'descripcion': ticket_line.Descripcion,
            'current_iva': ticket_line.IdIVA,
            'porcentaje_iva': float(ticket_line.PorcentajeIVA) if ticket_line.PorcentajeIVA else None,
            'precio_sin_iva': float(ticket_line.PrecioSinIVA) if ticket_line.PrecioSinIVA else None,
            'iva_description': {
                1: '4%',
                2: '10%',
                3: '22%',
                4: 'Esente IVA'
            }.get(ticket_line.IdIVA, 'Sconosciuto')
        })

    except Exception as e:
        current_app.logger.error(f"❌ Errore controllo IVA linea ticket: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore interno: {str(e)}'
        }), 500

@ddt_bp.route('/modify/<int:ddt_id>', methods=['GET'])
@login_required
def modify(ddt_id):
    """Modify existing DDT using preview interface"""
    # Controllo permessi personalizzato per DDT
    if not check_ddt_permissions():
        flash('Non hai i permessi per modificare DDT. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('index'))

    try:
        # Get DDT header
        ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()

        # Get client and company info
        cliente = Client.query.get_or_404(ddt.IdCliente)
        empresa = Company.query.get_or_404(ddt.IdEmpresa)

        # Get all lines from this DDT
        lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt_id).all()

        if not lines:
            flash('Nessuna linea trovata nel DDT selezionato', 'warning')
            return redirect(url_for('ddt.detail', ddt_id=ddt_id))

        # Convert DDT lines to preview format
        preview_data = []

        # Group lines by some identifier (since DDT doesn't have tickets, we'll create virtual tickets)
        # We'll group by a sequential number for simplicity
        ticket_counter = 1

        # Process each line
        for line in lines:
            # Get product info
            product = Article.query.get(line.IdArticulo)

            # Calculate prices
            line_price_without_vat = float(line.PrecioSinIVA or 0)
            line_price_with_vat = float(line.PrecioConIVASinDtoL or 0)

            # Calculate VAT rate
            vat_rate = 0
            if line.PorcentajeIVA:
                vat_rate = float(line.PorcentajeIVA) / 100

            # If price with VAT is not available, calculate it from price without VAT
            if line_price_with_vat == 0 and line_price_without_vat > 0:
                line_price_with_vat = line_price_without_vat * (1 + vat_rate)

            # Apply discount to prices
            discount_rate = float(line.Descuento or 0) / 100
            if discount_rate > 0:
                line_price_without_vat = line_price_without_vat * (1 - discount_rate)
                line_price_with_vat = line_price_with_vat * (1 - discount_rate)

            # Calculate amounts
            peso_value = float(line.Peso or 0)
            comportamiento = getattr(line, 'Comportamiento', 0)

            if comportamiento == 1:  # Weight-based
                line_amount = peso_value * line_price_without_vat
                line_amount_with_vat = peso_value * line_price_with_vat
            else:  # Unit-based
                line_amount = peso_value * line_price_without_vat
                line_amount_with_vat = peso_value * line_price_with_vat

            # Create virtual ticket data
            ticket_lines_data = [{
                'id_linea_ticket': line.IdLineaAlbaran,  # Use IdLineaAlbaran as line identifier
                'id_ticket': ticket_counter,  # Virtual ticket ID
                'id_articulo': line.IdArticulo,
                'descripcion': line.Descripcion,
                'peso': line.Peso,
                'quantita': line.Peso,  # Quantity field for ticket table
                'precio': line_price_with_vat,
                'precio_senza_iva': line_price_without_vat,
                'precio_con_iva': line_price_with_vat,
                'precio_standard': line_price_without_vat,
                'precio_listino': line_price_without_vat,
                'has_custom_price': False,
                'price_difference': 0,
                'importe': line_amount,
                'importe_con_iva': line_amount_with_vat,
                'desquento': float(line.Descuento or 0),  # Discount field for ticket table
                'fecha_caducidad': line.FechaCaducidad,
                'comportamiento': comportamiento,
                'id_iva': line.IdIVA or 1,
                'vat_rate': vat_rate,
                'porcentaje_iva': int(float(line.PorcentajeIVA or 0)),
                'texto_lote': line.TextoLote
            }]

            # Create virtual ticket
            virtual_ticket = {
                'IdTicket': ticket_counter,
                'NumTicket': f"DDT-{ddt.NumAlbaran}-{ticket_counter}",
                'Fecha': ddt.Fecha.strftime('%d/%m/%Y %H:%M') if ddt.Fecha else None,
                'IdEmpresa': ddt.IdEmpresa,
                'IdTienda': ddt.IdTienda,
                'IdBalanzaMaestra': ddt.IdBalanzaMaestra,
                'IdBalanzaEsclava': ddt.IdBalanzaEsclava,
                'TipoVenta': line.TipoVenta or 0
            }

            preview_data.append({
                'ticket': virtual_ticket,
                'ticket_info': {
                    'id_ticket': ticket_counter,
                    'id_empresa': ddt.IdEmpresa
                },
                'lines': ticket_lines_data,
                'ticket_total': line_amount_with_vat
            })

            ticket_counter += 1

        # Convert to JSON for JavaScript
        selected_tickets_json = json.dumps([{
            'id_ticket': item['ticket']['IdTicket'],
            'id_empresa': item['ticket']['IdEmpresa']
        } for item in preview_data])

        # Ottieni informazioni listino del cliente se il modulo è abilitato
        listini_enabled = False
        has_dedicated_listino = False
        listino_info = None

        try:
            from app.modules_config import modules_manager
            listini_enabled = modules_manager.is_module_enabled('listini')
        except Exception as e:
            current_app.logger.warning(f"⚠️ Impossibile verificare moduli abilitati: {str(e)}")

        if listini_enabled and cliente.IdListino:
            try:
                from app.models import ListinoPrezziHeader
                listino = ListinoPrezziHeader.query.get(cliente.IdListino)
                if listino:
                    listino_info = {
                        'id': listino.IdListino,
                        'nome': listino.NomeListino,
                        'descrizione': listino.Descrizione,
                        'has_custom_prices': True
                    }
                    has_dedicated_listino = True
                    current_app.logger.info(f"🏷️  Cliente {cliente.Nombre} ha listino personalizzato: {listino.NomeListino}")
                else:
                    current_app.logger.warning(f"⚠️  Cliente {cliente.Nombre} ha IdListino={cliente.IdListino} ma listino non trovato")
            except Exception as e:
                current_app.logger.warning(f"⚠️ Errore caricamento informazioni listino: {str(e)}")

        # Create form for final DDT creation (needed by template)
        from app.forms import DDTCreateForm
        create_form = DDTCreateForm()

        # Render preview template with DDT data
        return render_template('ddt/preview.html',
                             cliente=cliente,
                             empresa=empresa,
                             preview_data=preview_data,
                             selected_tickets_json=selected_tickets_json,
                             from_task=False,
                             from_warehouse=False,
                             from_modify=True,  # Flag to indicate we're modifying existing DDT
                             ddt_id=ddt_id,
                             create_form=create_form,
                             listini_enabled=listini_enabled,
                             has_dedicated_listino=has_dedicated_listino,
                             listino_info=listino_info)

    except Exception as e:
        current_app.logger.error(f"❌ Errore caricamento modifica DDT {ddt_id}: {str(e)}")
        flash('Errore durante il caricamento della pagina di modifica', 'danger')
        return redirect(url_for('ddt.detail', ddt_id=ddt_id))

@ddt_bp.route('/api/save_modifications/<int:ddt_id>', methods=['POST'])
@login_required
def api_save_ddt_modifications(ddt_id):
    """API to save DDT modifications to DAT_ALBARAN_LINEA table"""
    try:
        # Controllo permessi personalizzato per DDT
        if not check_ddt_permissions():
            return jsonify({
                'success': False,
                'message': 'Non hai i permessi per modificare DDT'
            }), 403

        # Get the modifications data from request
        modifications = request.get_json()
        if not modifications or 'lines' not in modifications:
            return jsonify({
                'success': False,
                'message': 'Dati modifiche non validi'
            }), 400

        # Verify DDT exists
        ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first()
        if not ddt:
            return jsonify({
                'success': False,
                'message': f'DDT {ddt_id} non trovato'
            }), 404

        # Process each line modification
        updated_lines = 0
        for line_data in modifications['lines']:
            try:
                # Find the line by IdLineaAlbaran (which is stored in ticket_id for virtual tickets)
                line_id = line_data.get('ticket_id')
                if not line_id:
                    continue

                # Get the line from database
                line = AlbaranLinea.query.filter_by(
                    IdAlbaran=ddt_id,
                    IdLineaAlbaran=int(line_id)
                ).first()

                if line:
                    # Get values from request data
                    peso = float(line_data.get('peso', line.Peso))
                    precio_con_iva = float(line_data.get('precio', line.PrecioSinIVA))  # This is the price WITH VAT from frontend
                    porcentaje_iva = int(line_data.get('iva', line.PorcentajeIVA or 22))

                    # ✅ CORRECTION: Calculate price WITHOUT VAT from price WITH VAT
                    # The frontend sends price WITH VAT, but we need to store price WITHOUT VAT
                    if porcentaje_iva > 0:
                        # For VAT > 0%, calculate price without VAT: price_with_vat / (1 + vat_rate)
                        vat_rate = porcentaje_iva / 100
                        precio_sin_iva = precio_con_iva / (1 + vat_rate)
                    else:
                        # For VAT = 0% (exempt), price without VAT = price with VAT
                        precio_sin_iva = precio_con_iva

                    # Apply commercial rounding to price without VAT
                    precio_sin_iva = round(precio_sin_iva, 2)

                    # Update line fields with corrected values
                    line.Peso = peso
                    line.PrecioSinIVA = precio_sin_iva  # Store price WITHOUT VAT
                    line.PorcentajeIVA = porcentaje_iva

                    # Recalculate all amounts based on the corrected price without VAT
                    line.ImporteSinIVASinDtoL = peso * precio_sin_iva
                    line.ImporteDelIVAConDtoL = line.ImporteSinIVASinDtoL * (porcentaje_iva / 100)
                    line.ImporteSinIVAConDtoL = line.ImporteSinIVASinDtoL
                    line.ImporteDelIVAConDtoLConDtoTotal = line.ImporteDelIVAConDtoL
                    line.ImporteConIVASinDtoL = line.ImporteSinIVASinDtoL + line.ImporteDelIVAConDtoL
                    line.ImporteSinIVAConDtoLConDtoTotal = line.ImporteSinIVASinDtoL
                    line.ImporteDelRE = 0
                    line.ImporteDelDescuento = 0
                    line.ImporteConDtoTotal = line.ImporteConIVASinDtoL
                    line.TextoLote = line_data.get('texto_lote', line.TextoLote or '')

                    # Handle date fields
                    fecha_caducidad = line_data.get('fecha_caducidad', '')
                    if fecha_caducidad:
                        try:
                            line.FechaCaducidad = datetime.strptime(fecha_caducidad, '%Y-%m-%d').date()
                        except ValueError:
                            pass  # Keep existing date if invalid

                    # Mark as modified
                    line.Modificado = 1
                    line.TimeStamp = datetime.now()

                    updated_lines += 1

                    current_app.logger.info(f"✅ Linea {line.IdLineaAlbaran} aggiornata: peso={line.Peso}, precio_con_iva={precio_con_iva:.2f}, precio_sin_iva={precio_sin_iva:.2f}, iva={porcentaje_iva}%")

            except Exception as e:
                current_app.logger.error(f"❌ Errore aggiornamento linea {line_data.get('ticket_id')}: {str(e)}")
                continue

        # Commit all changes
        db.session.commit()

        current_app.logger.info(f"✅ Modifiche DDT {ddt_id} salvate: {updated_lines} linee aggiornate")

        return jsonify({
            'success': True,
            'message': f'Modifiche salvate con successo. {updated_lines} linee aggiornate.',
            'updated_lines': updated_lines
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ Errore salvataggio modifiche DDT {ddt_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Errore interno del server: {str(e)}'
        }), 500