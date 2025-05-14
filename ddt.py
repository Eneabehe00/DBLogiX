from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, not_, exists
from models import db, Client, TicketHeader, TicketLine, Product, Company, AlbaranCabecera, AlbaranLinea, Article
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
    
    # Recuperare i DDT dalle tabelle AlbaranCabecera
    ddts = AlbaranCabecera.query.order_by(AlbaranCabecera.Fecha.desc()).all()
    
    # Preparare i dati per la visualizzazione
    combined_ddts = []
    
    for ddt in ddts:
        cliente = Client.query.get(ddt.IdCliente)
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
    
    # Ordina la lista per data (decrescente)
    combined_ddts.sort(key=lambda x: x['date'], reverse=True)
    
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
    
    return render_template('ddt/index.html', ddts=pagination)

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
        
        # Query for tickets not marked as processed
        tickets = TicketHeader.query.filter(
            TicketHeader.Fecha.between(from_date, to_date),
            TicketHeader.Enviado == 0  # Solo ticket pendenti
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
            Tipo="A",  # Albaran
            IdVendedor=1,  # Valore predefinito
            NombreVendedor="IL CAPO",  # Valore predefinito
            ReferenciaDocumento="",
            ObservacionesDocumento="",
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
            NumLineas=len(ticket_data),
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
        
        print(f"Created AlbaranCabecera with ID: {ddt.IdAlbaran}")
        
        # Create AlbaranLinea (DDT lines) for each ticket
        line_count = 0
        for ticket_idx, ticket in enumerate(ticket_data, 1):
            # Verify the ticket exists and is not already in another DDT
            ticket_exists = TicketHeader.query.filter_by(
                IdTicket=ticket['id_ticket'],
                IdEmpresa=ticket['id_empresa']
            ).first()
            
            if not ticket_exists:
                db.session.rollback()
                return jsonify({"success": False, "error": f"Ticket {ticket['id_ticket']} non trovato"})
            
            # Check if this ticket is already used in another DDT
            ticket_in_ddt = AlbaranLinea.query.filter(
                AlbaranLinea.IdEmpresa == ticket['id_empresa'],
                AlbaranLinea.IdArticulo == ticket['id_ticket']
            ).first()
            
            if ticket_in_ddt:
                db.session.rollback()
                return jsonify({"success": False, "error": f"Ticket {ticket['id_ticket']} già incluso in un DDT"})
            
            # Get ticket lines
            ticket_lines = TicketLine.query.filter_by(
                IdTicket=ticket_exists.IdTicket
            ).all()
            
            # Create an AlbaranLinea for each product in the ticket
            for ticket_line in ticket_lines:
                line_count += 1
                product = Product.query.get(ticket_line.IdArticulo)
                
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
                
                # Calculate prices
                price_with_vat = float(product.PrecioConIVA)
                price_without_vat = price_with_vat / (1 + vat_rate)
                line_total = price_without_vat * float(ticket_line.Peso)
                line_vat = line_total * vat_rate
                
                # Get product family, subfamily, class info
                product_article = Article.query.get(product.IdArticulo)
            
            # Create DDT line
                albaran_line = AlbaranLinea(
                    # Chiavi primarie e riferimenti
                    IdLineaAlbaran=line_count,
                    IdEmpresa=ddt.IdEmpresa,
                    IdTienda=ddt.IdTienda,
                    IdBalanzaMaestra=ddt.IdBalanzaMaestra,
                    IdBalanzaEsclava=ddt.IdBalanzaEsclava,
                    IdAlbaran=ddt.IdAlbaran,
                    TipoVenta=ddt.TipoVenta,
                    
                    # Dati prodotto
                    IdArticulo=product.IdArticulo,
                    Descripcion=product.Descripcion,
                    Descripcion1=getattr(product_article, 'Descripcion1', '') if product_article else '',
                    Comportamiento=1,  # Default come nell'esempio
                    ComportamientoDevolucion=0,
                    
                    # Pesi e quantità
                    Peso=float(ticket_line.Peso),
                    Medida2="un",  # Default come nell'esempio
                    
                    # Prezzi e IVA
                    Precio=0.0,  # Sarà calcolato
                    PrecioSinIVA=price_without_vat,
                    IdIVA=product.IdIva,
                    PorcentajeIVA=vat_rate * 100,
                    RecargoEquivalencia=0.0,
                    
                    # Importi
                    Importe=0.0,  # Sarà calcolato
                    ImporteSinIVASinDtoL=line_total,
                    ImporteDelIVAConDtoL=line_vat,
                    
                    # Informazioni aggiuntive dal prodotto
                    IdClase=getattr(product_article, 'IdClase', None),
                    NombreClase="ARTICOLI",  # Default come nell'esempio
                    IdFamilia=product.IdFamilia,
                    NombreFamilia="",  # Da popolare se disponibile
                    IdSeccion=getattr(product_article, 'IdSeccion', None),
                    NombreSeccion="",  # Da popolare se disponibile
                    IdSubFamilia=product.IdSubFamilia,
                    NombreSubFamilia="",  # Da popolare se disponibile
                    IdDepartamento=getattr(product_article, 'IdDepartamento', None),
                    NombreDepartamento="",  # Da popolare se disponibile
                    
                    # Informazioni ingredienti (da popolare se disponibili)
                    Texto1=getattr(product_article, 'Texto1', None),
                    
                    # Stato e timestamp
                    Modificado=1,
                    Operacion="A",
                    Usuario="DBLogiX",
                    TimeStamp=now
                )
                
                db.session.add(albaran_line)
            
            # Aggiorna lo stato del ticket a 'processato'
            ticket_exists.Enviado = 1
            
            print(f"Added AlbaranLinea for ticket {ticket['id_ticket']} and set status to processed")
        
        # Aggiorna il numero di linee nel DDT
        ddt.NumLineas = line_count
        
        # Calcola i totali
        total_senza_iva = 0
        total_iva = 0
        
        for line in db.session.query(AlbaranLinea).filter_by(IdAlbaran=ddt.IdAlbaran).all():
            total_senza_iva += float(line.ImporteSinIVASinDtoL or 0)
            total_iva += float(line.ImporteDelIVAConDtoL or 0)
        
        # Update totals
        ddt.ImporteTotalSinIVAConDtoL = total_senza_iva
        ddt.ImporteTotalDelIVAConDtoLConDtoTotal = total_iva
        ddt.ImporteTotalSinIVAConDtoLConDtoTotal = total_senza_iva
        ddt.ImporteTotal = total_senza_iva + total_iva
        
        # Commit the transaction
        db.session.commit()
        print(f"Transaction committed successfully")
        
        # Return success with redirect to detail page
        return redirect(url_for('ddt.detail', ddt_id=ddt.IdAlbaran))
        
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
    # Find the DDT in AlbaranCabecera
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    
    # Load cliente e empresa (già presenti nel ddt)
    cliente = Client.query.get(ddt.IdCliente)
    empresa = Company.query.get(ddt.IdEmpresa)
    
    # Get all products for this DDT
    products = []
    total_items = 0
    
    # Raggruppiamo i prodotti per avere una lista organizzata
    albaran_lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt_id).all()
    
    for line in albaran_lines:
        total_items += 1
        
        vat_rate = float(line.PorcentajeIVA) / 100 if line.PorcentajeIVA else 0
        
        product_data = {
            'id': line.IdArticulo,
            'name': line.Descripcion,
            'weight': line.Peso,
            'price_with_vat': float(line.Precio) if line.Precio else 0,
            'price_without_vat': float(line.PrecioSinIVA) if line.PrecioSinIVA else 0,
            'total': float(line.ImporteSinIVASinDtoL) if line.ImporteSinIVASinDtoL else 0,
            'total_with_vat': float(line.ImporteSinIVASinDtoL) + float(line.ImporteDelIVAConDtoL) if line.ImporteSinIVASinDtoL and line.ImporteDelIVAConDtoL else 0,
            'vat_rate': f"{vat_rate * 100:.0f}%",
            'vat_amount': float(line.ImporteDelIVAConDtoL) if line.ImporteDelIVAConDtoL else 0
        }
        products.append(product_data)
    
    # Organizziamo i prodotti come se fossero in ticket
    tickets = [{
        'id': ddt_id,
        'date': ddt.Fecha.strftime('%d/%m/%Y %H:%M') if ddt.Fecha else 'N/A',
        'lines': len(products),
        'products': products
    }]
    
    # Preparare i totali per il template
    totals = {
        'total_without_vat': float(ddt.ImporteTotalSinIVAConDtoL) if ddt.ImporteTotalSinIVAConDtoL else 0,
        'total_vat': float(ddt.ImporteTotalDelIVAConDtoLConDtoTotal) if ddt.ImporteTotalDelIVAConDtoLConDtoTotal else 0,
        'total': float(ddt.ImporteTotal) if ddt.ImporteTotal else 0
    }
    
    return render_template('ddt/detail.html',
                          ddt=ddt,
                          cliente=cliente,
                          empresa=empresa,
                          tickets=tickets,
                          totals=totals,
                          total_items=total_items)

@ddt_bp.route('/<int:ddt_id>/delete', methods=['POST'])
@login_required
def delete(ddt_id):
    """Delete a DDT and all its lines"""
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    form = DDTDeleteForm()
    
    if form.validate_on_submit() and form.confirm.data:
        try:
            # Start transaction
            # Prima di eliminare il DDT, ottieni tutti i ticket associati
            albaran_lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
            
            # Raggruppiamo le linee per ticket per evitare duplicati
            ticket_ids = {}
            for line in albaran_lines:
                # Chiave composta
                key = (line.IdEmpresa, line.IdTienda, line.IdBalanzaMaestra, line.IdBalanzaEsclava, line.TipoVenta)
                if key not in ticket_ids:
                    ticket_ids[key] = []
                
                # Aggiungiamo l'id del ticket se non è già presente
                if line.IdArticulo not in ticket_ids[key]:
                    ticket_ids[key].append(line.IdArticulo)
            
            # Per ogni ticket, reimpostalo come pendente
            for key in ticket_ids:
                empresa_id, tienda_id, balanza_maestra_id, balanza_esclava_id, tipo_venta = key
                
                # Trova il ticket e reimpostalo come pendente
                for articulo_id in ticket_ids[key]:
                    ticket = TicketHeader.query.filter_by(
                        IdEmpresa=empresa_id,
                        IdTienda=tienda_id,
                        IdBalanzaMaestra=balanza_maestra_id,
                        IdBalanzaEsclava=balanza_esclava_id,
                        TipoVenta=tipo_venta
                    ).first()
                
                if ticket:
                    ticket.Enviado = 0  # Reimposta il ticket come pendente
                    print(f"Reset ticket {ticket.IdTicket} to pending state")
            
            # Elimina tutte le linee (il cascade delete le eliminerà automaticamente)
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
    form = DDTExportForm()
    ddt = AlbaranCabecera.query.filter_by(IdAlbaran=ddt_id).first_or_404()
    
    if form.validate_on_submit():
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
        title=f"DDT #{ddt.IdAlbaran}",
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
        [logo, Paragraph(f"<font size='16'><b>DOCUMENTO DI TRASPORTO</b></font><br/><font color='#7f8c8d'>D.D.T. n° {ddt.IdAlbaran} del {ddt.Fecha.strftime('%d/%m/%Y') if ddt.Fecha else 'N/A'}</font>", styles['DDTTitle'])]
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
    
    # Prepara i dati del mittente e destinatario
    sender_address = f"{ddt.DireccionEmpresa or 'N/A'}<br/>{ddt.PoblacionEmpresa or 'N/A'}<br/>P.IVA: {ddt.CIF_VAT_Empresa or 'N/A'}<br/>Tel: {ddt.TelefonoEmpresa or 'N/A'}"
    recipient_address = f"{ddt.DireccionCliente or 'N/A'}<br/>{ddt.PoblacionCliente or 'N/A'}<br/>P.IVA/CF: {ddt.DNICliente or 'N/A'}<br/>Tel: {ddt.TelefonoCliente or 'N/A'}"
    sender_name = ddt.NombreEmpresa
    recipient_name = ddt.NombreCliente
    
    company_data = [
        [
            # Mittente (a sinistra)
            Table([
                [Paragraph("<b>MITTENTE</b>", styles['DDTTableHeader'])],
                [Paragraph(f"<b>{sender_name}</b><br/>" + sender_address, styles['DDTNormal'])],
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
                [Paragraph(f"<b>{recipient_name}</b><br/>" + recipient_address, styles['DDTNormal'])],
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
    
    # Imposta le informazioni del DDT
    ddt_info_data = [
        [
            Paragraph("<b>Data Emissione:</b>", styles['DDTNormal']), 
            Paragraph(f"{ddt.Fecha.strftime('%d/%m/%Y') if ddt.Fecha else 'N/A'}", styles['DDTNormal']),
            Paragraph("<b>Numero DDT:</b>", styles['DDTNormal']), 
            Paragraph(f"{ddt.IdAlbaran}", styles['DDTNormal']),
            Paragraph("<b>Tipo:</b>", styles['DDTNormal']),
            Paragraph(f"{ddt.Tipo}", styles['DDTNormal'])
        ],
        [
            Paragraph("<b>Totale Articoli:</b>", styles['DDTNormal']), 
            Paragraph(f"{ddt.NumLineas or 0}", styles['DDTNormal']),
            Paragraph("<b>Totale Imponibile:</b>", styles['DDTNormal']),
            Paragraph(f"€ {float(ddt.ImporteTotalSinIVAConDtoL or 0):.2f}", styles['DDTNormal']),
            Paragraph("<b>Totale IVA:</b>", styles['DDTNormal']),
            Paragraph(f"€ {float(ddt.ImporteTotalDelIVAConDtoLConDtoTotal or 0):.2f}", styles['DDTNormal'])
        ]
    ]
    
    ddt_info_table = Table(ddt_info_data, colWidths=[30*mm, 30*mm, 30*mm, 30*mm, 30*mm, 30*mm])
    ddt_info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (0, -1), light_gray),
        ('BACKGROUND', (2, 0), (2, -1), light_gray),
        ('BACKGROUND', (4, 0), (4, -1), light_gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
    ]))
    
    elements.append(ddt_info_table)
    elements.append(Spacer(1, 10*mm))
    
    # Get all product details for this DDT
    products_data = []
    
    # Product table header
    products_data.append([
        Paragraph("<b>Codice</b>", styles['DDTTableHeader']),
        Paragraph("<b>Descrizione</b>", styles['DDTTableHeader']),
        Paragraph("<b>Quantità</b>", styles['DDTTableHeader']),
        Paragraph("<b>Prezzo Unit.</b>", styles['DDTTableHeader']),
        Paragraph("<b>IVA %</b>", styles['DDTTableHeader']),
        Paragraph("<b>Subtotale</b>", styles['DDTTableHeader']),
        Paragraph("<b>Totale</b>", styles['DDTTableHeader']),
    ])
    
    # Add product rows
    # Get product data from AlbaranLinea
    lines = AlbaranLinea.query.filter_by(IdAlbaran=ddt.IdAlbaran).all()
    
    for line in lines:
        # Calcola aliquota IVA
        vat_rate = float(line.PorcentajeIVA or 0) / 100
        vat_display = f"{float(line.PorcentajeIVA or 0):.0f}%"
        
        # Calcola prezzi
        price = float(line.PrecioSinIVA or 0)
        subtotal = float(line.ImporteSinIVASinDtoL or 0)
        vat_amount = float(line.ImporteDelIVAConDtoL or 0)
        total = subtotal + vat_amount
        
        # Aggiungi riga prodotto
        products_data.append([
            Paragraph(f"{line.IdArticulo}", styles['DDTNormal']),
            Paragraph(f"{line.Descripcion}", styles['DDTNormal']),
            Paragraph(f"{float(line.Peso or 1):.3f} {line.Medida2 or 'kg'}", styles['DDTNormal']),
            Paragraph(f"€ {price:.2f}", styles['DDTNormal']),
            Paragraph(f"{vat_display}", styles['DDTNormal']),
            Paragraph(f"€ {subtotal:.2f}", styles['DDTNormal']),
            Paragraph(f"€ {total:.2f}", styles['DDTNormal']),
        ])
    
    # Add totals row
    total_without_vat = float(ddt.ImporteTotalSinIVAConDtoL or 0)
    total_vat = float(ddt.ImporteTotalDelIVAConDtoLConDtoTotal or 0)
    total = float(ddt.ImporteTotal or 0)
    
    products_data.append([
        Paragraph("", styles['DDTNormal']),
        Paragraph("", styles['DDTNormal']),
        Paragraph("", styles['DDTNormal']),
        Paragraph("", styles['DDTNormal']),
        Paragraph("<b>TOTALI:</b>", styles['DDTTableHeader']),
        Paragraph(f"<b>€ {total_without_vat:.2f}</b>", styles['DDTTableHeader']),
        Paragraph(f"<b>€ {total:.2f}</b>", styles['DDTTableHeader']),
    ])
    
    # Create products table with improved styling
    col_widths = [20*mm, 70*mm, 25*mm, 25*mm, 15*mm, 25*mm, 25*mm]
    products_table = Table(products_data, colWidths=col_widths, repeatRows=1)
    
    products_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
        ('TOPPADDING', (0, 0), (-1, 0), 7),
        ('GRID', (0, 0), (-1, -1), 0.25, medium_gray),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (2, 1), (6, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('BACKGROUND', (0, -1), (-1, -1), light_gray),
        ('FONTNAME', (4, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    # Add product table to document
    elements.append(Paragraph("<b>DETTAGLIO PRODOTTI</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 3*mm))
    elements.append(products_table)
    elements.append(Spacer(1, 10*mm))
    
    # Notes section
    elements.append(Paragraph("<b>NOTE E CONDIZIONI DI TRASPORTO</b>", styles['DDTSectionHeader']))
    elements.append(Spacer(1, 3*mm))
    
    notes_data = [
        [
            Paragraph("<b>Causale trasporto:</b>", styles['DDTNormal']),
            Paragraph("Vendita", styles['DDTNormal']),
            Paragraph("<b>Trasporto a cura di:</b>", styles['DDTNormal']),
            Paragraph("Mittente", styles['DDTNormal'])
        ],
        [
            Paragraph("<b>Aspetto dei beni:</b>", styles['DDTNormal']),
            Paragraph("Scatole/Confezioni", styles['DDTNormal']),
            Paragraph("<b>Porto:</b>", styles['DDTNormal']),
            Paragraph("Franco", styles['DDTNormal'])
        ]
    ]
    
    notes_table = Table(notes_data, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    notes_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.25, medium_gray),
        ('BACKGROUND', (0, 0), (0, -1), light_gray),
        ('BACKGROUND', (2, 0), (2, -1), light_gray),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
    ]))
    
    elements.append(notes_table)
    elements.append(Spacer(1, 15*mm))
    
    # Signatures section
    signature_data = [
        [
            Paragraph("<b>Firma del conducente:</b>", styles['DDTNormal']),
            Paragraph("<b>Firma del destinatario:</b>", styles['DDTNormal'])
        ],
        [
            Paragraph("_____________________________", styles['DDTNormal']),
            Paragraph("_____________________________", styles['DDTNormal'])
        ]
    ]
    
    signature_table = Table(signature_data, colWidths=[doc.width/2.0 - 5*mm, doc.width/2.0 - 5*mm])
    signature_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 25),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
    ]))
    
    elements.append(signature_table)
    
    # Define dynamic footer
    def footer(canvas, doc):
        canvas.saveState()
        footer_text = f"DDT #{ddt.IdAlbaran} - Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, 15*mm, footer_text)
        
        # Add page number
        page_num = canvas.getPageNumber()
        canvas.drawRightString(doc.width + doc.leftMargin, 15*mm, f"Pagina {page_num}")
        
        # Add horizontal line
        canvas.setStrokeColor(accent_color)
        canvas.line(doc.leftMargin, 20*mm, doc.width + doc.leftMargin, 20*mm)
        
        canvas.restoreState()
    
    # Build the document with footer
    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    
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