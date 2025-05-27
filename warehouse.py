from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Product, TicketHeader, TicketLine, ScanLog, Client, Company
from forms import SearchForm, FilterForm, ManualScanForm
from sqlalchemy import func, or_, select
from datetime import datetime, timedelta
import re
import logging
import logging.handlers
import os
from wtforms import SelectField, SubmitField, HiddenField, TextAreaField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired

warehouse_bp = Blueprint('warehouse', __name__)

# Configurazione più robusta del logger
logger = logging.getLogger(__name__)

# Configura un handler che non faccia crash se ci sono problemi di permessi
try:
    # Assicuriamoci che la directory dei log esista
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Proviamo a usare un file handler, ma con un sistema di fallback
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'warehouse.log'),
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3,
            delay=True  # Apertura ritardata del file
        )
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        # Se non possiamo usare il file, usiamo lo stderr come fallback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Usa WARNING invece di INFO per ridurre la verbosità
        logger.addHandler(console_handler)
        logger.warning("Impossibile scrivere sul file di log, usando lo stderr")
except Exception as e:
    # Non dovremmo avere errori qui, ma se succede qualcosa, non blocchiamo l'applicazione
    print(f"Errore nella configurazione del logger: {str(e)}")

@warehouse_bp.route('/')
@warehouse_bp.route('/index')
@login_required
def index():
    """Home page with dashboard overview"""
    # Get summary statistics
    products_count = Product.query.count()
    
    # Get recent tickets (limit to 5)
    recent_tickets = TicketHeader.query.order_by(TicketHeader.Fecha.desc()).limit(5).all()
    
    # Get pending tickets (not processed)
    pending_tickets = TicketHeader.query.filter_by(Enviado=0).count()
    
    # Get recent scans by current user (limit to 5) - only select the columns that exist in DB
    stmt = select(ScanLog.id, ScanLog.user_id, ScanLog.ticket_id, ScanLog.action, ScanLog.timestamp).where(
        ScanLog.user_id == current_user.id
    ).order_by(ScanLog.timestamp.desc()).limit(5)
    recent_scans = db.session.execute(stmt).all()
    
    return render_template('warehouse/index.html', 
                          products_count=products_count,
                          recent_tickets=recent_tickets,
                          pending_tickets=pending_tickets,
                          recent_scans=recent_scans)

# Product catalog and inventory

@warehouse_bp.route('/products')
@login_required
def product_catalog():
    """Product catalog with search and filter functionality - redirects to articles"""
    return redirect(url_for('articles.index'))

@warehouse_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    """Detailed view of a single product - redirects to article view"""
    return redirect(url_for('articles.view', id=product_id))

# Ticket management

@warehouse_bp.route('/tickets')
@login_required
def tickets():
    """List of all tickets with search and filter functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_form = SearchForm()
    
    # Get date range params if provided
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Inizializza query base
    query = TicketHeader.query
    
    # Applica filtro date se fornito
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TicketHeader.Fecha >= start_date_obj)
            search_form.start_date.data = start_date_obj
        except (ValueError, TypeError):
            flash('Formato data di inizio non valido', 'danger')
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            end_date_obj = end_date_obj + timedelta(days=1)  # Include the entire day
            query = query.filter(TicketHeader.Fecha <= end_date_obj)
            search_form.end_date.data = datetime.strptime(end_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            flash('Formato data di fine non valido', 'danger')
    
    # Applica ricerca se presente
    if request.args.get('query'):
        search_term = request.args.get('query').strip()
        search_form.query.data = search_term
        
        # Check if it's a ticket number search (starts with #)
        if search_term.startswith('#'):
            ticket_number = search_term[1:].strip()
            if ticket_number.isdigit():
                query = query.filter(TicketHeader.NumTicket == int(ticket_number))
        else:
            # Default to barcode search
            query = query.filter(TicketHeader.CodigoBarras.like(f'%{search_term}%'))
    
    # Crea subquery per trovare la linea con la data di scadenza più vicina per ogni ticket
    # Questa è la chiave: usiamo lo stesso approccio JOIN per tutti i filtri
    subquery = db.session.query(
        TicketLine.IdTicket,
        TicketLine.IdArticulo,
        TicketLine.FechaCaducidad,
        func.row_number().over(
            partition_by=TicketLine.IdTicket,
            order_by=TicketLine.FechaCaducidad.asc()
        ).label('row_num')
    ).subquery()
    
    # Seleziona solo la prima riga per ogni ticket (quella con la data di scadenza più vicina)
    first_expiring_line = db.session.query(subquery).filter(subquery.c.row_num == 1).subquery()
    
    # Applica filtro di stato
    status = request.args.get('status')
    if status == 'pending':
        query = query.filter_by(Enviado=0)
    elif status == 'processed':
        query = query.filter_by(Enviado=1)
    elif status == 'expiring':
        today = datetime.now()
        seven_days_from_now = today + timedelta(days=7)
        
        # Correggo il filtro scadenza per mostrare SOLO prodotti con data di scadenza
        # Usiamo una subquery per trovare solo i ticket con almeno un prodotto in scadenza
        ticket_ids_with_expiry = db.session.query(TicketLine.IdTicket).filter(
            TicketLine.FechaCaducidad.isnot(None),
            TicketLine.FechaCaducidad <= seven_days_from_now,
            TicketLine.FechaCaducidad >= today
        ).distinct().subquery()
        
        # Usa la subquery per limitare i risultati solo ai ticket trovati
        query = query.join(
            ticket_ids_with_expiry,
            TicketHeader.IdTicket == ticket_ids_with_expiry.c.IdTicket
        )
    
    # Applica ordinamento
    if status == 'expiring':
        # Ottieni i ticket con ordine di scadenza (prima i più urgenti)
        # Join con TicketLine per ordinare per data di scadenza
        expiry_subquery = db.session.query(
            TicketLine.IdTicket,
            func.min(TicketLine.FechaCaducidad).label('min_expiry_date')
        ).filter(
            TicketLine.FechaCaducidad.isnot(None)
        ).group_by(TicketLine.IdTicket).subquery()
        
        tickets = query.join(
            expiry_subquery,
            TicketHeader.IdTicket == expiry_subquery.c.IdTicket
        ).order_by(expiry_subquery.c.min_expiry_date.asc()).paginate(page=page, per_page=per_page)
    else:
        # Ordinamento standard per data per gli altri filtri
        tickets = query.order_by(TicketHeader.Fecha.desc()).paginate(page=page, per_page=per_page)
    
    # Get main product for each ticket
    ticket_products = {}
    for ticket in tickets.items:
        main_product_info = db.session.query(
            TicketLine.IdTicket,
            TicketLine.IdArticulo,
            TicketLine.Descripcion.label('linea_descripcion'),
            Product.Descripcion.label('producto_descripcion')
        ).join(
            Product, 
            TicketLine.IdArticulo == Product.IdArticulo
        ).filter(
            TicketLine.IdTicket == ticket.IdTicket
        ).first()
        
        if main_product_info:
            ticket_products[ticket.IdTicket] = {
                'product_name': main_product_info.producto_descripcion or main_product_info.linea_descripcion,
                'product_id': main_product_info.IdArticulo
            }
    
    # Get the count of lines for each ticket
    ticket_ids = [ticket.IdTicket for ticket in tickets.items]
    ticket_lines_count = {}
    
    if ticket_ids:
        # Count lines for each ticket
        line_counts = db.session.query(
            TicketLine.IdTicket,
            func.count(TicketLine.IdTicket).label('line_count')
        ).filter(
            TicketLine.IdTicket.in_(ticket_ids)
        ).group_by(
            TicketLine.IdTicket
        ).all()
        
        # Create dictionary of ticket_id: line_count
        for ticket_id, line_count in line_counts:
            ticket_lines_count[ticket_id] = line_count
    
    # Count the total expiring tickets for the badge in filter
    today = datetime.now()
    seven_days_from_now = today + timedelta(days=7)
    expiring_count = db.session.query(TicketHeader.IdTicket).distinct().\
        join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket).\
        filter(
            TicketLine.FechaCaducidad.isnot(None),
            TicketLine.FechaCaducidad <= seven_days_from_now,
            TicketLine.FechaCaducidad >= today
        ).count()
    
    return render_template('warehouse/tickets.html', 
                          tickets=tickets,
                          ticket_products=ticket_products,
                          ticket_lines_count=ticket_lines_count,
                          search_form=search_form,
                          current_status=status,
                          expiring_count=expiring_count)

@warehouse_bp.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    """Detailed view of a single ticket"""
    # Get the search form for ticket search functionality
    search_form = SearchForm()
    
    # Handle any search form data from URL parameters
    if request.args.get('query'):
        search_form.query.data = request.args.get('query')
    
    # Get the ticket by ID
    ticket = TicketHeader.query.get_or_404(ticket_id)
    
    # Get all lines for this ticket with explicit join to Product table
    # Ensures correct association between ticket and products
    lines = db.session.query(TicketLine).filter(
        TicketLine.IdTicket == ticket_id
    ).outerjoin(
        Product, TicketLine.IdArticulo == Product.IdArticulo
    ).order_by(
        TicketLine.IdTicket,
        TicketLine.IdArticulo
    ).all()
    
    # Recupera il prodotto principale usando la stessa logica della pagina tickets
    main_product_info = db.session.query(
        TicketLine.IdTicket,
        TicketLine.IdArticulo,
        TicketLine.Descripcion.label('linea_descripcion'),
        TicketLine.FechaCaducidad,
        Product.Descripcion.label('producto_descripcion')
    ).join(
        Product, 
        TicketLine.IdArticulo == Product.IdArticulo
    ).filter(
        TicketLine.IdTicket == ticket_id
    ).first()
    
    # Estrai l'ID articolo dal codice QR per avere priorità
    product_id_from_qr = None
    if ticket.CodigoBarras and len(ticket.CodigoBarras) >= 8:
        try:
            product_id_from_qr = int(ticket.CodigoBarras[4:8])
            # Se troviamo un ID prodotto nel QR, cerchiamo specificamente quel prodotto
            if product_id_from_qr:
                specific_product = db.session.query(
                    TicketLine.IdTicket,
                    TicketLine.IdArticulo,
                    TicketLine.Descripcion.label('linea_descripcion'),
                    TicketLine.FechaCaducidad,
                    Product.Descripcion.label('producto_descripcion')
                ).join(
                    Product, 
                    TicketLine.IdArticulo == Product.IdArticulo
                ).filter(
                    TicketLine.IdTicket == ticket_id,
                    TicketLine.IdArticulo == product_id_from_qr
                ).first()
                
                if specific_product:
                    main_product_info = specific_product
        except (ValueError, TypeError):
            logger.warning(f"Ticket #{ticket.NumTicket}: ID articolo dal QR non valido")
    
    # Prepara i dati del prodotto principale
    main_product = {
        'id': None,
        'name': "Nessun prodotto",
        'description': None,
        'expiration_date': None
    }
    
    if main_product_info:
        main_product['id'] = main_product_info.IdArticulo
        main_product['name'] = main_product_info.producto_descripcion or main_product_info.linea_descripcion
        main_product['description'] = main_product_info.linea_descripcion
        main_product['expiration_date'] = main_product_info.FechaCaducidad
    
    # Check for soon-to-expire products
    today = datetime.now()
    expiring_soon = False
    expired = False
    
    for line in lines:
        if line.FechaCaducidad:
            days_to_expire = (line.FechaCaducidad - today).days
            if days_to_expire <= 2 and days_to_expire >= 0:
                expiring_soon = True
            elif days_to_expire < 0:
                expired = True
    
    # Count the total expiring tickets for the badge in filter
    seven_days_from_now = today + timedelta(days=7)
    expiring_count = db.session.query(TicketHeader.IdTicket).distinct().\
        join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket).\
        filter(
            TicketLine.FechaCaducidad.isnot(None),
            TicketLine.FechaCaducidad <= seven_days_from_now,
            TicketLine.FechaCaducidad >= today
        ).count()
    
    # Log this view
    log = ScanLog(
        user_id=current_user.id,
        ticket_id=ticket_id,
        action='view'
    )
    db.session.add(log)
    db.session.commit()
    
    return render_template('warehouse/ticket_detail.html', 
                          ticket=ticket,
                          lines=lines,
                          expiring_soon=expiring_soon,
                          expired=expired,
                          search_form=search_form,
                          expiring_count=expiring_count,
                          main_product=main_product)

@warehouse_bp.route('/ticket/<int:ticket_id>/checkout', methods=['POST'])
@login_required
def ticket_checkout(ticket_id):
    """Process a ticket (mark as processed/checked out)"""
    ticket = TicketHeader.query.get_or_404(ticket_id)
    
    if ticket.Enviado == 1:
        flash('This ticket has already been processed.', 'warning')
    else:
        # Mark the ticket as processed
        ticket.Enviado = 1
        
        # Log this checkout
        log = ScanLog(
            user_id=current_user.id,
            ticket_id=ticket_id,
            action='checkout'
        )
        db.session.add(log)
        db.session.commit()
        
        flash('Ticket processed successfully!', 'success')
    
    return redirect(url_for('warehouse.ticket_detail', ticket_id=ticket_id))

# Scanner

@warehouse_bp.route('/scanner', methods=['GET', 'POST'])
@login_required
def scanner():
    """QR code scanner page"""
    form = ManualScanForm()
    
    if form.validate_on_submit():
        ticket_code = form.ticket_id.data.strip()
        
        # Check for QR code format: NumTicket(4)-IdArticolo(4)-Peso(5)-Timestamp(14)
        if ticket_code.isdigit() and len(ticket_code) == 27:
            # Parse the QR components
            ticket_num = int(ticket_code[:4])           # First 4 digits = NumTicket
            product_id = int(ticket_code[4:8])          # Next 4 digits = IdArticolo
            weight = int(ticket_code[8:13]) / 1000.0    # Next 5 digits = Peso (in grams, convert to kg)
            
            # Parse timestamp - format: DDMMYYYYHHMMSS
            timestamp_str = ticket_code[13:27]
            day = timestamp_str[0:2]
            month = timestamp_str[2:4]
            year = timestamp_str[4:8]
            hour = timestamp_str[8:10]
            minute = timestamp_str[10:12]
            second = timestamp_str[12:14]
            
            formatted_date = f"{day}/{month}/{year}"
            formatted_time = f"{hour}:{minute}:{second}"
            
            # Convert timestamp to datetime object (for comparison)
            try:
                timestamp_dt = datetime.strptime(timestamp_str, "%d%m%Y%H%M%S")
            except ValueError:
                timestamp_dt = None
            
            # Find tickets with matching NumTicket
            tickets = TicketHeader.query.filter_by(NumTicket=ticket_num).all()
            
            # If there are multiple tickets with the same NumTicket, try to find the one closest to the timestamp
            matching_ticket = None
            if tickets:
                if len(tickets) == 1:
                    # If there's only one ticket, use it
                    matching_ticket = tickets[0]
                elif timestamp_dt:
                    # Find the ticket with date closest to the timestamp in QR code
                    min_diff = None
                    for t in tickets:
                        if t.Fecha:  # Make sure ticket has a date
                            diff = abs((t.Fecha - timestamp_dt).total_seconds())
                            if min_diff is None or diff < min_diff:
                                min_diff = diff
                                matching_ticket = t
                    
                    # If we still don't have a match, use the first one as fallback
                    if not matching_ticket:
                        matching_ticket = tickets[0]
                else:
                    # If no timestamp, use the first ticket as fallback
                    matching_ticket = tickets[0]
            
            # Find the product
            product = Product.query.filter_by(IdArticulo=product_id).first()
            
            # Log the scan in scan_log table
            log = ScanLog(
                user_id=current_user.id,
                ticket_id=matching_ticket.IdTicket if matching_ticket else None,
                action='scan',
                raw_code=ticket_code,
                product_code=product_id,
                scan_date=formatted_date,
                scan_time=formatted_time
            )
            db.session.add(log)
            db.session.commit()
            
            if matching_ticket:
                # Check if this product is in the ticket
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=matching_ticket.IdTicket,
                    IdArticulo=product_id
                ).first()
                
                # Check for expiration date
                expiration_msg = ""
                if ticket_line and ticket_line.FechaCaducidad:
                    today = datetime.now()
                    days_to_expire = (ticket_line.FechaCaducidad - today).days
                    
                    if days_to_expire <= 2 and days_to_expire >= 0:
                        expiration_msg = f" - ATTENZIONE: Prodotto in scadenza tra {days_to_expire} giorni!"
                    elif days_to_expire < 0:
                        expiration_msg = f" - ATTENZIONE: Prodotto SCADUTO da {abs(days_to_expire)} giorni!"
                
                flash(f'QR Code elaborato: Ticket #{ticket_num}, Prodotto #{product_id}, Peso: {weight:.3f}kg{expiration_msg}', 
                      'warning' if expiration_msg else 'success')
                return redirect(url_for('warehouse.ticket_detail', ticket_id=matching_ticket.IdTicket))
            else:
                flash(f'Ticket {ticket_num} non trovato.', 'danger')
        else:
            flash('Formato QR code non valido. Inserisci un codice a 27 cifre nel formato corretto.', 'danger')
    
    return render_template('warehouse/scanner.html', form=form)

# Add a new endpoint to process product checkout
@warehouse_bp.route('/api/checkout', methods=['POST'])
@login_required
def api_checkout():
    """API endpoint to process a product checkout from a scan"""
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    scan_log_id = data.get('scan_log_id')
    ticket_id = data.get('ticket_id')
    
    if scan_log_id:
        # Find the scan log entry
        log = ScanLog.query.get(scan_log_id)
        if not log:
            return jsonify({'success': False, 'error': 'Scan log not found'}), 404
        
        # Update the scan log
        log.action = 'checkout'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Product marked as checked out successfully'
        })
    
    elif ticket_id:
        # Find the ticket
        ticket = TicketHeader.query.get(ticket_id)
        if not ticket:
            return jsonify({'success': False, 'error': 'Ticket not found'}), 404
        
        # Update the ticket status
        ticket.Enviado = 1
        
        # Log this checkout
        log = ScanLog(
            user_id=current_user.id,
            ticket_id=ticket.IdTicket,
            action='checkout'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Ticket processed successfully'
        })
    
    return jsonify({'success': False, 'error': 'Missing scan_log_id or ticket_id'}), 400

# Process QR code scan
@warehouse_bp.route('process_qr', methods=['POST'])
@login_required
def process_qr():
    """Process the QR code and return its contents in JSON format"""
    data = request.json
    
    if not data or 'qr_data' not in data:
        return jsonify({
            'success': False, 
            'message': 'No QR code data provided'
        }), 400
    
    qr_data = data['qr_data'].strip()
    
    if qr_data.isdigit() and len(qr_data) == 27:
        try:
            ticket_num_str = qr_data[:4]
            product_id_str = qr_data[4:8]
            weight_str = qr_data[8:13] # Peso in grammi
            timestamp_str = qr_data[13:27]

            ticket_num = int(ticket_num_str)
            product_id = int(product_id_str)
            weight_grams = int(weight_str)
            weight_kg = weight_grams / 1000.0

            day = timestamp_str[0:2]
            month = timestamp_str[2:4]
            year = timestamp_str[4:8]
            hour = timestamp_str[8:10]
            minute = timestamp_str[10:12]
            second = timestamp_str[12:14]
            
            formatted_scan_date = f"{day}/{month}/{year}"
            formatted_scan_time = f"{hour}:{minute}:{second}"
            
            try:
                timestamp_dt = datetime.strptime(timestamp_str, "%d%m%Y%H%M%S")
            except ValueError:
                timestamp_dt = None
            
            tickets = TicketHeader.query.filter_by(NumTicket=ticket_num).all()
            matching_ticket = None
            if tickets:
                if len(tickets) == 1:
                    matching_ticket = tickets[0]
                elif timestamp_dt:
                    min_diff = None
                    for t in tickets:
                        if t.Fecha:
                            diff = abs((t.Fecha - timestamp_dt).total_seconds())
                            if min_diff is None or diff < min_diff:
                                min_diff = diff
                                matching_ticket = t
                    if not matching_ticket: # Fallback if timestamp logic fails
                        matching_ticket = tickets[0]
                else:
                    matching_ticket = tickets[0] # Fallback if no timestamp in QR
            
            product = Product.query.filter_by(IdArticulo=product_id).first()
            
            log = ScanLog(
                user_id=current_user.id,
                ticket_id=matching_ticket.IdTicket if matching_ticket else None,
                action='scan_attempt', # Changed from 'scan' to 'scan_attempt' initially
                raw_code=qr_data,
                product_code=product_id,
                scan_date=formatted_scan_date,
                scan_time=formatted_scan_time
            )
            db.session.add(log)
            db.session.flush() # Get log.id before full commit
            
            if matching_ticket and product:
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=matching_ticket.IdTicket,
                    IdArticulo=product_id
                ).first()
                
                if ticket_line:
                    log.action = 'scan_success' # Update action to success
                    expiration_info = None
                    # ... (keep existing expiration logic here if present) ...

                    # Determina il peso/quantità corretti basandosi su comportamiento
                    if ticket_line.comportamiento == 0:  # Unità
                        display_weight = str(int(weight_kg)) if weight_kg == int(weight_kg) else str(weight_kg)
                        weight_unit = "unità"
                    else:  # kg
                        display_weight = f"{weight_kg:.3f}".rstrip('0').rstrip('.')
                        weight_unit = "kg"

                    db.session.commit() # Commit the log and any other changes
                    return jsonify({
                        'success': True,
                        'ticket_id': matching_ticket.IdTicket,
                        'ticket_number': matching_ticket.NumTicket,
                        'ticket_date': matching_ticket.formatted_date, # Assuming formatted_date exists on model
                        'scan_date': f"{formatted_scan_date} {formatted_scan_time}",
                        'is_processed': matching_ticket.Enviado == 1, 
                        'enviado': str(matching_ticket.Enviado) if matching_ticket.Enviado is not None else "0",
                        'product': {
                            'id': product.IdArticulo,
                            'name': product.Descripcion,
                            'code': product.IdArticulo, # Assuming code is IdArticulo, adjust if different
                            'weight': f"{display_weight} {weight_unit}",
                            'comportamiento': ticket_line.comportamiento  # Aggiungo il comportamiento
                        },
                        # 'expiration': expiration_info, # Add back if logic is present
                        'scan_log_id': log.id
                    })
                else:
                    # Product not in this specific ticket
                    log.action = 'scan_fail_product_not_in_ticket'
                    db.session.commit()
                    return jsonify({
                        'success': False,
                        'message': f'Prodotto {product_id} ({product.Descripcion if product else "N/A"}) non trovato nel ticket {ticket_num}.',
                        'ticket_number': ticket_num,
                        'product_id': product_id,
                        'scan_log_id': log.id
                    })
            
            # Handle cases where ticket or product is not found
            log_message = ""
            if not matching_ticket and not product:
                log_message = f'Ticket {ticket_num} e Prodotto {product_id} non trovati.'
                log.action = 'scan_fail_ticket_product_not_found'
            elif not matching_ticket:
                log_message = f'Ticket {ticket_num} non trovato.'
                log.action = 'scan_fail_ticket_not_found'
            elif not product:
                log_message = f'Prodotto {product_id} non trovato.'
                log.action = 'scan_fail_product_not_found'
            
            db.session.commit() # Commit the log
            return jsonify({
                'success': False,
                'message': log_message,
                'scan_log_id': log.id
            })
                
        except Exception as e:
            db.session.rollback() # Rollback if any error during processing
            logger.error(f"Error processing QR data {qr_data}: {str(e)}")
            # Attempt to log the error even if previous log failed
            try:
                error_log = ScanLog(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    action='scan_error',
                    raw_code=qr_data,
                    # product_code=product_id_str if 'product_id_str' in locals() else None
                )
                # db.session.add(error_log)
                # db.session.commit()
            except Exception as log_err:
                logger.error(f"Failed to log scan_error: {str(log_err)}")

            return jsonify({
                'success': False,
                'message': f'Errore durante l\'elaborazione del codice QR: {str(e)}'
            }), 500
    
    return jsonify({
        'success': False,
        'message': f'Formato QR code non valido. Attesi 27 caratteri numerici.'
    }), 400

# Endpoint to assign ticket to DDT
@warehouse_bp.route('/assign_ddt', methods=['POST'])
@login_required
def assign_ddt():
    data = request.json
    ticket_id = data.get('ticket_id')
    ddt_type = data.get('ddt_type') # Should be "2" for DDT1 or "3" for DDT2

    if not ticket_id or not ddt_type:
        return jsonify({'success': False, 'message': 'ID Ticket o tipo DDT mancante'}), 400

    if ddt_type not in ["2", "3"]:
        return jsonify({'success': False, 'message': 'Tipo DDT non valido. Deve essere "2" o "3".'}), 400

    ticket = TicketHeader.query.get(ticket_id)
    if not ticket:
        return jsonify({'success': False, 'message': f'Ticket {ticket_id} non trovato'}), 404

    if ticket.Enviado == 1: 
        return jsonify({'success': False, 'message': f'Ticket {ticket_id} già scaricato e non assegnabile a DDT.'}), 400
    
    # Optional: check if already assigned to the *same* DDT to avoid redundant updates
    # if str(ticket.Enviado) == ddt_type:
    #     return jsonify({'success': True, 'message': f'Ticket {ticket_id} già assegnato a DDT tipo {ddt_type}'})

    original_enviado_status = ticket.Enviado
    ticket.Enviado = int(ddt_type) 
    try:
        # Add ticket to session if it was loaded and modified
        db.session.add(ticket)
        
        # Log this action
        log_action = f'assign_ddt{ddt_type}'
        # Ensure log action string is not too long if there's a constraint
        # max_len_action = 20 # Example, adjust if known
        # if len(log_action) > max_len_action:
        #     log_action = log_action[:max_len_action]

        log = ScanLog(
            user_id=current_user.id,
            ticket_id=ticket.IdTicket,
            action=log_action, 
            raw_code=f'ticket_id:{ticket_id},ddt_type:{ddt_type},prev_enviado:{original_enviado_status}'
        )
        db.session.add(log)
        
        db.session.commit() # Single commit for both operations
        return jsonify({
            'success': True, 
            'message': f'Ticket {ticket_id} assegnato a DDT tipo {ddt_type}',
            'ticket_id_assigned': ticket_id # Add ticket_id to response
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore database assegnazione ticket {ticket_id} a DDT {ddt_type} (prev: {original_enviado_status}): {str(e)}")
        return jsonify({'success': False, 'message': 'Errore database durante l\'assegnazione DDT.'}), 500

# Process checkout from QR scanner
@warehouse_bp.route('checkout', methods=['POST'])
@login_required
def checkout():
    """Checkout a ticket/product from QR scanner"""
    data = request.json
    
    if not data:
        return jsonify({
            'success': False, 
            'message': 'No data provided'
        }), 400
    
    ticket_id = data.get('ticket_id')
    
    if not ticket_id:
        return jsonify({
            'success': False, 
            'message': 'No ticket ID provided'
        }), 400
    
    # Find the ticket
    ticket = TicketHeader.query.get(ticket_id)
    if not ticket:
        return jsonify({
            'success': False, 
            'message': f'Ticket {ticket_id} not found'
        }), 404
    
    # Update ticket status to processed
    ticket.Enviado = 1
    
    # Log this action
    log = ScanLog(
        user_id=current_user.id,
        ticket_id=ticket.IdTicket,
        action='checkout'
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Ticket processed successfully',
        'ticket_id_processed': ticket.IdTicket # Add ticket_id to response
    }) 

@warehouse_bp.route('/get_ddt_items', methods=['GET'])
@login_required
def get_ddt_items():
    try:
        # Fetch items for DDT1 (Enviado = 2)
        # We need to join with Product and potentially TicketLine to get details
        # This is a simplified version; you'll need to adapt it based on your exact data needs for display
        ddt1_tickets = db.session.query(
            TicketHeader.IdTicket,
            TicketHeader.NumTicket,
            Product.Descripcion.label('product_name'),
            TicketLine.Peso.label('product_weight'), # Corretto da UnidadReal a Peso
            TicketLine.comportamiento.label('comportamiento') # Aggiunto campo comportamiento
        ).join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket)\
         .join(Product, TicketLine.IdArticulo == Product.IdArticulo)\
         .filter(TicketHeader.Enviado == 2).all()

        ddt2_tickets = db.session.query(
            TicketHeader.IdTicket,
            TicketHeader.NumTicket,
            Product.Descripcion.label('product_name'),
            TicketLine.Peso.label('product_weight'), # Corretto da UnidadReal a Peso
            TicketLine.comportamiento.label('comportamiento') # Aggiunto campo comportamiento
        ).join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket)\
         .join(Product, TicketLine.IdArticulo == Product.IdArticulo)\
         .filter(TicketHeader.Enviado == 3).all()

        # Convert to list of dicts for JSON response
        ddt1_items = [{'ticket_id': t.IdTicket, 'ticket_number': t.NumTicket, 'product_name': t.product_name, 'product_weight': t.product_weight, 'comportamiento': t.comportamiento} for t in ddt1_tickets]
        ddt2_items = [{'ticket_id': t.IdTicket, 'ticket_number': t.NumTicket, 'product_name': t.product_name, 'product_weight': t.product_weight, 'comportamiento': t.comportamiento} for t in ddt2_tickets]
        
        return jsonify({
            'success': True, 
            'ddt1_items': ddt1_items, 
            'ddt2_items': ddt2_items
        })
    except Exception as e:
        logger.error(f"Error fetching DDT items: {str(e)}")
        return jsonify({'success': False, 'message': 'Errore nel caricamento degli elementi DDT dal database.'}), 500

@warehouse_bp.route('/remove_from_ddt', methods=['POST'])
@login_required
def remove_from_ddt():
    data = request.json
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({'success': False, 'message': 'ID Ticket mancante'}), 400

    ticket = TicketHeader.query.get(ticket_id)
    if not ticket:
        return jsonify({'success': False, 'message': f'Ticket {ticket_id} non trovato'}), 404

    original_enviado_status = ticket.Enviado
    ticket.Enviado = 0 
    try:
        db.session.add(ticket) # Add ticket to session
        
        # Log this action - shorten if necessary
        # Max length observed in error was for 'remove_from_ddt_prev_3' (25 chars)
        # Let's try to be more concise or ensure DB schema allows for more.
        # For now, making it shorter.
        log_action = f'rm_ddt_prv_{original_enviado_status}'


        log = ScanLog(
            user_id=current_user.id,
            ticket_id=ticket.IdTicket,
            action=log_action, 
            raw_code=f'ticket_id:{ticket_id},prev_enviado:{original_enviado_status}'
        )
        db.session.add(log)
        
        db.session.commit() # Single commit
        return jsonify({
            'success': True, 
            'message': f'Ticket {ticket_id} rimosso da DDT e reimpostato.',
            'ticket_id_removed': ticket_id # Add ticket_id to response
            })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore database rimozione ticket {ticket_id} da DDT (prev: {original_enviado_status}): {str(e)}")
        return jsonify({'success': False, 'message': 'Errore database durante la rimozione da DDT.'}), 500 

@warehouse_bp.route('/search_clients', methods=['GET'])
@login_required
def search_clients():
    query_param = request.args.get('query', '').strip()
    clients_list = []
    if len(query_param) < 1: # Potresti voler richiedere almeno 2 o 3 caratteri qui, ma il JS già lo fa
        return jsonify({'success': True, 'clients': []})

    try:
        # Assumendo che il modello Client abbia un campo 'name' o simile per la ricerca
        # e che tu voglia una ricerca case-insensitive che matcha l'inizio del nome.
        # Modifica Client.name con il campo corretto del tuo modello se diverso.
        clients_found = Client.query.filter(Client.NomeCliente.ilike(f'%{query_param}%')).limit(10).all()
        # Oppure, se vuoi cercare in qualsiasi punto del nome: Client.NomeCliente.ilike(f'%{query_param}%'))
        
        clients_list = [{'id': client.IdCliente, 'name': client.NomeCliente} for client in clients_found]
        return jsonify({'success': True, 'clients': clients_list})
    except Exception as e:
        logger.error(f"Error searching clients with query '{query_param}': {str(e)}")
        return jsonify({'success': False, 'message': 'Errore durante la ricerca dei clienti.', 'clients': []}), 500

class DDTGenerationForm(FlaskForm):
    # Assuming Customer model has id and a name/identifier attribute
    # The choices for customer_id would be populated in the route
    customer_id = SelectField('Cliente', validators=[DataRequired(message="Seleziona un cliente.")], coerce=int)
    ddt_type = HiddenField('DDT Type') # To pass along ddt_type (1 or 2)
    ddt_notes = TextAreaField('Note Aggiuntive')
    submit = SubmitField('Genera DDT')

@warehouse_bp.route('/generate_ddt_step', methods=['GET'])
@login_required
def generate_ddt_step():
    ddt_type_param = request.args.get('ddt_type') # This will be "1" or "2" from scanner page
    if not ddt_type_param or ddt_type_param not in ['1', '2']:
        flash('Tipo DDT non valido specificato.', 'danger')
        return redirect(url_for('warehouse.scanner'))

    ddt_enviado_status = 2 if ddt_type_param == '1' else 3
    ddt_type_display_name = f"DDT{ddt_type_param}"

    # Fetch items for the specified DDT (similar to get_ddt_items but for one type)
    try:
        ddt_tickets_query = db.session.query(
            TicketHeader.IdTicket,
            TicketHeader.NumTicket,
            Product.Descripcion.label('product_name'),
            TicketLine.Peso.label('product_weight'), # Corretto da UnidadReal a Peso
            TicketLine.comportamiento.label('comportamiento') # Aggiunto campo comportamiento
        ).join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket)\
         .join(Product, TicketLine.IdArticulo == Product.IdArticulo)\
         .filter(TicketHeader.Enviado == ddt_enviado_status).all()
        
        current_ddt_items = [{
            'ticket_id': t.IdTicket, 
            'ticket_number': t.NumTicket, 
            'product_name': t.product_name, 
            'product_weight': t.product_weight,
            'comportamiento': t.comportamiento
        } for t in ddt_tickets_query]

    except Exception as e:
        logger.error(f"Error fetching items for {ddt_type_display_name}: {str(e)}")
        flash(f'Errore nel recupero degli articoli per {ddt_type_display_name}.', 'danger')
        current_ddt_items = []

    # Fetch customers for the dropdown
    # Replace with your actual Customer model and query
    customers_list = []
    try:
        # Placeholder: replace with your actual Customer model and query
        # Example: customers_list = Customer.query.order_by(Customer.name).all()
        # For now, using a dummy list
        # customers_list = [ consommateur fictif pour le moment
        #     type('DummyCustomer', (object,), {'id': 1, 'name': 'Cliente Prova 1'})(),
        #     type('DummyCustomer', (object,), {'id': 2, 'name': 'Cliente Prova 2'})()
        # ]
        pass # Query customers here
        # Let's assume you have a Customer model like this:
        # class Customer(db.Model):
        #     id = db.Column(db.Integer, primary_key=True)
        #     name = db.Column(db.String(150), nullable=False)
        # customers_list = Customer.query.order_by(Customer.name).all()
        # If you don't have a customer model yet, you need to define it.
        # For the template to work without Flask-WTF for this part:
        mock_customers = [
            {'id': 1, 'name': 'Cliente Demo Alpha'},
            {'id': 2, 'name': 'Cliente Demo Beta'},
            {'id': 3, 'name': 'Cliente Demo Gamma'}
        ]

    except Exception as e:
        logger.error(f"Error fetching customers: {str(e)}")
        flash('Errore nel recupero della lista clienti.', 'danger')
    
    form = DDTGenerationForm()
    form.ddt_type.data = ddt_type_param # pre-fill hidden field
    # Populate customer choices if using Flask-WTF
    # form.customer_id.choices = [(c.id, c.name) for c in customers_list]
    # If not using Flask-WTF for choices, pass customers_list directly to template

    return render_template('warehouse/generate_ddt_step.html',
                           form=form, 
                           ddt_type_display_name=ddt_type_display_name,
                           ddt_type_actual=ddt_type_param, # For the hidden input in template
                           items=current_ddt_items,
                           customers=mock_customers # Pass mock_customers or your actual customers_list
                          )

@warehouse_bp.route('/finalize_ddt_generation', methods=['POST'])
@login_required
def finalize_ddt_generation():
    form = DDTGenerationForm() # If using Flask-WTF to validate submitted data
    ddt_type_submitted = request.form.get('ddt_type') # "1" or "2"
    customer_id_submitted = request.form.get('customer_id')
    ddt_notes = request.form.get('ddt_notes', '')

    # Validate with form if using WTForms
    # if form.validate_on_submit():
    #    customer_id_submitted = form.customer_id.data
    #    ddt_type_submitted = form.ddt_type.data 
    #    ddt_notes = form.ddt_notes.data
    # else:
    #    # Handle validation errors, perhaps re-render the generate_ddt_step page
    #    flash('Errore di validazione. Controlla i campi.', 'danger')
    #    # Need to re-fetch items and customers to re-render
    #    return redirect(url_for('warehouse.generate_ddt_step', ddt_type=ddt_type_submitted))

    if not ddt_type_submitted or ddt_type_submitted not in ['1', '2']:
        flash('Tipo DDT sottomesso non valido.', 'danger')
        return redirect(url_for('warehouse.scanner'))
    
    if not customer_id_submitted:
        flash('ID Cliente non selezionato.', 'danger')
        # This should ideally be caught by client-side validation or form.validate_on_submit()
        return redirect(url_for('warehouse.generate_ddt_step', ddt_type=ddt_type_submitted))
    
    ddt_enviado_status_to_process = 2 if ddt_type_submitted == '1' else 3

    # 1. Fetch all tickets for this DDT (Enviado = ddt_enviado_status_to_process)
    # 2. Create a new DDT Header record in your database (e.g., in a DdtHeader table)
    #    - Link it to the customer_id
    #    - Store ddt_notes, generation date, ddt_number etc.
    # 3. For each ticket fetched in step 1:
    #    - Create DDT Line items (e.g., in DdtLine table) linking to the new DdtHeader and the product/ticket details.
    #    - Update the original TicketHeader.Enviado status to a new status indicating it's been processed into a DDT (e.g., 4 = "In DDT", 5 = "DDT Generato")
    #    - Or, if these tickets are considered "consumed" by the DDT, maybe they are archived or their status reflects that.
    # 4. Potentially generate a PDF or other document for the DDT.
    # 5. Commit database changes.
    # 6. Redirect to a success page or the DDT detail page.

    logger.info(f"Inizio generazione DDT{ddt_type_submitted} per cliente ID: {customer_id_submitted}. Note: {ddt_notes}")
    
    # ---- THIS IS A PLACEHOLDER FOR ACTUAL DDT GENERATION LOGIC ----
    try:
        # Example: Find tickets to include
        tickets_for_ddt = TicketHeader.query.filter_by(Enviado=ddt_enviado_status_to_process).all()
        if not tickets_for_ddt:
            flash(f'Nessun articolo trovato da includere in DDT{ddt_type_submitted}.', 'warning')
            return redirect(url_for('warehouse.generate_ddt_step', ddt_type=ddt_type_submitted))

        # Create DdtHeader (assuming you have a DdtHeader model)
        # new_ddt = DdtHeader(customer_id=customer_id_submitted, ddt_type=ddt_type_submitted, notes=ddt_notes, date_generated=datetime.utcnow())
        # db.session.add(new_ddt)
        # db.session.flush() # To get new_ddt.id

        for ticket in tickets_for_ddt:
            # Create DdtLine items (assuming DdtLine model)
            # for line_item in ticket.lines: # Assuming ticket.lines is a relationship to TicketLine
            #    ddt_line = DdtLine(ddt_id=new_ddt.id, product_id=line_item.IdArticulo, quantity=line_item.UnidadReal, ticket_ref=ticket.NumTicket)
            #    db.session.add(ddt_line)
            
            # Update ticket status (e.g., Enviado = 4 meaning 'Included in DDT')
            ticket.Enviado = 4 # Or another status indicating it's part of a generated DDT
            db.session.add(ticket)
        
        # db.session.commit()
        # flash(f'DDT{ddt_type_submitted} generato con successo! (ID: {new_ddt.id})', 'success')
        # return redirect(url_for('warehouse.view_ddt', ddt_id=new_ddt.id)) # Or to a success page

        # For now, just a success message and redirect to scanner
        # Simulating work by changing status (actual DDT creation is complex)
        for ticket in tickets_for_ddt:
            ticket.Enviado = 4 # Mark as processed into a DDT
            db.session.add(ticket)
        db.session.commit()
        flash(f'DDT{ddt_type_submitted} per Cliente ID {customer_id_submitted} è stato generato (simulazione). Gli articoli sono stati aggiornati.', 'success')
        return redirect(url_for('warehouse.scanner'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore durante la finalizzazione del DDT: {str(e)}")
        flash('Si è verificato un errore critico durante la generazione del DDT.', 'danger')
        return redirect(url_for('warehouse.generate_ddt_step', ddt_type=ddt_type_submitted))
    # ---- END PLACEHOLDER ---- 

@warehouse_bp.route('/api/company/first')
@login_required
def get_first_company():
    """Get the ID of the first company in the database"""
    try:
        company = Company.query.first()
        if company:
            return jsonify({
                'success': True,
                'id_empresa': company.IdEmpresa,
                'company_name': company.NombreEmpresa
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nessuna azienda configurata nel sistema'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Errore durante il recupero dell\'azienda: {str(e)}'
        }) 

# Add a new API endpoint for real-time ticket search
@warehouse_bp.route('/api/tickets/search')
@login_required
def api_tickets_search():
    """API endpoint for real-time ticket search"""
    query = request.args.get('query', '').strip()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not query and not (start_date or end_date):
        return jsonify([])
    
    # Initialize query
    ticket_query = TicketHeader.query
    
    # Apply date filter if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            ticket_query = ticket_query.filter(TicketHeader.Fecha >= start_date)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            end_date = end_date + timedelta(days=1)  # Include the entire day
            ticket_query = ticket_query.filter(TicketHeader.Fecha <= end_date)
        except ValueError:
            pass
    
    # Apply text search if provided
    if query:
        # Check if it's a ticket number search (starts with #)
        if query.startswith('#'):
            ticket_number = query[1:].strip()
            if ticket_number.isdigit():
                ticket_query = ticket_query.filter(TicketHeader.NumTicket == int(ticket_number))
        else:
            # Otherwise, search by barcode
            ticket_query = ticket_query.filter(TicketHeader.CodigoBarras.like(f'%{query}%'))
    
    # Limit and order results
    tickets = ticket_query.order_by(TicketHeader.Fecha.desc()).limit(10).all()
    
    results = []
    for ticket in tickets:
        # Format date for display
        formatted_date = ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else 'N/A'
        
        # Get the main product for this ticket
        main_product_info = db.session.query(
            TicketLine.IdTicket,
            TicketLine.IdArticulo,
            TicketLine.Descripcion.label('linea_descripcion'),
            Product.Descripcion.label('producto_descripcion')
        ).join(
            Product, 
            TicketLine.IdArticulo == Product.IdArticulo
        ).filter(
            TicketLine.IdTicket == ticket.IdTicket
        ).first()
        
        product_name = 'N/A'
        product_id = None
        
        if main_product_info:
            product_name = main_product_info.producto_descripcion or main_product_info.linea_descripcion or 'N/A'
            product_id = main_product_info.IdArticulo
        
        results.append({
            'id': ticket.IdTicket,
            'number': ticket.NumTicket,
            'formatted_date': formatted_date,
            'barcode': ticket.CodigoBarras or 'N/A',
            'product_name': product_name,
            'product_id': product_id,
            'is_processed': bool(ticket.Enviado),
            'url': url_for('warehouse.ticket_detail', ticket_id=ticket.IdTicket)
        })
    
    return jsonify(results) 