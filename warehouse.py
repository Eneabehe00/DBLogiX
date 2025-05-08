from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Product, TicketHeader, TicketLine, ScanLog
from forms import SearchForm, FilterForm, ManualScanForm
from sqlalchemy import func, or_, select
from datetime import datetime, timedelta
import re
import logging

warehouse_bp = Blueprint('warehouse', __name__)
logger = logging.getLogger(__name__)

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
    """Product catalog with search and filter functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Initialize forms
    search_form = SearchForm()
    filter_form = FilterForm()
    
    # Get distinct families and subfamilies for filter dropdowns
    families = db.session.query(Product.IdFamilia).distinct().all()
    filter_form.familia.choices = [(0, 'All')] + [(f[0], f'Family {f[0]}') for f in families if f[0] is not None]
    
    subfamilies = db.session.query(Product.IdSubFamilia).distinct().all()
    filter_form.subfamilia.choices = [(0, 'All')] + [(s[0], f'Subfamily {s[0]}') for s in subfamilies if s[0] is not None]
    
    # Initialize query
    query = Product.query
    
    # Apply filters if present
    if request.args.get('familia') and int(request.args.get('familia')) > 0:
        familia_id = int(request.args.get('familia'))
        query = query.filter(Product.IdFamilia == familia_id)
        filter_form.familia.data = familia_id
    
    if request.args.get('subfamilia') and int(request.args.get('subfamilia')) > 0:
        subfamilia_id = int(request.args.get('subfamilia'))
        query = query.filter(Product.IdSubFamilia == subfamilia_id)
        filter_form.subfamilia.data = subfamilia_id
        
    # Apply search if present
    if request.args.get('query'):
        search_term = f"%{request.args.get('query')}%"
        query = query.filter(or_(
            Product.Descripcion.like(search_term),
            Product.CodEAN.like(search_term),
            Product.IdArticulo.like(search_term)
        ))
        search_form.query.data = request.args.get('query')
    
    # Execute paginated query
    products = query.order_by(Product.IdArticulo).paginate(page=page, per_page=per_page)
    
    return render_template('warehouse/products.html', 
                          products=products,
                          search_form=search_form,
                          filter_form=filter_form)

@warehouse_bp.route('/product/<int:product_id>')
@login_required
def product_detail(product_id):
    """Detailed view of a single product"""
    product = Product.query.get_or_404(product_id)
    
    # Get recent ticket lines for this product (limit to 10)
    recent_usage = TicketLine.query.filter_by(
        IdArticulo=product_id
    ).join(TicketHeader).order_by(
        TicketHeader.Fecha.desc()
    ).limit(10).all()
    
    return render_template('warehouse/product_detail.html', 
                          product=product,
                          recent_usage=recent_usage)

# Ticket management

@warehouse_bp.route('/tickets')
@login_required
def tickets():
    """List of all tickets with search and filter functionality"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_form = SearchForm()
    
    # Initialize query
    query = TicketHeader.query
    
    # Apply search if present
    if request.args.get('query'):
        search_term = f"%{request.args.get('query')}%"
        query = query.filter(or_(
            TicketHeader.NumTicket.like(search_term),
            TicketHeader.CodigoBarras.like(search_term)
        ))
        search_form.query.data = request.args.get('query')
    
    # Apply status filter if present
    status = request.args.get('status')
    if status == 'pending':
        query = query.filter_by(Enviado=0)
    elif status == 'processed':
        query = query.filter_by(Enviado=1)
    elif status == 'expiring':
        # For expiration filter, we need to join with TicketLine to get FechaCaducidad
        today = datetime.now()
        seven_days_from_now = today + timedelta(days=7)
        
        try:
            # Alternativa più sicura per verificare se esiste già un join
            # Ricostruiamo la query da zero per assicurarci che sia corretta
            base_query = TicketHeader.query
            
            # Applica le condizioni di ricerca se presenti
            if request.args.get('query'):
                search_term = f"%{request.args.get('query')}%"
                base_query = base_query.filter(or_(
                    TicketHeader.NumTicket.like(search_term),
                    TicketHeader.CodigoBarras.like(search_term)
                ))
            
            # Join con TicketLine e applicazione dei filtri di scadenza
            query = base_query.join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket)
            query = query.filter(
                TicketLine.FechaCaducidad.isnot(None),
                TicketLine.FechaCaducidad <= seven_days_from_now,
                TicketLine.FechaCaducidad >= today
            )
            
            # Distinct per evitare duplicati
            query = query.distinct()
            
            # Esegui subito la query paginata con l'ordinamento per scadenza
            tickets = query.order_by(TicketLine.FechaCaducidad.asc()).paginate(page=page, per_page=per_page)
            
            # Bypass dell'esecuzione normale della query sotto
            skip_normal_query_execution = True
        except Exception as e:
            # Fallback in caso di errore
            logger.error(f"Errore nella query expiring: {str(e)}")
            # Se fallisce, torna ai ticket pendenti
            query = TicketHeader.query.filter_by(Enviado=0)
            skip_normal_query_execution = False
    else:
        skip_normal_query_execution = False
    
    # Execute paginated query with proper ordering
    if status == 'expiring' and skip_normal_query_execution:
        # La query è già stata eseguita sopra
        pass
    elif status == 'expiring':
        # Se siamo qui, c'è stato un fallback dall'errore, usa comunque la data di ordinamento
        tickets = query.order_by(TicketHeader.Fecha.desc()).paginate(page=page, per_page=per_page)
    else:
        # Default ordering by date
        tickets = query.order_by(TicketHeader.Fecha.desc()).paginate(page=page, per_page=per_page)
    
    # Count tickets expiring soon (within 2 days)
    two_days_from_now = datetime.now() + timedelta(days=2)
    
    # Count tickets with products expiring within 7 days
    expiring_count = db.session.query(TicketHeader.IdTicket).distinct()\
        .join(TicketLine, TicketHeader.IdTicket == TicketLine.IdTicket)\
        .filter(TicketLine.FechaCaducidad.isnot(None))\
        .filter(TicketLine.FechaCaducidad <= (datetime.now() + timedelta(days=7)))\
        .count()
    
    # Get product information and expiration dates for each ticket
    ticket_products = {}
    for ticket in tickets.items:
        # Per ogni ticket, estraiamo l'ID articolo direttamente dal codice a barre
        product_id = None
        product_name = "Prodotto sconosciuto"
        expiration_date = None
        
        # Estrai l'ID articolo dal codice a barre (posizioni 4-8)
        if ticket.CodigoBarras and len(ticket.CodigoBarras) >= 8:
            try:
                # Il formato del QR è: NumTicket(4)-IdArticolo(4)-Peso(5)-Timestamp(14)
                product_id = int(ticket.CodigoBarras[4:8])
                logger.info(f"Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket}): trovato ID articolo {product_id} dal QR")
            except (ValueError, IndexError):
                logger.warning(f"Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket}): impossibile estrarre ID articolo dal QR: {ticket.CodigoBarras}")
                product_id = None
        
        # Ottieni le linee del ticket
        ticket_lines = TicketLine.query.filter_by(IdTicket=ticket.IdTicket).all()
        
        # Se non abbiamo trovato l'ID dal QR ma abbiamo delle linee, prova ad usare la prima linea
        if product_id is None and ticket_lines:
            product_id = ticket_lines[0].IdArticulo
            logger.info(f"Ticket #{ticket.NumTicket} (ID: {ticket.IdTicket}): usando ID articolo {product_id} dalla prima linea")
        
        # Cerca il prodotto nel database usando l'ID articolo trovato
        if product_id:
            product = Product.query.filter_by(IdArticulo=product_id).first()
            if product:
                product_name = product.Descripcion
                logger.info(f"Ticket #{ticket.NumTicket}: trovato prodotto '{product_name}' (ID: {product_id})")
            else:
                product_name = f"Prodotto #{product_id}"
                logger.warning(f"Ticket #{ticket.NumTicket}: prodotto con ID {product_id} non trovato nel database")
        
        # Cerca la data di scadenza nelle linee del ticket
        if ticket_lines and product_id:
            # Prima cerca una linea con lo stesso ID prodotto
            matching_line = next((line for line in ticket_lines if line.IdArticulo == product_id), None)
            
            if matching_line and matching_line.FechaCaducidad:
                expiration_date = matching_line.FechaCaducidad
                logger.info(f"Ticket #{ticket.NumTicket}: trovata data scadenza {expiration_date} per prodotto ID {product_id}")
            elif ticket_lines[0].FechaCaducidad:
                # Se non troviamo una linea corrispondente, usa la prima linea
                expiration_date = ticket_lines[0].FechaCaducidad
                logger.info(f"Ticket #{ticket.NumTicket}: usando data scadenza {expiration_date} dalla prima linea")
        
        ticket_products[ticket.IdTicket] = {
            'product_name': product_name,
            'product_id': product_id,
            'expiration_date': expiration_date
        }
    
    return render_template('warehouse/tickets.html', 
                          tickets=tickets,
                          ticket_products=ticket_products,
                          search_form=search_form,
                          current_status=status,
                          expiring_count=expiring_count)

@warehouse_bp.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    """Detailed view of a single ticket"""
    ticket = TicketHeader.query.get_or_404(ticket_id)
    
    # Get all lines for this ticket
    lines = TicketLine.query.filter_by(IdTicket=ticket_id).all()
    
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
                          expired=expired)

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
            product_id = int(ticket_code[4:8])          # Next 4 digits = IdArticulo
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
    
    # Check for QR code format: NumTicket(4)-IdArticolo(4)-Peso(5)-Timestamp(14)
    # Example: 001000220000108052025093508 (27 characters)
    if qr_data.isdigit() and len(qr_data) == 27:
        try:
            # Parse the QR components
            ticket_num = int(qr_data[:4])           # First 4 digits = NumTicket
            product_id = int(qr_data[4:8])          # Next 4 digits = IdArticolo
            weight = int(qr_data[8:13]) / 1000.0    # Next 5 digits = Peso (in grams, convert to kg)
            
            # Parse timestamp - format: DDMMYYYYHHMMSS
            timestamp_str = qr_data[13:27]
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
                # If timestamp can't be parsed, just log it but continue
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
                raw_code=qr_data,
                product_code=product_id,
                scan_date=formatted_date,
                scan_time=formatted_time
            )
            db.session.add(log)
            db.session.commit()
            
            # If both ticket and product exist
            if matching_ticket and product:
                # Check if this product is in the ticket
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=matching_ticket.IdTicket,
                    IdArticulo=product_id
                ).first()
                
                # If ticket_line exists, proceed
                if ticket_line:
                    # Check expiration date
                    expiration_info = None
                    expiring_soon = False
                    expired = False
                    
                    if ticket_line.FechaCaducidad:
                        today = datetime.now()
                        days_to_expire = (ticket_line.FechaCaducidad - today).days
                        
                        if days_to_expire <= 2 and days_to_expire >= 0:
                            expiring_soon = True
                        elif days_to_expire < 0:
                            expired = True
                            
                        expiration_info = {
                            'date': ticket_line.FechaCaducidad.strftime('%d/%m/%Y'),
                            'days_remaining': days_to_expire,
                            'expiring_soon': expiring_soon,
                            'expired': expired
                        }
                    
                    return jsonify({
                        'success': True,
                        'ticket_id': matching_ticket.IdTicket,
                        'ticket_number': matching_ticket.NumTicket,
                        'ticket_date': matching_ticket.formatted_date,
                        'scan_date': f"{formatted_date} {formatted_time}",
                        'is_processed': matching_ticket.is_processed,
                        'product': {
                            'id': product.IdArticulo,
                            'name': product.Descripcion,
                            'code': product.IdArticulo,
                            'weight': float(weight)
                        },
                        'expiration': expiration_info,
                        'scan_log_id': log.id
                    })
                else:
                    # Product is not in the ticket
                    return jsonify({
                        'success': False,
                        'message': f'Product {product_id} not found in ticket {ticket_num}',
                        'ticket_number': ticket_num,
                        'product_id': product_id,
                        'scan_log_id': log.id
                    })
            
            # If ticket exists but product doesn't
            elif matching_ticket and not product:
                return jsonify({
                    'success': False,
                    'message': f'Product {product_id} not found',
                    'ticket_id': matching_ticket.IdTicket,
                    'ticket_number': matching_ticket.NumTicket,
                    'scan_log_id': log.id
                })
            
            # If product exists but ticket doesn't
            elif not matching_ticket and product:
                return jsonify({
                    'success': False,
                    'message': f'Ticket {ticket_num} not found',
                    'product_id': product.IdArticulo,
                    'product_name': product.Descripcion,
                    'scan_log_id': log.id
                })
            
            # Neither ticket nor product exists
            else:
                return jsonify({
                    'success': False,
                    'message': f'Ticket {ticket_num} and Product {product_id} not found',
                    'scan_log_id': log.id
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error processing QR code: {str(e)}'
            }), 400
    
    # Invalid QR format
    return jsonify({
        'success': False,
        'message': f'Invalid QR code format. Expected 27 digits.'
    }), 400

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
        'message': 'Ticket processed successfully'
    }) 