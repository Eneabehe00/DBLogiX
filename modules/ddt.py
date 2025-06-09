from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, not_, exists
from app.models import db, Client, TicketHeader, TicketLine, Product, Company, AlbaranCabecera, AlbaranLinea, Article
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

ddt_bp = Blueprint('ddt', __name__)

@ddt_bp.route('/')
@login_required
def index():
    """Display a list of all DDTs with enhanced search functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 15  # Aumentato da 10 a 15 per visualizzare più elementi
    search_query = request.args.get('search', '', type=str).strip()
    
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
    
    # Order by date descending
    ddts = ddts_query.order_by(AlbaranCabecera.Fecha.desc()).all()
    
    # Preparare i dati per la visualizzazione
    combined_ddts = []
    
    for ddt in ddts:
        combined_ddts.append({
            'id': ddt.IdAlbaran,
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
    
    return render_template('ddt/index.html', ddts=pagination, search_query=search_query)

@ddt_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new():
    """Step 1: Select a client for the new DDT"""
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
@admin_required
def select_tickets(cliente_id):
    """Step 2: Select tickets to include in the DDT"""
    cliente = Client.query.get_or_404(cliente_id)
    form = DDTTicketFilterForm()
    
    # Get current empresa ID - use first available empresa for demo
    # In a real app, you would get this from the user's session/profile
    empresa = Company.query.first()
    if not empresa:
        flash('Nessuna azienda configurata nel sistema.', 'danger')
        return redirect(url_for('ddt.index'))
    
    id_empresa = empresa.IdEmpresa
    
    # Query for all pending tickets - TicketHeader doesn't have IdCliente attribute
    tickets = TicketHeader.query.filter(
        TicketHeader.Enviado == 0  # Solo ticket pendenti
    ).order_by(TicketHeader.Fecha.desc()).all()
    
    # Also create the create form for the hidden form CSRF token
    create_form = DDTCreateForm()
    
    return render_template('ddt/select_tickets.html', 
                          cliente=cliente, 
                          tickets=tickets, 
                          form=form,
                          create_form=create_form,
                          id_empresa=id_empresa)

@ddt_bp.route('/preview', methods=['POST'])
@login_required
@admin_required
def preview():
    """Step 2.5: Preview DDT before final creation with ability to modify tickets"""
    # Get form data
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
        flash('Nessun ticket selezionato', 'danger')
        if from_task and task_id:
            return redirect(url_for('tasks.view_task', task_id=task_id))
        elif from_warehouse:
            return redirect(url_for('warehouse.scanner'))
        return redirect(url_for('ddt.select_tickets', cliente_id=cliente_id))
    
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
    total_amount = 0
    total_weight = 0
    
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
            SELECT IdLineaTicket, IdTicket, IdArticulo, Descripcion, Peso, FechaCaducidad, comportamiento
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
                    'FechaCaducidad': row[5],
                    'comportamiento': row[6]
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
            
            ticket_total = 0
            ticket_lines_data = []
            
            for line in verified_lines:
                # DEBUG: Log each line
                current_app.logger.info(f"   🔸 Linea {line.IdLineaTicket}: IdTicket={line.IdTicket}, IdArticulo={line.IdArticulo}, Desc={line.Descripcion}")
                
                # Additional verification: ensure line belongs to this ticket
                if line.IdTicket != ticket.IdTicket:
                    current_app.logger.error(f"🚨 ERRORE CRITICO: Linea {line.IdLineaTicket} non appartiene al ticket {ticket.IdTicket}")
                    continue
                
                # Get product info
                product = Product.query.get(line.IdArticulo)
                if product:
                    line_amount = float(line.Peso or 0) * float(product.PrecioConIVA or 0)
                    ticket_total += line_amount
                    
                    ticket_lines_data.append({
                        'id_linea_ticket': line.IdLineaTicket,  # Added for better tracking
                        'id_ticket': line.IdTicket,  # Added for verification
                        'id_articulo': line.IdArticulo,
                        'descripcion': line.Descripcion,
                        'peso': line.Peso,
                        'precio': product.PrecioConIVA,
                        'importe': line_amount,
                        'fecha_caducidad': line.FechaCaducidad
                    })
                else:
                    current_app.logger.warning(f"   ⚠️  Prodotto non trovato per IdArticulo={line.IdArticulo}")
            
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
                'ticket_total': ticket_total
            })
            
            total_amount += ticket_total
            total_weight += sum(float(line.get('peso', 0)) for line in ticket_lines_data)
        else:
            current_app.logger.warning(f"⚠️  Ticket non trovato: ID={ticket_info['id_ticket']}, Empresa={ticket_info['id_empresa']}")
    
    # DEBUG: Final summary
    current_app.logger.info(f"📊 DEBUG: Elaborazione completata - {len(preview_data)} ticket nel preview")
    
    # Get all available tickets for adding more
    available_tickets = TicketHeader.query.filter(
        TicketHeader.Enviado == 0,
        ~TicketHeader.IdTicket.in_([t['id_ticket'] for t in selected_tickets])
    ).order_by(TicketHeader.Fecha.desc()).limit(50).all()
    
    # Create form for final DDT creation
    create_form = DDTCreateForm()
    
    return render_template('ddt/preview.html',
                          cliente=cliente,
                          empresa=empresa,
                          preview_data=preview_data,
                          total_amount=total_amount,
                          total_weight=total_weight,
                          available_tickets=available_tickets,
                          create_form=create_form,
                          selected_tickets_json=tickets_data,
                          from_task=from_task,
                          from_warehouse=from_warehouse,
                          task_id=task_id)

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
@admin_required
def create():
    """Step 3: Create the DDT with the selected client and tickets"""
    # Get form data
    cliente_id = request.form.get('cliente_id')
    id_empresa = request.form.get('id_empresa', 1)
    tickets_data = request.form.get('tickets')
    manual_tickets_data = request.form.get('manual_tickets')  # Ticket manuali dal localStorage
    ticket_discounts_data = request.form.get('ticket_discounts')  # Sconti dei ticket dal localStorage
    note = request.form.get('note')
    
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
    current_app.logger.info(f"    ticket_data (parsed): {ticket_data}")
    current_app.logger.info(f"    manual_tickets (parsed): {manual_tickets}")
    current_app.logger.info(f"    ticket_discounts (parsed): {ticket_discounts}")
    
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
    
    # Start a transaction
    try:
        # Create new AlbaranCabecera (DDT header)
        now = datetime.now()
        # Correctly calculate the max ID by adding 1 after getting the max value
        max_id = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 0
        # Get the last NumAlbaran and add 1 to make it sequential
        max_num_albaran = db.session.query(db.func.max(AlbaranCabecera.NumAlbaran)).scalar() or 0
        ddt = AlbaranCabecera(
            # Chiavi primarie
            IdAlbaran=max_id + 1,
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
                
                # Calculate prices - Handle None value for PrecioConIVA
                price_with_vat = float(product.PrecioConIVA) if product.PrecioConIVA is not None else 0.0
                price_without_vat = price_with_vat / (1 + vat_rate)
                # Handle None value for Peso - use 1.0 as default if Peso is None
                peso_value = float(ticket_line.Peso) if ticket_line.Peso is not None else 1.0
                line_total = price_without_vat * peso_value
                line_vat = line_total * vat_rate
                
                # Applica sconto del ticket se presente
                ticket_id_str = str(ticket['id_ticket'])
                ticket_discount = float(ticket_discounts.get(ticket_id_str, 0))
                if ticket_discount > 0:
                    discount_factor = 1 - (ticket_discount / 100)
                    line_total = line_total * discount_factor
                    line_vat = line_vat * discount_factor
                    current_app.logger.info(f"💰 Applicato sconto {ticket_discount}% al ticket {ticket['id_ticket']}")
                    current_app.logger.info(f"   Totale scontato: {line_total:.2f}, IVA scontata: {line_vat:.2f}")
                
                # Get product family, subfamily, class info
                product_article = Article.query.get(product.IdArticulo)
                
                # Create DDT line con assegnazione esplicita di IdTicket
                albaran_line = AlbaranLinea()
                albaran_line.IdLineaAlbaran = line_count
                albaran_line.IdEmpresa = ddt.IdEmpresa
                albaran_line.IdTienda = ddt.IdTienda
                albaran_line.IdBalanzaMaestra = ddt.IdBalanzaMaestra
                albaran_line.IdBalanzaEsclava = ddt.IdBalanzaEsclava
                albaran_line.IdAlbaran = ddt.IdAlbaran
                albaran_line.TipoVenta = ddt.TipoVenta
                
                # Assegna esplicitamente l'ID del ticket
                albaran_line.IdTicket = int(ticket['id_ticket'])
                
                # Dati prodotto - usa i dati dalla linea del ticket, non dal prodotto
                albaran_line.IdArticulo = ticket_line.IdArticulo
                albaran_line.Descripcion = ticket_line.Descripcion or product.Descripcion
                albaran_line.Descripcion1 = getattr(product_article, 'Descripcion1', '') if product_article else ''
                albaran_line.Comportamiento = getattr(ticket_line, 'comportamiento', 0)  # Usa il valore dal ticket
                albaran_line.ComportamientoDevolucion = getattr(ticket_line, 'comportamiento_devolucion', 0)
                
                # Pesi e quantità - Handle None value for Peso
                albaran_line.Peso = peso_value  # Use the same peso_value calculated above
                albaran_line.Medida2 = "un"  # Default come nell'esempio
                
                # Prezzi e IVA
                albaran_line.Precio = 0.0  # Sarà calcolato
                albaran_line.PrecioSinIVA = price_without_vat
                albaran_line.IdIVA = product.IdIva
                albaran_line.PorcentajeIVA = vat_rate * 100
                albaran_line.RecargoEquivalencia = 0.0
                
                # Importi
                albaran_line.Importe = 0.0  # Sarà calcolato
                albaran_line.ImporteSinIVASinDtoL = line_total
                albaran_line.ImporteDelIVAConDtoL = line_vat
                
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
                current_app.logger.info(f"    IdArticolo: {albaran_line.IdArticulo}")
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
                id_iva = ticket_line.get('id_iva', 3)  # Default 22%
                vat_rate = 0
                if id_iva == 1:
                    vat_rate = 0.04  # 4%
                elif id_iva == 2:
                    vat_rate = 0.10  # 10%
                elif id_iva == 3:
                    vat_rate = 0.22  # 22%
                
                # Calcola prezzi
                price_with_vat = float(ticket_line['precio'])
                price_without_vat = price_with_vat / (1 + vat_rate)
                peso_value = float(ticket_line['peso'])
                line_total = price_without_vat * peso_value
                line_vat = line_total * vat_rate
                
                # Applica sconto del ticket manuale se presente
                manual_ticket_id_str = str(manual_ticket['id_ticket'])
                ticket_discount = float(ticket_discounts.get(manual_ticket_id_str, 0))
                if ticket_discount > 0:
                    discount_factor = 1 - (ticket_discount / 100)
                    line_total = line_total * discount_factor
                    line_vat = line_vat * discount_factor
                    current_app.logger.info(f"💰 Applicato sconto {ticket_discount}% al ticket manuale {manual_ticket['id_ticket']}")
                    current_app.logger.info(f"   Totale scontato: {line_total:.2f}, IVA scontata: {line_vat:.2f}")
                
                # Crea riga DDT per ticket manuale
                albaran_line = AlbaranLinea()
                albaran_line.IdLineaAlbaran = line_count
                albaran_line.IdEmpresa = ddt.IdEmpresa
                albaran_line.IdTienda = ddt.IdTienda
                albaran_line.IdBalanzaMaestra = ddt.IdBalanzaMaestra
                albaran_line.IdBalanzaEsclava = ddt.IdBalanzaEsclava
                albaran_line.IdAlbaran = ddt.IdAlbaran
                albaran_line.TipoVenta = ddt.TipoVenta
                
                # Per i ticket manuali, usiamo un ID ticket speciale o NULL
                albaran_line.IdTicket = None  # Ticket manuale non ha ID ticket reale
                
                # Dati prodotto dal ticket manuale
                albaran_line.IdArticulo = 999  # ID prodotto personalizzato
                albaran_line.Descripcion = ticket_line['descripcion']
                albaran_line.Descripcion1 = "Prodotto manuale"
                albaran_line.Comportamiento = ticket_line.get('comportamiento', 1)
                albaran_line.ComportamientoDevolucion = 0
                
                # Pesi e quantità
                albaran_line.Peso = peso_value
                albaran_line.Medida2 = "un"
                
                # Prezzi e IVA
                albaran_line.Precio = 0.0
                albaran_line.PrecioSinIVA = price_without_vat
                albaran_line.IdIVA = id_iva
                albaran_line.PorcentajeIVA = vat_rate * 100
                albaran_line.RecargoEquivalencia = 0.0
                
                # Importi
                albaran_line.Importe = 0.0
                albaran_line.ImporteSinIVASinDtoL = line_total
                albaran_line.ImporteDelIVAConDtoL = line_vat
                
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

        # Aggiorna i totali del DDT
        total_ddt_amount = total_without_vat + total_vat
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
        
        # Commit della transazione
        db.session.commit()
        
        current_app.logger.info(f"🎉 DDT #{ddt.IdAlbaran} creato con successo!")
        current_app.logger.info(f"📊 Riepilogo: {len(ticket_data)} ticket normali + {len(manual_tickets)} ticket manuali = {line_count} righe totali")
        
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
        # Gestiamo anche il caso in cui IdTicket è NULL
        ticket_id = line.IdTicket if line.IdTicket is not None else 'N/A'
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
        
        # Identifica i ticket associati (escludendo quelli manuali che hanno IdTicket = NULL)
        unique_ticket_ids = set()
        manual_lines_count = 0
        
        if albaran_lines:
            for line in albaran_lines:
                if line.IdTicket is not None:
                    # Ticket normale con ID valido
                    unique_ticket_ids.add(line.IdTicket)
                else:
                    # Ticket manuale (IdTicket = NULL)
                    manual_lines_count += 1
        
        current_app.logger.info(f"📋 DDT #{ddt_id}: {len(unique_ticket_ids)} ticket normali, {manual_lines_count} righe manuali")
        
        # Reset stato dei ticket normali (NON quelli manuali)
        reset_tickets_count = 0
        if unique_ticket_ids:
            tickets_to_reset = TicketHeader.query.filter(TicketHeader.IdTicket.in_(list(unique_ticket_ids))).all()
            if tickets_to_reset:
                for ticket_header in tickets_to_reset:
                    if task_with_ddt:
                        # Se il DDT era da task, verifica se il ticket apparteneva al task
                        from app.models import TaskTicket
                        task_ticket = TaskTicket.query.filter_by(
                            task_id=task_with_ddt.id_task, 
                            ticket_id=ticket_header.IdTicket
                        ).first()
                        
                        if task_ticket:
                            # Reset ticket a Enviado = 10 (assegnato al task) invece di 0
                            ticket_header.Enviado = 10
                            current_app.logger.info(f"🔄 Ticket {ticket_header.IdTicket} (Task #{task_with_ddt.task_number}) reimpostato a Enviado = 10 (assegnato)")
                        else:
                            # Ticket non nel task, reset normale
                            ticket_header.Enviado = 0
                            current_app.logger.info(f"🔄 Ticket {ticket_header.IdTicket} (non-task) reimpostato a Enviado = 0 (pendente)")
                    else:
                        # DDT normale, reset a pendente
                        ticket_header.Enviado = 0
                        current_app.logger.info(f"🔄 Ticket {ticket_header.IdTicket} reimpostato a Enviado = 0 (pendente)")
                    
                    reset_tickets_count += 1
                    db.session.add(ticket_header)
            else:
                current_app.logger.warning(f"⚠️  Nessun TicketHeader trovato per gli IdTicket: {list(unique_ticket_ids)}")
        
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
        unit = line.Medida2 or 'un'
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
        
        # Create elegant table rows
        products_data.append([
            Paragraph(code if code != '999' else '', styles['TableCell']),
            Paragraph(description, styles['TableCellLeft']),
            Paragraph(unit, styles['TableCell']),
            Paragraph(f"{quantity:.2f}", styles['TableCellRight']),
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
            vat_rate = float(line.PorcentajeIVA or 0)
            
            # Calculate original amount (without discount)
            original_subtotal = price * quantity
            original_vat = original_subtotal * (vat_rate / 100)
            original_total = original_subtotal + original_vat
            
            # Get actual discounted amount
            discounted_subtotal = float(line.ImporteSinIVASinDtoL or 0)
            discounted_vat = float(line.ImporteDelIVAConDtoL or 0)
            discounted_total = discounted_subtotal + discounted_vat
            
            # Calculate discount amount
            discount_amount = original_total - discounted_total
            total_discount_amount += discount_amount
    
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
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'logos', 'LogoDDT.png')
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
                p.PrecioConIVA
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
                "precio": float(product.PrecioConIVA) if product.PrecioConIVA is not None else 0
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
    
    if not ticket_id:
        return jsonify({'success': False, 'message': 'ID ticket mancante'})
    
    # Get ticket info
    ticket = TicketHeader.query.filter_by(
        IdTicket=ticket_id,
        IdEmpresa=empresa_id
    ).first()
    
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket non trovato'})
    
    if ticket.Enviado != 0:
        return jsonify({'success': False, 'message': 'Ticket già processato'})
    
    # Get unique ticket lines and calculate total - avoid duplicates
    lines_query = """
        SELECT DISTINCT 
            tl.IdArticulo,
            tl.Descripcion,
            tl.Peso,
            tl.FechaCaducidad,
            p.PrecioConIVA
        FROM dat_ticket_linea tl
        LEFT JOIN dat_articulo p ON tl.IdArticulo = p.IdArticulo
        WHERE tl.IdTicket = :ticket_id
        ORDER BY tl.IdArticulo
    """
    
    lines_result = db.session.execute(text(lines_query), {'ticket_id': ticket_id})
    
    ticket_total = 0
    ticket_lines_data = []
    unique_products = {}
    
    for row in lines_result:
        id_articulo = row[0]
        descripcion = row[1]
        peso = float(row[2] or 0)
        fecha_caducidad = row[3]
        precio = float(row[4] or 0)
        
        # Skip if we already processed this article
        if id_articulo in unique_products:
            current_app.logger.warning(f"⚠️ Skipping duplicate IdArticulo {id_articulo} in ticket {ticket_id}")
            continue
        
        # Mark this article as processed
        unique_products[id_articulo] = True
        
        line_amount = peso * precio
        ticket_total += line_amount
        
        ticket_lines_data.append({
            'id_articulo': id_articulo,
            'descripcion': descripcion,
            'peso': peso,
            'precio': precio,
            'importe': line_amount,
            'fecha_caducidad': fecha_caducidad.strftime('%d/%m/%Y') if fecha_caducidad else None
        })
    
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
    """API to search available tickets for adding to DDT preview"""
    query = request.args.get('q', '').strip()
    excluded_tickets = request.args.get('excluded', '').split(',')
    excluded_tickets = [int(x) for x in excluded_tickets if x.isdigit()]
    
    # Build base query
    base_query = TicketHeader.query.filter(TicketHeader.Enviado == 0)
    
    # Exclude already selected tickets
    if excluded_tickets:
        base_query = base_query.filter(~TicketHeader.IdTicket.in_(excluded_tickets))
    
    # Apply search filter if provided
    if query:
        if query.isdigit():
            # Search by ticket number
            base_query = base_query.filter(TicketHeader.NumTicket.like(f'%{query}%'))
        else:
            # Search by product description in ticket lines
            base_query = base_query.join(TicketLine).filter(
                TicketLine.Descripcion.like(f'%{query}%')
            )
    
    tickets = base_query.order_by(TicketHeader.Fecha.desc()).limit(20).all()
    
    results = []
    for ticket in tickets:
        # Get ticket summary info
        lines_count = TicketLine.query.filter_by(
            IdTicket=ticket.IdTicket,
            IdEmpresa=ticket.IdEmpresa
        ).count()
        
        results.append({
            'id_ticket': ticket.IdTicket,
            'num_ticket': ticket.NumTicket,
            'fecha': ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else '',
            'lines_count': lines_count,
            'id_empresa': ticket.IdEmpresa
        })
    
    return jsonify({'success': True, 'tickets': results})

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
            precio = float(product_data.get('precio', 1.00))
            id_iva = int(product_data.get('id_iva', 3))  # Default 22%
            fecha_caducidad = product_data.get('fecha_caducidad')
            
            # Calcola importo linea
            importe = peso * precio
            total_ticket += importe
            
            # Prepara dati per localStorage (simula una TicketLine)
            ticket_lines_data.append({
                'id_linea_ticket': f"temp_{temp_ticket_id}_{idx}",  # ID temporaneo
                'id_ticket': temp_ticket_id,
                'id_articulo': 999,  # Usa sempre ID 999 per prodotti personalizzati
                'descripcion': descripcion,
                'peso': float(peso),
                'precio': precio,
                'importe': importe,
                'fecha_caducidad': fecha_caducidad,
                'id_iva': id_iva,
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
        
        return jsonify({
            'success': True,
            'duplicates': duplicates,
            'orphaned_lines': orphaned_lines
        })
        
    except Exception as e:
        current_app.logger.error(f"Errore nel controllo duplicati: {str(e)}")
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
                        'ticket_id': line.IdTicket,
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
        price_without_vat = price_with_vat / (1 + vat_rate)
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
                    p.PrecioConIVA
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