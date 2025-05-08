from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import db, Product, TicketHeader, TicketLine, ScanLog
from forms import SearchForm, FilterForm, ManualScanForm
from sqlalchemy import func, or_, select
import re

warehouse_bp = Blueprint('warehouse', __name__)

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
    
    # Execute paginated query
    tickets = query.order_by(TicketHeader.Fecha.desc()).paginate(page=page, per_page=per_page)
    
    return render_template('warehouse/tickets.html', 
                          tickets=tickets,
                          search_form=search_form,
                          current_status=status)

@warehouse_bp.route('/ticket/<int:ticket_id>')
@login_required
def ticket_detail(ticket_id):
    """Detailed view of a single ticket"""
    ticket = TicketHeader.query.get_or_404(ticket_id)
    
    # Get all lines for this ticket
    lines = TicketLine.query.filter_by(IdTicket=ticket_id).all()
    
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
                          lines=lines)

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
        
        # Check for QR code format: NumTicket(4)-IdArticulo(4)-Peso(5)-Timestamp(14)
        if ticket_code.isdigit() and len(ticket_code) == 27:
            # Parse the QR components
            ticket_num = int(ticket_code[:4])           # First 4 digits = NumTicket
            product_id = int(ticket_code[4:8])          # Next 4 digits = IdArticulo
            weight = int(ticket_code[8:13]) / 1000.0    # Next 5 digits = Peso (in grams, convert to kg)
            
            # Parse timestamp - format: DDMMYYYYHHMMSS
            timestamp = ticket_code[13:27]
            day = timestamp[0:2]
            month = timestamp[2:4]
            year = timestamp[4:8]
            hour = timestamp[8:10]
            minute = timestamp[10:12]
            second = timestamp[12:14]
            
            formatted_date = f"{day}/{month}/{year}"
            formatted_time = f"{hour}:{minute}:{second}"
            
            # Find the ticket
            ticket = TicketHeader.query.filter_by(NumTicket=ticket_num).first()
            
            # Find the product
            product = Product.query.filter_by(IdArticulo=product_id).first()
            
            # Log the scan in scan_log table
            log = ScanLog(
                user_id=current_user.id,
                ticket_id=ticket.IdTicket if ticket else None,
                action='scan',
                raw_code=ticket_code,
                product_code=product_id,
                scan_date=formatted_date,
                scan_time=formatted_time
            )
            db.session.add(log)
            db.session.commit()
            
            if ticket:
                flash(f'QR Code elaborato: Ticket #{ticket_num}, Prodotto #{product_id}, Peso: {weight:.3f}kg', 'success')
                return redirect(url_for('warehouse.ticket_detail', ticket_id=ticket.IdTicket))
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
    
    # New QR code format: NumTicket(4)-IdArticulo(4)-Peso(5)-Timestamp(14)
    # Example: 001000220000108052025093508 (27 characters)
    if qr_data.isdigit() and len(qr_data) == 27:
        try:
            # Parse the QR components
            ticket_num = int(qr_data[:4])           # First 4 digits = NumTicket
            product_id = int(qr_data[4:8])          # Next 4 digits = IdArticulo
            weight = int(qr_data[8:13]) / 1000.0    # Next 5 digits = Peso (in grams, convert to kg)
            
            # Parse timestamp - format: DDMMYYYYHHMMSS
            timestamp = qr_data[13:27]
            day = timestamp[0:2]
            month = timestamp[2:4]
            year = timestamp[4:8]
            hour = timestamp[8:10]
            minute = timestamp[10:12]
            second = timestamp[12:14]
            
            formatted_date = f"{day}/{month}/{year}"
            formatted_time = f"{hour}:{minute}:{second}"
            
            # Find the ticket
            ticket = TicketHeader.query.filter_by(NumTicket=ticket_num).first()
            
            # Find the product
            product = Product.query.filter_by(IdArticulo=product_id).first()
            
            # Log the scan in scan_log table
            log = ScanLog(
                user_id=current_user.id,
                ticket_id=ticket.IdTicket if ticket else None,
                action='scan',
                raw_code=qr_data,
                product_code=product_id,
                scan_date=formatted_date,
                scan_time=formatted_time
            )
            db.session.add(log)
            db.session.commit()
            
            # If both ticket and product exist
            if ticket and product:
                # Check if this product is in the ticket
                ticket_line = TicketLine.query.filter_by(
                    IdTicket=ticket.IdTicket,
                    IdArticulo=product_id
                ).first()
                
                # If ticket_line exists, update the weight if needed
                if ticket_line:
                    return jsonify({
                        'success': True,
                        'ticket_id': ticket.IdTicket,
                        'ticket_number': ticket.NumTicket,
                        'ticket_date': ticket.formatted_date,
                        'scan_date': f"{formatted_date} {formatted_time}",
                        'is_processed': ticket.is_processed,
                        'product': {
                            'id': product.IdArticulo,
                            'name': product.Descripcion,
                            'code': product.IdArticulo,
                            'weight': float(weight)
                        },
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
            elif ticket and not product:
                return jsonify({
                    'success': False,
                    'message': f'Product {product_id} not found',
                    'ticket_id': ticket.IdTicket,
                    'ticket_number': ticket.NumTicket,
                    'scan_log_id': log.id
                })
            
            # If product exists but ticket doesn't
            elif not ticket and product:
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