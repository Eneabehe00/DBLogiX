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
        
        # Parse ticket code (expected format: T[number]-P[product])
        match = re.match(r'T(\d+)(?:-P(\d+))?', ticket_code)
        
        if match:
            ticket_num = int(match.group(1))
            product_id = int(match.group(2)) if match.group(2) else None
            
            # Try to find the ticket
            ticket = TicketHeader.query.filter_by(NumTicket=ticket_num).first()
            
            if ticket:
                return redirect(url_for('warehouse.ticket_detail', ticket_id=ticket.IdTicket))
            else:
                flash(f'Ticket {ticket_num} not found.', 'danger')
        else:
            flash('Invalid ticket format. Expected: T[number]-P[product]', 'danger')
    
    return render_template('warehouse/scanner.html', form=form)

@warehouse_bp.route('/api/scan', methods=['POST'])
@login_required
def api_scan():
    """API endpoint for scanner to process QR codes"""
    data = request.json
    
    if not data or 'code' not in data:
        return jsonify({'success': False, 'error': 'No code provided'}), 400
    
    ticket_code = data['code'].strip()
    
    # Try first to parse the new format ticket code (format: 000003000801029042025110211)
    if ticket_code.isdigit() and len(ticket_code) == 27:
        try:
            # Parse the different components
            ticket_num = int(ticket_code[:6])  # First 6 digits = receipt number
            product_code = int(ticket_code[6:12])  # Next 6 digits = product code
            date_str = ticket_code[12:20]  # Next 8 digits = date (DDMMYYYY)
            time_str = ticket_code[20:26]  # Next 6 digits = time (HHMMSS)
            
            # Format date for display: DDMMYYYY to DD/MM/YYYY
            formatted_date = f"{date_str[:2]}/{date_str[2:4]}/{date_str[4:]}"
            # Format time for display: HHMMSS to HH:MM:SS
            formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
            
            # Try to find the ticket
            ticket = TicketHeader.query.filter_by(NumTicket=ticket_num).first()
            
            if not ticket:
                # Create a log entry even if ticket isn't found
                log = ScanLog(
                    user_id=current_user.id,
                    ticket_id=ticket_num,  # Use the number since we don't have an ID
                    action='scan_attempt',
                    raw_code=ticket_code,
                    product_code=product_code,
                    scan_date=formatted_date,
                    scan_time=formatted_time
                )
                db.session.add(log)
                db.session.commit()
                
                # Try to find the product
                product = Product.query.filter_by(IdArticulo=product_code).first()
                
                if product:
                    return jsonify({
                        'success': True,
                        'ticket_number': ticket_num,
                        'ticket_date': f"{formatted_date} {formatted_time}",
                        'is_processed': False,
                        'product_id': product.IdArticulo,
                        'product_name': product.Descripcion,
                        'is_new_format': True,
                        'scan_log_id': log.id
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Product code {product_code} not found.',
                        'is_new_format': True,
                        'ticket_number': ticket_num,
                        'ticket_date': f"{formatted_date} {formatted_time}",
                        'scan_log_id': log.id
                    }), 404
            
            # Create a log entry for successful scan
            log = ScanLog(
                user_id=current_user.id,
                ticket_id=ticket.IdTicket,
                action='scan',
                raw_code=ticket_code,
                product_code=product_code,
                scan_date=formatted_date,
                scan_time=formatted_time
            )
            db.session.add(log)
            
            # Find the specific product in the ticket
            ticket_line = TicketLine.query.filter_by(
                IdTicket=ticket.IdTicket, 
                IdArticulo=product_code
            ).first()
            
            product = None
            if ticket_line:
                product = Product.query.filter_by(IdArticulo=product_code).first()
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'ticket_id': ticket.IdTicket,
                'ticket_number': ticket.NumTicket,
                'ticket_date': ticket.formatted_date,
                'scan_date': f"{formatted_date} {formatted_time}",
                'is_processed': ticket.is_processed,
                'is_new_format': True,
                'product_id': product.IdArticulo if product else None,
                'product_name': product.Descripcion if product else None,
                'scan_log_id': log.id,
                'url': url_for('warehouse.ticket_detail', ticket_id=ticket.IdTicket)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error processing the QR code: {str(e)}',
                'is_new_format': True
            }), 400
    
    # Fall back to the old format (T[number]-P[product])
    match = re.match(r'T(\d+)(?:-P(\d+))?', ticket_code)
    
    if not match:
        return jsonify({
            'success': False, 
            'error': 'Invalid ticket format. Expected: T[number]-P[product] or numeric format'
        }), 400
    
    ticket_num = int(match.group(1))
    product_id = int(match.group(2)) if match.group(2) else None
    
    # Try to find the ticket
    ticket = TicketHeader.query.filter_by(NumTicket=ticket_num).first()
    
    if not ticket:
        return jsonify({
            'success': False, 
            'error': f'Ticket {ticket_num} not found.'
        }), 404
    
    # Return success with ticket details
    return jsonify({
        'success': True,
        'ticket_id': ticket.IdTicket,
        'ticket_number': ticket.NumTicket,
        'ticket_date': ticket.formatted_date,
        'is_processed': ticket.is_processed,
        'url': url_for('warehouse.ticket_detail', ticket_id=ticket.IdTicket)
    })

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