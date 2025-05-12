from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, not_, exists
from models import db, Client, TicketHeader, TicketLine, Product, DDTHead, DDTLine, Company
from forms import DDTClientSelectForm, DDTTicketFilterForm, DDTCreateForm, DDTDeleteForm, DDTExportForm
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

ddt_bp = Blueprint('ddt', __name__)

@ddt_bp.route('/')
@login_required
def index():
    """Display a list of all DDTs"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    ddts = DDTHead.query.order_by(DDTHead.data_creazione.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    return render_template('ddt/index.html', ddts=ddts)

@ddt_bp.route('/new', methods=['GET', 'POST'])
@login_required
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
    
    if form.validate_on_submit():
        from_date = datetime.strptime(form.from_date.data, '%Y-%m-%d')
        to_date = datetime.strptime(form.to_date.data, '%Y-%m-%d')
        # Add a day to to_date to include the full day
        to_date = to_date + timedelta(days=1)
        
        # Query for tickets not already included in any DDT
        tickets = TicketHeader.query.filter(
            TicketHeader.Fecha.between(from_date, to_date),
            TicketHeader.Enviado == 0,  # Solo ticket pendenti
            not_(exists().where(
                and_(
                    DDTLine.id_ticket == TicketHeader.IdTicket,
                    DDTLine.id_empresa == TicketHeader.IdEmpresa
                )
            ))
        ).order_by(TicketHeader.Fecha.desc()).all()
    else:
        # Se il form non è stato ancora inviato, non mostrare alcun ticket
        tickets = []
    
    # Also create the create form for the hidden form CSRF token
    create_form = DDTCreateForm()
    
    return render_template('ddt/select_tickets.html', 
                          cliente=cliente, 
                          tickets=tickets, 
                          form=form,
                          create_form=create_form,
                          id_empresa=id_empresa)

@ddt_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Step 3: Create the DDT with the selected client and tickets"""
    # Debug request data
    print("=" * 50)
    print("CREATE DDT REQUEST")
    print("=" * 50)
    print(f"Request method: {request.method}")
    print(f"Request form data: {request.form}")
    print(f"Request headers: {request.headers}")
    print("=" * 50)
    
    # Create form instance with request data
    form = DDTCreateForm()
    
    # Debug form validation
    print(f"Form data: {request.form}")
    print(f"Form errors before validation: {form.errors}")
    
    # Check CSRF token first
    csrf_token = request.form.get('csrf_token')
    if not csrf_token:
        print("Missing CSRF token in form data")
        return jsonify({"success": False, "error": "Token CSRF mancante"})
    
    # Validate form
    if not form.validate_on_submit():
        print(f"Form validation failed: {form.errors}")
        
        # Check if we have CSRF token issues
        if 'csrf_token' in form.errors:
            print(f"CSRF token error: {form.errors['csrf_token']}")
            # Try to recover by rendering the form again
            return redirect(url_for('ddt.select_tickets', cliente_id=request.form.get('cliente_id', 0)))
            
        return jsonify({"success": False, "error": "Validation error", "details": form.errors})
    
    cliente_id = form.cliente_id.data
    id_empresa = form.id_empresa.data
    
    # Verify client exists
    client = Client.query.get(cliente_id)
    if not client:
        return jsonify({"success": False, "error": "Cliente non trovato"})
    
    # Verify empresa exists
    empresa = Company.query.get(id_empresa)
    if not empresa:
        return jsonify({"success": False, "error": "Azienda non trovata"})
    
    # Parse ticket data
    try:
        ticket_data = json.loads(form.tickets.data)
        print(f"Parsed ticket data: {ticket_data}")
        if not ticket_data:
            return jsonify({"success": False, "error": "Nessun ticket selezionato"})
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}, data: {form.tickets.data}")
        return jsonify({"success": False, "error": f"Formato JSON non valido: {str(e)}"})
    
    # Start a transaction
    try:
        # Create DDT header
        ddt = DDTHead(
            id_cliente=cliente_id,
            id_empresa=id_empresa,
            data_creazione=datetime.now(),
            totale_senza_iva=0,
            totale_iva=0,
            totale_importo=0
        )
        db.session.add(ddt)
        db.session.flush()  # Get the DDT ID
        
        print(f"Created DDT with ID: {ddt.id}")
        
        # Create DDT lines
        for ticket in ticket_data:
            # Debug ticket data
            print(f"Processing ticket: {ticket}")
            
            # Verify the ticket exists and is not already in another DDT
            ticket_exists = TicketHeader.query.filter_by(
                IdTicket=ticket['id_ticket'],
                IdEmpresa=ticket['id_empresa']
            ).first()
            
            if not ticket_exists:
                db.session.rollback()
                return jsonify({"success": False, "error": f"Ticket {ticket['id_ticket']} non trovato"})
            
            ticket_in_ddt = DDTLine.query.filter_by(
                id_ticket=ticket['id_ticket'],
                id_empresa=ticket['id_empresa']
            ).first()
            
            if ticket_in_ddt:
                db.session.rollback()
                return jsonify({"success": False, "error": f"Ticket {ticket['id_ticket']} già incluso in un DDT"})
            
            # Create DDT line
            ddt_line = DDTLine(
                id_ddt=ddt.id,
                id_empresa=ticket['id_empresa'],
                id_tienda=ticket['id_tienda'],
                id_balanza_maestra=ticket['id_balanza_maestra'],
                id_balanza_esclava=ticket['id_balanza_esclava'],
                tipo_venta=ticket['tipo_venta'],
                id_ticket=ticket['id_ticket']
            )
            db.session.add(ddt_line)
            
            # Aggiorna lo stato del ticket a 'processato'
            ticket_exists.Enviado = 1
            
            print(f"Added DDT line for ticket {ticket['id_ticket']} and set status to processed")
        
        # Calculate totals
        db.session.flush()
        totals = ddt.calculate_totals()
        print(f"DDT totals calculated: {totals}")
        
        # Commit the transaction
        db.session.commit()
        print(f"Transaction committed successfully")
        
        # Return success with redirect to detail page
        return redirect(url_for('ddt.detail', ddt_id=ddt.id))
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating DDT: {str(e)}")
        print(f"Exception type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Errore durante la creazione del DDT: {str(e)}"})

@ddt_bp.route('/<int:ddt_id>')
@login_required
def detail(ddt_id):
    """Show DDT details with all associated tickets and products"""
    ddt = DDTHead.query.get_or_404(ddt_id)
    
    # Load cliente
    cliente = Client.query.get(ddt.id_cliente)
    
    # Load empresa
    empresa = Company.query.get(ddt.id_empresa)
    
    # Get all ticket details for this DDT
    tickets = []
    total_items = 0
    
    for ddt_line in ddt.lines:
        # Get ticket usando todas las claves primarias compuestas
        ticket = TicketHeader.query.filter_by(
            IdTicket=ddt_line.id_ticket,
            IdEmpresa=ddt_line.id_empresa,
            IdTienda=ddt_line.id_tienda,
            IdBalanzaMaestra=ddt_line.id_balanza_maestra,
            IdBalanzaEsclava=ddt_line.id_balanza_esclava,
            TipoVenta=ddt_line.tipo_venta
        ).first()
        
        if not ticket:
            continue
        
        # Get ticket lines
        ticket_lines = TicketLine.query.filter_by(
            IdTicket=ticket.IdTicket
        ).all()
        
        # Get products for each ticket line
        ticket_products = []
        for line in ticket_lines:
            product = Product.query.get(line.IdArticulo)
            if not product:
                continue
            
            # Determine VAT rate
            vat_rate = 0
            if product.IdIva == 1:
                vat_rate = 0.04  # 4%
            elif product.IdIva == 2:
                vat_rate = 0.10  # 10%
            elif product.IdIva == 3:
                vat_rate = 0.22  # 22%
            
            # Calculate values
            price_with_vat = float(product.PrecioConIVA)
            price_without_vat = price_with_vat / (1 + vat_rate)
            line_total = price_without_vat * float(line.Peso)
            line_vat = line_total * vat_rate
            
            ticket_products.append({
                'id': product.IdArticulo,
                'description': product.Descripcion,
                'peso': line.Peso,
                'comportamiento': line.comportamiento,
                'price_with_vat': price_with_vat,
                'price_without_vat': price_without_vat,
                'vat_rate': vat_rate,
                'iva_id': product.IdIva,
                'line_total': line_total,
                'line_vat': line_vat,
                'line_total_with_vat': line_total + line_vat
            })
            
            total_items += 1
        
        tickets.append({
            'ticket': ticket,
            'products': ticket_products
        })
    
    # Prepare delete form
    delete_form = DDTDeleteForm()
    
    # Prepare export form
    export_form = DDTExportForm()
    
    return render_template('ddt/detail.html',
                          ddt=ddt,
                          cliente=cliente,
                          empresa=empresa,
                          tickets=tickets,
                          total_items=total_items,
                          delete_form=delete_form,
                          export_form=export_form)

@ddt_bp.route('/<int:ddt_id>/delete', methods=['POST'])
@login_required
def delete(ddt_id):
    """Delete a DDT and all its lines"""
    ddt = DDTHead.query.get_or_404(ddt_id)
    form = DDTDeleteForm()
    
    if form.validate_on_submit() and form.confirm.data:
        try:
            # Start transaction
            # Prima di eliminare il DDT, ottieni tutti i ticket associati
            ddt_lines = DDTLine.query.filter_by(id_ddt=ddt.id).all()
            
            # Per ogni linea DDT, trova il ticket corrispondente e reimpostalo come pendente
            for line in ddt_lines:
                ticket = TicketHeader.query.filter_by(
                    IdTicket=line.id_ticket,
                    IdEmpresa=line.id_empresa,
                    IdTienda=line.id_tienda,
                    IdBalanzaMaestra=line.id_balanza_maestra,
                    IdBalanzaEsclava=line.id_balanza_esclava,
                    TipoVenta=line.tipo_venta
                ).first()
                
                if ticket:
                    ticket.Enviado = 0  # Reimposta il ticket come pendente
                    print(f"Reset ticket {ticket.IdTicket} to pending state")
            
            # The cascade delete will take care of the DDT lines
            db.session.delete(ddt)
            db.session.commit()
            
            flash('DDT eliminato con successo e ticket reimpostati come pendenti.', 'success')
            return redirect(url_for('ddt.index'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'eliminazione del DDT: {str(e)}', 'danger')
    
    flash('Conferma richiesta per eliminare il DDT.', 'warning')
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

@ddt_bp.route('/<int:ddt_id>/export', methods=['POST'])
@login_required
def export(ddt_id):
    """Export DDT as PDF"""
    ddt = DDTHead.query.get_or_404(ddt_id)
    form = DDTExportForm()
    
    if form.validate_on_submit():
        # Generate PDF 
        try:
            # Get all the necessary data
            cliente = Client.query.get(ddt.id_cliente)
            empresa = Company.query.get(ddt.id_empresa)
            
            # Generate PDF
            pdf_data = generate_ddt_pdf(ddt, cliente, empresa)
            
            return send_file(
                io.BytesIO(pdf_data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'DDT_{ddt.id}.pdf'
            )
        
        except Exception as e:
            flash(f'Errore durante l\'esportazione del DDT: {str(e)}', 'danger')
    
    return redirect(url_for('ddt.detail', ddt_id=ddt_id))

def generate_ddt_pdf(ddt, cliente, empresa):
    """Generate a PDF document for the DDT"""
    buffer = io.BytesIO()
    
    # Create the PDF document using ReportLab
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=25*mm,
        leftMargin=25*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
        title=f"DDT #{ddt.id}",
        author=empresa.NombreEmpresa
    )
    
    # Define colors for a more professional look - using more subtle colors
    primary_color = colors.HexColor('#2980b9')  # Soft blue
    accent_color = colors.HexColor('#f39c12')   # Soft orange
    text_color = colors.HexColor('#34495e')     # Dark blue-gray
    light_gray = colors.HexColor('#ecf0f1')     # Very light gray
    medium_gray = colors.HexColor('#bdc3c7')    # Medium gray
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='DDTTitle',
        parent=styles['Heading1'],
        fontSize=20,
        alignment=1,  # centered
        textColor=primary_color,
        spaceAfter=8*mm,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='DDTHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=primary_color,
        spaceAfter=5*mm,
        fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        name='DDTSectionHeader',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.white,
        alignment=0,  # left
        spaceAfter=3*mm,
        fontName='Helvetica-Bold',
        backColor=primary_color,
        borderPadding=(4, 4, 4, 4)
    ))
    styles.add(ParagraphStyle(
        name='DDTNormal',
        parent=styles['Normal'],
        fontSize=9,
        textColor=text_color,
        spaceAfter=2*mm
    ))
    styles.add(ParagraphStyle(
        name='DDTSmall',
        parent=styles['Normal'],
        fontSize=8,
        textColor=text_color
    ))
    styles.add(ParagraphStyle(
        name='DDTTableHeader',
        parent=styles['Normal'],
        fontSize=9,
        alignment=1,  # Centered
        textColor=primary_color,
        fontName='Helvetica-Bold'
    ))
    
    # Collect all elements that will be added to the PDF
    elements = []
    
    # Add logo and header in a table for better layout control
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'img', 'logo.png')
    
    # Check if logo exists, otherwise use a placeholder
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 18*mm
        logo.drawWidth = 40*mm
    else:
        # If no logo found, create a placeholder text
        logo = Paragraph(f"<b>{empresa.NombreEmpresa}</b>", styles['DDTHeader'])
    
    # Create header with logo and title
    header_data = [
        [logo, Paragraph(f"<font size='16'><b>DOCUMENTO DI TRASPORTO</b></font><br/><font color='#7f8c8d'>D.D.T. n° {ddt.id} del {ddt.data_creazione.strftime('%d/%m/%Y')}</font>", styles['DDTTitle'])]
    ]
    
    header_table = Table(header_data, colWidths=[50*mm, doc.width-50*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(header_table)
    
    # Add a horizontal line with accent color
    elements.append(Spacer(1, 6*mm))
    elements.append(Table([['']], colWidths=[doc.width], rowHeights=[1], style=TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 1, accent_color),
    ])))
    elements.append(Spacer(1, 10*mm))
    
    # Company and client information - create a 2-column layout with improved styling
    elements.append(Paragraph("<b>INFORMAZIONI TRASPORTO</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 2*mm))
    
    company_data = [
        [
            # Mittente (a sinistra)
            Table([
                [Paragraph("<b>MITTENTE</b>", styles['DDTTableHeader'])],
                [Paragraph(f"<b>{empresa.NombreEmpresa}</b><br/>"
                          f"{empresa.Direccion or 'N/A'}<br/>"
                          f"{empresa.Poblacion or 'N/A'}<br/>"
                          f"P.IVA: {empresa.CIF_VAT or 'N/A'}<br/>"
                          f"Tel: {getattr(empresa, 'Telefono', 'N/A')}", styles['DDTNormal'])],
            ], colWidths=[doc.width/2.0 - 10*mm], style=TableStyle([
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('LINEBELOW', (0, 0), (0, 0), 0.5, primary_color),
            ])),
            
            # Destinatario (a destra)
            Table([
                [Paragraph("<b>DESTINATARIO</b>", styles['DDTTableHeader'])],
                [Paragraph(f"<b>{cliente.Nombre}</b><br/>"
                          f"{cliente.Direccion or 'N/A'}<br/>"
                          f"{cliente.Poblacion or 'N/A'}<br/>"
                          f"P.IVA/CF: {cliente.DNI or 'N/A'}<br/>"
                          f"Tel: {getattr(cliente, 'Telefono', 'N/A')}", styles['DDTNormal'])],
            ], colWidths=[doc.width/2.0 - 10*mm], style=TableStyle([
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('LINEBELOW', (0, 0), (0, 0), 0.5, primary_color),
            ])),
        ]
    ]
    
    company_table = Table(company_data, colWidths=[doc.width/2.0, doc.width/2.0])
    company_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(company_table)
    elements.append(Spacer(1, 10*mm))
    
    # DDT Information with improved styling
    elements.append(Paragraph("<b>DETTAGLI DOCUMENTO</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 2*mm))
    
    ddt_info_data = [
        [
            Paragraph("<b>Data Emissione:</b>", styles['DDTNormal']), 
            Paragraph(f"{ddt.data_creazione.strftime('%d/%m/%Y %H:%M')}", styles['DDTNormal']),
            Paragraph("<b>Numero DDT:</b>", styles['DDTNormal']), 
            Paragraph(f"{ddt.id}", styles['DDTNormal']),
            Paragraph("<b>Totale Articoli:</b>", styles['DDTNormal']), 
            Paragraph(f"{len(DDTLine.query.filter_by(id_ddt=ddt.id).all())}", styles['DDTNormal'])
        ]
    ]
    
    ddt_info_table = Table(ddt_info_data, colWidths=[40*mm, 30*mm, 30*mm, 20*mm, 30*mm, 20*mm])
    ddt_info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), light_gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
    ]))
    
    elements.append(ddt_info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Get all ticket details for this DDT
    tickets = []
    total_items = 0
    all_products = []
    
    ddt_lines = DDTLine.query.filter_by(id_ddt=ddt.id).all()
    for line in ddt_lines:
        # Get the ticket
        ticket = TicketHeader.query.filter_by(
            IdEmpresa=line.id_empresa,
            IdTienda=line.id_tienda,
            IdBalanzaMaestra=line.id_balanza_maestra,
            IdBalanzaEsclava=line.id_balanza_esclava,
            TipoVenta=line.tipo_venta,
            IdTicket=line.id_ticket
        ).first()
        
        if not ticket:
            continue
        
        # Get the ticket lines with articles for this ticket
        ticket_lines = TicketLine.query.filter_by(
            IdTicket=ticket.IdTicket
        ).all()
        
        ticket_products = []
        for t_line in ticket_lines:
            product = Product.query.get(t_line.IdArticulo)
            if not product:
                continue
            
            # Determine VAT rate
            vat_rate = get_vat_rate(product.IdIva)
            
            # Calculate values
            price_with_vat = float(product.PrecioConIVA)
            price_without_vat = price_with_vat / (1 + vat_rate)
            line_total = price_without_vat * float(t_line.Peso)
            line_vat = line_total * vat_rate
            
            product_data = {
                'id': product.IdArticulo,
                'description': product.Descripcion,
                'peso': t_line.Peso,
                'comportamiento': t_line.comportamiento,
                'price_with_vat': price_with_vat,
                'price_without_vat': price_without_vat,
                'vat_rate': vat_rate,
                'iva_id': product.IdIva,
                'line_total': line_total,
                'line_vat': line_vat,
                'line_total_with_vat': line_total + line_vat,
                'ticket_id': ticket.IdTicket
            }
            
            ticket_products.append(product_data)
            all_products.append(product_data)
            total_items += 1
        
        tickets.append({
            'ticket': ticket,
            'products': ticket_products
        })
    
    # Add products table with improved styling
    elements.append(Paragraph("<b>PRODOTTI</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 2*mm))
    
    # Style the table header
    col_widths = [
        20*mm,  # Ticket
        20*mm,  # ID
        60*mm,  # Descrizione
        17*mm,  # Peso
        17*mm,  # Prezzo
        15*mm,  # IVA %
        17*mm,  # Imponibile
        15*mm,  # IVA
        17*mm   # Totale
    ]
    
    # Create product rows
    product_rows = [
        [
            Paragraph("<b>Ticket</b>", styles['DDTTableHeader']),
            Paragraph("<b>ID</b>", styles['DDTTableHeader']),
            Paragraph("<b>Descrizione</b>", styles['DDTTableHeader']),
            Paragraph("<b>Peso/Qta.</b>", styles['DDTTableHeader']),
            Paragraph("<b>Prezzo Unit.</b>", styles['DDTTableHeader']),
            Paragraph("<b>IVA %</b>", styles['DDTTableHeader']),
            Paragraph("<b>Imponibile</b>", styles['DDTTableHeader']),
            Paragraph("<b>IVA</b>", styles['DDTTableHeader']),
            Paragraph("<b>Totale</b>", styles['DDTTableHeader'])
        ]
    ]
    
    for product in all_products:
        iva_percentage = "4%" if product['iva_id'] == 1 else "10%" if product['iva_id'] == 2 else "22%" if product['iva_id'] == 3 else "N/A"
        
        row = [
            Paragraph(f"{product['ticket_id']}", styles['DDTSmall']),
            Paragraph(f"{product['id']}", styles['DDTSmall']),
            Paragraph(f"{product['description']}", styles['DDTSmall']),
            Paragraph(f"{product['peso']} {'unità' if product.get('comportamiento', 0) == 0 else 'kg'}", styles['DDTSmall']),
            Paragraph(f"€ {product['price_without_vat']:.2f}", styles['DDTSmall']),
            Paragraph(f"{iva_percentage}", styles['DDTSmall']),
            Paragraph(f"€ {product['line_total']:.2f}", styles['DDTSmall']),
            Paragraph(f"€ {product['line_vat']:.2f}", styles['DDTSmall']),
            Paragraph(f"€ {product['line_total_with_vat']:.2f}", styles['DDTSmall'])
        ]
        product_rows.append(row)
    
    # Add totals row
    total_row = [
        Paragraph("", styles['DDTSmall']),
        Paragraph("", styles['DDTSmall']),
        Paragraph("", styles['DDTSmall']),
        Paragraph("", styles['DDTSmall']),
        Paragraph("", styles['DDTSmall']),
        Paragraph("<b>TOTALI:</b>", styles['DDTSmall']),
        Paragraph(f"<b>€ {ddt.totale_senza_iva:.2f}</b>", styles['DDTSmall']),
        Paragraph(f"<b>€ {ddt.totale_iva:.2f}</b>", styles['DDTSmall']),
        Paragraph(f"<b>€ {ddt.totale_importo:.2f}</b>", styles['DDTSmall'])
    ]
    product_rows.append(total_row)
    
    # Create product table
    product_table = Table(product_rows, colWidths=col_widths, repeatRows=1)
    
    # Style for the product table - minimalist approach
    table_style = [
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),  # Right-align numeric columns
        ('LINEBELOW', (0, 0), (-1, 0), 1, primary_color),  # Header underline only
        ('LINEBELOW', (0, -2), (-1, -2), 0.5, medium_gray),  # Line before totals
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Bold font for total row
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]
    
    # Add alternating row colors - subtle
    for i in range(len(product_rows)):
        if i % 2 == 1 and i < len(product_rows) - 1:  # Odd rows get light background except header and total row
            table_style.append(('BACKGROUND', (0, i), (-1, i), light_gray))
    
    # Add a background color to the total row
    table_style.append(('BACKGROUND', (0, -1), (-1, -1), light_gray))
    
    product_table.setStyle(TableStyle(table_style))
    
    elements.append(product_table)
    elements.append(Spacer(1, 15*mm))
    
    # Notes and signature area with improved styling
    elements.append(Paragraph("<b>ANNOTAZIONI E FIRME</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 2*mm))
    
    notes_data = [
        [
            # Notes (left column)
            Table([
                [Paragraph("<b>NOTE</b>", styles['DDTTableHeader'])],
                [Paragraph("", styles['DDTNormal'])],
            ], colWidths=[doc.width/2.0 - 10*mm], rowHeights=[None, 40*mm], style=TableStyle([
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('LINEBELOW', (0, 0), (0, 0), 0.5, primary_color),
                ('BOTTOMPADDING', (0, 0), (0, 0), 5),
                ('TOPPADDING', (0, 0), (0, 0), 5),
            ])),
            
            # Signature (right column)
            Table([
                [Paragraph("<b>FIRMA PER RICEVUTA</b>", styles['DDTTableHeader'])],
                [Paragraph("", styles['DDTNormal'])],
            ], colWidths=[doc.width/2.0 - 10*mm], rowHeights=[None, 40*mm], style=TableStyle([
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('LINEBELOW', (0, 0), (0, 0), 0.5, primary_color),
                ('BOTTOMPADDING', (0, 0), (0, 0), 5),
                ('TOPPADDING', (0, 0), (0, 0), 5),
            ])),
        ]
    ]
    
    notes_table = Table(notes_data, colWidths=[doc.width/2.0, doc.width/2.0])
    notes_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(notes_table)
    
    # Add footer
    def footer(canvas, doc):
        canvas.saveState()
        # Line above footer
        canvas.setStrokeColor(accent_color)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, 15*mm, doc.width + doc.leftMargin, 15*mm)
        
        # Footer text
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        
        # Footer left (company)
        canvas.drawString(doc.leftMargin, 10*mm, empresa.NombreEmpresa)
        
        # Footer center (date)
        footer_text = f"Documento generato il {datetime.now().strftime('%d/%m/%Y')}"
        text_width = canvas.stringWidth(footer_text, "Helvetica", 8)
        canvas.drawString(doc.leftMargin + (doc.width / 2) - (text_width / 2), 10*mm, footer_text)
        
        # Footer right (page number)
        page_num = canvas.getPageNumber()
        text = f"Pagina {page_num}"
        text_width = canvas.stringWidth(text, "Helvetica", 8)
        canvas.drawString(doc.leftMargin + doc.width - text_width, 10*mm, text)
        
        canvas.restoreState()
    
    # Build the PDF with custom template
    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    
    # Get the value of the BytesIO buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

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
        
        # Get ticket lines
        lines = TicketLine.query.filter_by(IdTicket=ticket_id).all()
        print(f"Found {len(lines)} lines for ticket {ticket_id}")
        
        # Format response data
        ticket_data = {
            "success": True,
            "ticket": {
                "id": ticket.IdTicket,
                "date": ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else 'N/A',
                "num_lines": len(lines)
            },
            "items": []
        }
        
        # Add product details for each line
        for line in lines:
            try:
                product = Product.query.get(line.IdArticulo)
                if not product:
                    print(f"Product not found for line {line.IdLinea}, article ID: {line.IdArticulo}")
                    continue
                    
                ticket_data["items"].append({
                    "id": product.IdArticulo,
                    "description": product.Descripcion,
                    "quantity": f"{line.Peso} {'unità' if line.comportamiento == 0 else 'Kg'}" if line.Peso else "N/A",
                    "price": f"€ {product.PrecioConIVA}" if product.PrecioConIVA else "N/A"
                })
            except Exception as e:
                print(f"Error processing line {line.IdLinea}: {str(e)}")
                continue
        
        print(f"Returning ticket data with {len(ticket_data['items'])} items")
        return jsonify(ticket_data)
    
    except Exception as e:
        import traceback
        print(f"Error in ticket_details: {str(e)}")
        print(traceback.format_exc())
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
    
    # Query for tickets for this client not already included in any DDT
    tickets = TicketHeader.query.filter(
        TicketHeader.Fecha.between(from_date, to_date),
        TicketHeader.IdCliente == client_id,
        TicketHeader.Enviado == 0,  # Solo ticket pendenti
        not_(exists().where(
            and_(
                DDTLine.id_ticket == TicketHeader.IdTicket,
                DDTLine.id_empresa == TicketHeader.IdEmpresa
            )
        ))
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
                "peso": float(line.Peso) if line.Peso else 0,
                "comportamiento": line.comportamiento,
                "precio": float(product.PrecioConIVA) if product.PrecioConIVA else 0
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