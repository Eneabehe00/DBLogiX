from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, and_, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date
import json
import qrcode
import io
import base64

from models import db, Task, TaskTicket, TaskTicketScan, TaskNotification, TicketHeader, TicketLine, User, Client, AlbaranCabecera, AlbaranLinea, Product
from utils import admin_required

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/')
@login_required
def index():
    """Main tasks page - shows different views based on user role"""
    if current_user.is_admin:
        return redirect(url_for('tasks.admin_dashboard'))
    else:
        return redirect(url_for('tasks.user_dashboard'))


@tasks_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard for task management"""
    # Get filter parameters
    title_filter = request.args.get('title', '').strip()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    priority_filter = request.args.get('priority', '')
    status_filter = request.args.get('status', '')
    
    # Base query
    query = Task.query
    
    # Apply filters
    if title_filter:
        query = query.filter(Task.title.ilike(f'%{title_filter}%'))
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Task.created_at >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Task.created_at < date_to_obj)
        except ValueError:
            pass
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    # Get filtered tasks
    tasks = query.order_by(desc(Task.created_at)).all()
    
    # Update progress for all tasks
    for task in tasks:
        task.update_progress()
    
    # Separate completed and non-completed tasks
    completed_tasks = [task for task in tasks if task.status == 'completed']
    active_tasks = [task for task in tasks if task.status != 'completed']
    
    # Get task statistics
    stats = {
        'total_tasks': Task.query.count(),
        'pending_tasks': Task.query.filter_by(status='pending').count(),
        'in_progress_tasks': Task.query.filter_by(status='in_progress').count(),
        'completed_tasks': Task.query.filter_by(status='completed').count()
    }
    
    # Get users for assignment
    users = User.query.filter_by(is_admin=False).all()
    
    # Get clients for DDT generation
    clients = Client.query.order_by(Client.Nombre).all()
    
    return render_template('tasks/admin_dashboard.html', 
                         active_tasks=active_tasks,
                         completed_tasks=completed_tasks,
                         stats=stats,
                         users=users,
                         clients=clients,
                         current_filters={
                             'title': title_filter,
                             'date_from': date_from,
                             'date_to': date_to,
                             'priority': priority_filter,
                             'status': status_filter
                         },
                         now=datetime.now)


@tasks_bp.route('/user')
@login_required
def user_dashboard():
    """User dashboard for assigned tasks"""
    # Get filter parameters
    title_filter = request.args.get('title', '').strip()
    priority_filter = request.args.get('priority', '')
    status_filter = request.args.get('status', '')
    
    # Base query for tasks assigned to current user
    query = Task.query.filter_by(assigned_to=current_user.id)
    
    # Apply filters
    if title_filter:
        query = query.filter(Task.title.ilike(f'%{title_filter}%'))
    
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    # Get filtered tasks
    assigned_tasks = query.order_by(desc(Task.assigned_at)).all()
    
    # Update progress for assigned tasks
    for task in assigned_tasks:
        task.update_progress()
    
    # Separate completed and non-completed tasks
    completed_tasks = [task for task in assigned_tasks if task.status == 'completed']
    active_tasks = [task for task in assigned_tasks if task.status != 'completed']
    
    # Get task statistics for user
    stats = {
        'total_assigned': len(assigned_tasks),
        'pending': len([t for t in assigned_tasks if t.status == 'pending']),
        'in_progress': len([t for t in assigned_tasks if t.status == 'in_progress']),
        'completed': len([t for t in assigned_tasks if t.status == 'completed'])
    }
    
    # Get unread notifications
    unread_notifications = TaskNotification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(desc(TaskNotification.created_at)).limit(5).all()
    
    return render_template('tasks/user_dashboard.html', 
                         active_tasks=active_tasks,
                         completed_tasks=completed_tasks,
                         stats=stats,
                         notifications=unread_notifications,
                         now=datetime.now)


@tasks_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_task():
    """Create a new task"""
    if request.method == 'POST':
        try:
            # Create new task
            task = Task(
                title=request.form['title'],
                description=request.form.get('description', ''),
                priority=request.form.get('priority', 'medium'),
                created_by=current_user.id,
                deadline=datetime.strptime(request.form['deadline'], '%Y-%m-%dT%H:%M') if request.form.get('deadline') else None
            )
            
            # Generate unique task number
            task.task_number = task.generate_task_number()
            
            # Handle assignment during creation
            assigned_user_id = request.form.get('assigned_user_id')
            if assigned_user_id and assigned_user_id != '':
                task.assigned_to = int(assigned_user_id)
                task.assigned_at = datetime.utcnow()
                task.status = 'assigned'
            
            db.session.add(task)
            db.session.flush()  # Get the task ID
            
            # Add selected tickets to task
            selected_tickets = request.form.getlist('tickets')
            for ticket_id in selected_tickets:
                # Create task ticket relationship
                task_ticket = TaskTicket(
                    task_id=task.id_task,
                    ticket_id=int(ticket_id)
                )
                db.session.add(task_ticket)
                
                # Set ticket status to Enviado=10 (assigned to task)
                ticket = TicketHeader.query.get(int(ticket_id))
                if ticket:
                    ticket.Enviado = 10
            
            # Update progress
            task.update_progress()
            
            # Create notification for assigned user
            if task.assigned_to:
                notification = TaskNotification(
                    task_id=task.id_task,
                    user_id=task.assigned_to,
                    notification_type='task_assigned',
                    title=f'Nuovo Task Assegnato: {task.task_number}',
                    message=f'Ti è stato assegnato il task "{task.title}". Clicca per visualizzare i dettagli.'
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash(f'Task {task.task_number} creato con successo!', 'success')
            return redirect(url_for('tasks.admin_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione del task: {str(e)}', 'error')
    
    # GET request - show form
    available_tickets = TicketHeader.query.filter_by(Enviado=0).order_by(desc(TicketHeader.Fecha)).all()
    
    # Calculate actual line count and load lines for each ticket
    for ticket in available_tickets:
        # Load ticket lines with product details
        ticket_lines = db.session.query(TicketLine).join(
            Product, TicketLine.IdArticulo == Product.IdArticulo
        ).filter(TicketLine.IdTicket == ticket.IdTicket).all()
        
        # Attach lines to ticket object for template access
        ticket.lines = ticket_lines
        
        # Count actual lines in database
        actual_lines = len(ticket_lines)
        # Update NumLineas if it's wrong
        if ticket.NumLineas != actual_lines:
            ticket.NumLineas = actual_lines
            # Don't commit here, just for display
    
    # Get users for assignment
    users = User.query.filter_by(is_admin=False).all()
        
    return render_template('tasks/create_task.html', tickets=available_tickets, users=users)


@tasks_bp.route('/task/<int:task_id>')
@login_required
def view_task(task_id):
    """View task details"""
    task = Task.query.get_or_404(task_id)
    
    # Check permissions
    if not current_user.is_admin and task.assigned_to != current_user.id:
        flash('Non hai il permesso di visualizzare questo task.', 'error')
        return redirect(url_for('tasks.index'))
    
    # Update progress
    task.update_progress()
    
    # Get task tickets with scan progress
    task_tickets = TaskTicket.query.filter_by(task_id=task_id).all()
    for tt in task_tickets:
        tt.update_scan_progress()
    
    # Get users for assignment (admin only)
    users = User.query.filter_by(is_admin=False).all() if current_user.is_admin else []
    
    # Get clients for DDT generation (admin only)
    clients = Client.query.order_by(Client.Nombre).all() if current_user.is_admin else []
    
    return render_template('tasks/view_task.html', 
                         task=task, 
                         task_tickets=task_tickets,
                         users=users,
                         clients=clients,
                         now=datetime.now)


@tasks_bp.route('/task/<int:task_id>/assign', methods=['POST'])
@admin_required
def assign_task(task_id):
    """Assign task to a user"""
    task = Task.query.get_or_404(task_id)
    user_id = request.form.get('user_id')
    
    if user_id:
        task.assigned_to = int(user_id)
        task.assigned_at = datetime.utcnow()
        task.status = 'assigned'
        
        # Create notification for assigned user
        notification = TaskNotification(
            task_id=task.id_task,
            user_id=int(user_id),
            notification_type='task_assigned',
            title=f'Nuovo Task Assegnato: {task.task_number}',
            message=f'Ti è stato assegnato il task "{task.title}". Clicca per visualizzare i dettagli.'
        )
        db.session.add(notification)
        
        db.session.commit()
        flash(f'Task assegnato con successo a {task.assignee.username}!', 'success')
    else:
        flash('Errore: seleziona un utente valido.', 'error')
    
    return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/ticket/<int:task_ticket_id>/process_scan', methods=['POST'])
@login_required
def process_scan(task_ticket_id):
    """Process a scanned code for simplified scanning interface"""
    try:
        task_ticket = TaskTicket.query.get_or_404(task_ticket_id)
        scanned_code = request.form.get('scanned_code', '').strip()
        
        if not scanned_code:
            return jsonify({'success': False, 'message': 'Codice non valido'})
        
        # Check if user has permission
        if not current_user.is_admin and task_ticket.task.assigned_to != current_user.id:
            return jsonify({'success': False, 'message': 'Non autorizzato'})
        
        # Get current product to scan
        ticket_lines = TicketLine.query.filter_by(IdTicket=task_ticket.ticket_id).all()
        scanned_lines = TaskTicketScan.query.filter_by(task_ticket_id=task_ticket_id).all()
        scanned_line_ids = [scan.ticket_line_id for scan in scanned_lines]
        
        # Find next unscanned line
        current_line = None
        for line in ticket_lines:
            if line.IdLineaTicket not in scanned_line_ids:
                current_line = line
                break
        
        if not current_line:
            return jsonify({'success': False, 'message': 'Tutti i prodotti sono già stati scansionati'})
        
        # Validate scanned code matches expected product
        # Here you can implement your QR code validation logic
        # For now, we'll assume the scan is successful if code is not empty
        
        # Create scan record
        scan = TaskTicketScan(
            task_ticket_id=task_ticket_id,
            ticket_line_id=current_line.IdLineaTicket,
            scanned_code=scanned_code,
            scanned_at=datetime.utcnow(),
            scanned_by=current_user.id,
            status='completed'
        )
        db.session.add(scan)
        
        # Update progress
        task_ticket.update_scan_progress()
        task_ticket.task.update_progress()
        
        # Check if ticket is completed
        remaining_lines = [line for line in ticket_lines if line.IdLineaTicket not in scanned_line_ids + [current_line.IdLineaTicket]]
        
        if not remaining_lines:
            # Ticket completed
            task_ticket.status = 'completed'
            task_ticket.completed_at = datetime.utcnow()
            
            # Check if there are more tickets in the task
            task = task_ticket.task
            task.update_progress()
            
            # Find next ticket in task
            next_task_ticket = TaskTicket.query.filter(
                TaskTicket.task_id == task.id_task,
                TaskTicket.status != 'completed',
                TaskTicket.id != task_ticket_id
            ).first()
            
            db.session.commit()
            
            if next_task_ticket:
                return jsonify({
                    'success': True, 
                    'message': 'Prodotto scansionato! Passaggio al prossimo ticket...',
                    'next_ticket_id': next_task_ticket.id
                })
            else:
                # All tickets completed
                task.status = 'completed' if task.progress_percentage == 100 else 'in_progress'
                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Task completato!',
                    'task_completed': True
                })
        else:
            db.session.commit()
            return jsonify({
                'success': True, 
                'message': 'Prodotto scansionato con successo!'
            })
            
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in process_scan: {str(e)}")
        return jsonify({'success': False, 'message': 'Errore durante la scansione'})


@tasks_bp.route('/ticket/<int:task_ticket_id>/scan')
@login_required
def scan_ticket(task_ticket_id):
    """Scan products in a ticket - simplified interface with task-based progress"""
    task_ticket = TaskTicket.query.get_or_404(task_ticket_id)
    
    # Check permissions
    if not current_user.is_admin and task_ticket.task.assigned_to != current_user.id:
        flash('Non hai i permessi per accedere a questo ticket.', 'error')
        return redirect(url_for('tasks.user_dashboard'))
    
    # Get the task and all its tickets
    task = task_ticket.task
    all_task_tickets = TaskTicket.query.filter_by(task_id=task.id_task).order_by(TaskTicket.id).all()
    
    # Calculate task progress (based on completed tickets)
    completed_tickets = [tt for tt in all_task_tickets if tt.status == 'completed']
    total_tickets = len(all_task_tickets)
    completed_count = len(completed_tickets)
    
    # Find the current ticket position (1-based index)
    current_ticket_index = 1
    for i, tt in enumerate(all_task_tickets):
        if tt.id == task_ticket_id:
            current_ticket_index = i + 1
            break
    
    # Get current product to scan from this ticket
    ticket_lines = TicketLine.query.filter_by(IdTicket=task_ticket.ticket_id).all()
    scanned_lines = TaskTicketScan.query.filter_by(task_ticket_id=task_ticket_id, status='success').all()
    scanned_line_ids = [scan.ticket_line_id for scan in scanned_lines]
    
    # Find current product to scan
    current_product = None
    for line in ticket_lines:
        if line.IdLineaTicket not in scanned_line_ids:
            current_product = line
            break
    
    # If no current product, this ticket is completed
    if not current_product:
        # Mark ticket as completed if not already
        if task_ticket.status != 'completed':
            task_ticket.status = 'completed'
            task_ticket.completed_at = datetime.utcnow()
            task_ticket.update_scan_progress()
            task.update_progress()
            db.session.commit()
        
        # Find next incomplete ticket in the task
        next_ticket = None
        for tt in all_task_tickets:
            if tt.status != 'completed':
                next_ticket = tt
                break
        
        if next_ticket:
            # Redirect to next ticket
            flash(f'Ticket #{task_ticket.ticket.NumTicket} completato! Passaggio al prossimo ticket.', 'success')
            return redirect(url_for('tasks.scan_ticket', task_ticket_id=next_ticket.id))
        else:
            # All tickets completed - mark task as completed and redirect to dashboard
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()
            
            # Create notification for admin
            notification = TaskNotification(
                task_id=task.id_task,
                user_id=task.created_by,
                notification_type='task_completed',
                title=f'Task Completato: {task.task_number}',
                message=f'Il task "{task.title}" è stato completato da {current_user.username}.'
            )
            db.session.add(notification)
            db.session.commit()
            
            flash(f'🎉 Task {task.task_number} completato con successo!', 'success')
            return redirect(url_for('tasks.user_dashboard'))
    
    return render_template('tasks/scan_ticket.html',
                         task_ticket=task_ticket,
                         current_product=current_product,
                         # Task-based progress
                         current_ticket_index=current_ticket_index,
                         total_tickets=total_tickets,
                         completed_tickets_count=completed_count,
                         task_progress_percentage=int((completed_count / total_tickets * 100)) if total_tickets > 0 else 0)


@tasks_bp.route('/api/scan', methods=['POST'])
@login_required
def api_scan_product():
    """API endpoint for scanning QR codes"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            current_app.logger.error("Request is not JSON")
            return jsonify({'success': False, 'message': 'Richiesta deve essere in formato JSON'}), 400
        
        data = request.get_json()
        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'success': False, 'message': 'Nessun dato ricevuto'}), 400
        
        task_ticket_id = data.get('task_ticket_id')
        scanned_code = data.get('scanned_code')
        ticket_line_id = data.get('ticket_line_id')
        
        current_app.logger.info(f"🔍 Scan request: task_ticket_id={task_ticket_id}, scanned_code={scanned_code}")
        
        if not task_ticket_id:
            current_app.logger.error("Missing task_ticket_id")
            return jsonify({'success': False, 'message': 'ID ticket task mancante'}), 400
        
        if not scanned_code:
            current_app.logger.error("Missing scanned_code")
            return jsonify({'success': False, 'message': 'Codice scansionato mancante'}), 400
        
        task_ticket = TaskTicket.query.get_or_404(task_ticket_id)
        
        # Check permissions
        if not current_user.is_admin and task_ticket.task.assigned_to != current_user.id:
            return jsonify({'success': False, 'message': 'Permesso negato'}), 403
        
        # Get the ticket line if specified
        ticket_line = None
        if ticket_line_id:
            try:
                ticket_line = TicketLine.query.get(ticket_line_id)
                current_app.logger.info(f"🔍 Ticket line lookup: ID={ticket_line_id}, Found={ticket_line is not None}")
                if ticket_line:
                    current_app.logger.info(f"📋 Ticket line details: IdLineaTicket={ticket_line.IdLineaTicket}, IdTicket={ticket_line.IdTicket}, IdArticulo={getattr(ticket_line, 'IdArticulo', 'MISSING')}")
                    current_app.logger.info(f"🔬 Ticket line type: {type(ticket_line)}")
                    current_app.logger.info(f"🔬 Ticket line attributes: {dir(ticket_line)}")
                else:
                    current_app.logger.warning(f"❌ Ticket line not found for ID: {ticket_line_id}")
            except Exception as e:
                current_app.logger.error(f"❌ Error retrieving ticket line {ticket_line_id}: {str(e)}")
                ticket_line = None
        
        # Parse QR code using warehouse format: NumTicket(4)-IdArticolo(4)-Peso(5)-Timestamp(14)
        try:
            if not (scanned_code.isdigit() and len(scanned_code) == 27):
                raise ValueError("Invalid QR code format - expected 27 digits")
            
            # Parse the QR components
            ticket_num = int(scanned_code[:4])           # First 4 digits = NumTicket
            product_id = int(scanned_code[4:8])          # Next 4 digits = IdArticulo
            weight = int(scanned_code[8:13]) / 1000.0    # Next 5 digits = Peso (in grams, convert to kg)
            
            # Parse timestamp - format: DDMMYYYYHHMMSS
            timestamp_str = scanned_code[13:27]
            day = timestamp_str[0:2]
            month = timestamp_str[2:4]
            year = timestamp_str[4:8]
            hour = timestamp_str[8:10]
            minute = timestamp_str[10:12]
            second = timestamp_str[12:14]
            
            formatted_date = f"{day}/{month}/{year}"
            formatted_time = f"{hour}:{minute}:{second}"
            
            # Convert timestamp to datetime object for verification
            try:
                from datetime import datetime
                timestamp_dt = datetime.strptime(timestamp_str, "%d%m%Y%H%M%S")
            except ValueError:
                timestamp_dt = None
                
        except (ValueError, IndexError) as e:
            # Create failed scan record
            scan_result = TaskTicketScan(
                task_ticket_id=task_ticket_id,
                ticket_line_id=ticket_line_id,
                scanned_by=current_user.id,
                scanned_code=scanned_code,
                status='error',
                error_message='Formato QR code non valido - attesi 27 caratteri numerici'
            )
            db.session.add(scan_result)
            db.session.commit()
            
            return jsonify({
                'success': False, 
                'message': 'QR code non valido. Formato atteso: 27 cifre numeriche.'
            })
        
        # Verify the scanned ticket matches the expected ticket
        success = False
        error_message = None
        status = 'error'
        
        # Get the expected ticket number from task_ticket
        expected_ticket = task_ticket.ticket
        expected_ticket_num = expected_ticket.NumTicket
        
        # Check if ticket number matches
        if ticket_num != expected_ticket_num:
            success = False
            status = 'ticket_mismatch'
            error_message = f'Ticket non corrispondente. Atteso: #{expected_ticket_num}, Scansionato: #{ticket_num}'
        else:
            # Ticket number matches, now check product
            if ticket_line_id and ticket_line:
                # Specific product line selected - verify exact match
                if hasattr(ticket_line, 'IdArticulo') and ticket_line.IdArticulo == product_id:
                    # Perfect match: correct ticket and correct product
                    success = True
                    status = 'success'
                else:
                    # Correct ticket but wrong product for this specific line
                    success = False
                    status = 'product_mismatch'
                    if hasattr(ticket_line, 'IdArticulo'):
                        error_message = f'Prodotto non corrispondente. Atteso: {ticket_line.IdArticulo}, Scansionato: {product_id}'
                    else:
                        error_message = f'Prodotto non corrispondente. Scansionato: {product_id}'
            else:
                # No specific product line selected - verify product exists in this ticket
                ticket_has_product = TicketLine.query.filter_by(
                    IdTicket=expected_ticket.IdTicket,
                    IdArticulo=product_id
                ).first()
                
                if ticket_has_product:
                    # Found the product in this ticket
                    success = True
                    status = 'success'
                    # Update ticket_line_id to the found line for proper record keeping
                    ticket_line_id = ticket_has_product.IdLineaTicket
                    ticket_line = ticket_has_product
                else:
                    success = False
                    status = 'product_not_in_ticket'
                    error_message = f'Prodotto {product_id} non presente nel ticket #{ticket_num}'
        
        # Create scan record with detailed information
        scan_result = TaskTicketScan(
            task_ticket_id=task_ticket_id,
            ticket_line_id=ticket_line_id,
            product_id=product_id if success else None,
            scanned_by=current_user.id,
            scanned_code=scanned_code,
            status=status,
            error_message=error_message,
            # Store additional scan data
            weight_scanned=weight,
            expected_code=f"{expected_ticket_num:04d}{ticket_line.IdArticulo if ticket_line and hasattr(ticket_line, 'IdArticulo') else '????'}"
        )
        db.session.add(scan_result)
        
        # Update progress
        task_ticket.update_scan_progress()
        task_ticket.task.update_progress()
        
        # Check if this specific ticket within the task is now fully verified
        ticket_completed = False
        next_ticket_id = None
        task_completed = False
        
        if success:
            # Check if current ticket is now completed
            if task_ticket.status == 'completed':
                ticket_completed = True
                # Update ticket status to Enviado = 10 (completed in task)
                expected_ticket.Enviado = 10
                current_app.logger.info(f"✅ Ticket #{expected_ticket_num} completato - impostato Enviado = 10")
                
                # Find next incomplete ticket in the task
                all_task_tickets = TaskTicket.query.filter_by(task_id=task_ticket.task_id).order_by(TaskTicket.id).all()
                next_ticket = None
                for tt in all_task_tickets:
                    if tt.status != 'completed' and tt.id != task_ticket.id:
                        next_ticket = tt
                        break
                
                if next_ticket:
                    next_ticket_id = next_ticket.id
                else:
                    # All tickets completed - mark task as completed
                    task_ticket.task.status = 'completed'
                    task_ticket.task.completed_at = datetime.utcnow()
                    task_completed = True
                    
                    # Create notification for admin
                    notification = TaskNotification(
                        task_id=task_ticket.task.id_task,
                        user_id=task_ticket.task.created_by,
                        notification_type='task_completed',
                        title=f'Task Completato: {task_ticket.task.task_number}',
                        message=f'Il task "{task_ticket.task.title}" è stato completato da {current_user.username}.'
                    )
                    db.session.add(notification)
        
        db.session.commit()
        
        if success:
            success_message = f'✅ Ticket #{ticket_num} - Prodotto {product_id} verificato!'
            if weight > 0:
                success_message += f' Peso: {weight:.3f}kg'
            
            response_data = {
                'success': True, 
                'message': success_message,
                'scan_id': scan_result.id,
                'ticket_verified': True,
                'product_verified': True,
                'ticket_completed': ticket_completed,
                'task_completed': task_completed,
                'next_ticket_id': next_ticket_id,
                'scan_details': {
                    'ticket_number': ticket_num,
                    'product_id': product_id,
                    'weight': weight,
                    'scan_date': formatted_date,
                    'scan_time': formatted_time
                }
            }
            
            if ticket_completed and next_ticket_id:
                response_data['message'] += f' Passaggio al prossimo ticket...'
            elif task_completed:
                response_data['message'] = f'🎉 Task {task_ticket.task.task_number} completato!'
            
            return jsonify(response_data)
        else:
            return jsonify({
                'success': False, 
                'message': error_message or 'Errore nella verifica del QR code.',
                'scan_id': scan_result.id,
                'ticket_verified': status != 'ticket_mismatch',
                'product_verified': False,
                'ticket_completed': False,
                'task_completed': False,
                'scan_details': {
                    'ticket_number': ticket_num,
                    'product_id': product_id,
                    'weight': weight,
                    'scan_date': formatted_date,
                    'scan_time': formatted_time,
                    'expected_ticket': expected_ticket_num
                }
            })
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Scan error: {str(e)}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Errore del sistema: {str(e)}'}), 500


@tasks_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@admin_required
def complete_task(task_id):
    """Mark task as ready for DDT generation"""
    task = Task.query.get_or_404(task_id)
    
    if not task.is_completed:
        flash('Il task non può essere completato: non tutti i ticket sono stati verificati.', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    client_id = request.form.get('client_id')
    if not client_id:
        flash('Seleziona un cliente per generare il DDT.', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    try:
        # Generate DDT
        ddt_id = generate_ddt_from_task(task, int(client_id))
        
        task.ddt_generated = True
        task.ddt_id = ddt_id
        task.client_id = int(client_id)
        
        db.session.commit()
        
        flash(f'DDT generato con successo! ID DDT: {ddt_id}', 'success')
        return redirect(url_for('ddt.detail', ddt_id=ddt_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Errore nella generazione del DDT: {str(e)}', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))


def generate_ddt_from_task(task, client_id):
    """Generate a DDT (Documento di Trasporto) from completed task"""
    client = Client.query.get(client_id)
    if not client:
        raise ValueError("Cliente non trovato")
    
    # Create DDT header
    from models import Company
    company = Company.query.first()
    
    # Get next DDT ID using the same logic as ddt.py
    max_id = db.session.query(db.func.max(AlbaranCabecera.IdAlbaran)).scalar() or 0
    next_id = max_id + 1
    
    # Get next DDT number (NumAlbaran)
    max_num_albaran = db.session.query(db.func.max(AlbaranCabecera.NumAlbaran)).scalar() or 0
    next_num = max_num_albaran + 1
    
    ddt_header = AlbaranCabecera(
        # Use the calculated unique ID
        IdAlbaran=next_id,
        NumAlbaran=next_num,
        IdEmpresa=1,  # Default value
        IdTienda=1,   # Default value
        IdBalanzaMaestra=1,  # Default value
        IdBalanzaEsclava=-1,  # Default value
        IdCliente=client.IdCliente,
        NombreCliente=client.Nombre,
        DNICliente=client.DNI,
        EmailCliente=client.Email,
        DireccionCliente=client.Direccion,
        PoblacionCliente=client.Poblacion,
        ProvinciaCliente=client.Provincia,
        CPCliente=client.CodPostal,
        TelefonoCliente=client.Telefono1,
        Fecha=datetime.utcnow(),
        FechaModificacion=datetime.utcnow(),
        Usuario=current_user.username,
        # Company info
        NombreEmpresa=company.NombreEmpresa if company else "Default Company",
        CIF_VAT_Empresa=company.CIF_VAT if company else "",
        DireccionEmpresa=company.Direccion if company else "",
        PoblacionEmpresa=company.Poblacion if company else "",
        CPEmpresa=company.CodPostal if company else "",
        TelefonoEmpresa=company.Telefono1 if company else "",
        # Set default values to match ddt.py structure
        Tipo="A",
        IdVendedor=1,
        NombreVendedor="IL CAPO",
        TipoVenta=2,
        ReferenciaDocumento="",
        ObservacionesDocumento="",
        ImporteLineas=0.0,
        ImporteTotal=0.0,
        ImporteTotalSinIVAConDtoL=0.0,
        ImporteTotalDelIVAConDtoLConDtoTotal=0.0,
        ImporteTotalSinIVAConDtoLConDtoTotal=0.0,
        PreseleccionCliente=1,
        Enviado=0,
        Modificado=1,
        Operacion="A",
        EstadoTicket="C"
    )
    
    db.session.add(ddt_header)
    db.session.flush()  # Get the DDT ID
    
    # Add lines from all task tickets
    line_number = 1
    total_amount = 0
    
    for task_ticket in task.task_tickets:
        for ticket_line in task_ticket.ticket.lines:
            # Only add successfully scanned items
            scan_result = task_ticket.scan_results.filter_by(
                ticket_line_id=ticket_line.IdLineaTicket,
                status='success'
            ).first()
            
            if scan_result:
                ddt_line = AlbaranLinea(
                    IdAlbaran=ddt_header.IdAlbaran,
                    IdLineaAlbaran=line_number,
                    IdEmpresa=ddt_header.IdEmpresa,
                    IdTienda=ddt_header.IdTienda,
                    IdBalanzaMaestra=ddt_header.IdBalanzaMaestra,
                    IdBalanzaEsclava=ddt_header.IdBalanzaEsclava,
                    TipoVenta=ddt_header.TipoVenta,
                    EstadoLinea=0,  # Default value
                    IdTicket=task_ticket.ticket_id,  # Reference to the original ticket
                    IdArticulo=ticket_line.IdArticulo,
                    Descripcion=ticket_line.Descripcion,
                    Comportamiento=1,  # Default value
                    ComportamientoDevolucion=0,  # Default value
                    EntradaManual=0,  # Default value
                    Tara=0,  # Default value
                    Peso=ticket_line.Peso,
                    Medida2="un",  # Default unit
                    PrecioPorCienGramos=0,  # Default value
                    Precio=ticket_line.product.PrecioConIVA if ticket_line.product else 0,
                    PrecioSinIVA=0,  # Will be calculated if needed
                    PorcentajeIVA=0,  # Default VAT
                    RecargoEquivalencia=0,  # Default value
                    Descuento=0,  # Default discount
                    TipoDescuento=1,  # Default discount type
                    Importe=float(ticket_line.Peso) * float(ticket_line.product.PrecioConIVA) if ticket_line.product else 0,
                    ImporteSinOferta=None,
                    ImporteSinIVASinDtoL=0,  # Will be calculated if needed
                    ImporteConIVASinDtoL=None,
                    ImporteSinIVAConDtoL=0,  # Will be calculated if needed
                    ImporteDelIVAConDtoL=0,  # VAT amount
                    ImporteSinIVAConDtoLConDtoTotal=0,
                    ImporteDelIVAConDtoLConDtoTotal=0,
                    ImporteDelRE=0,
                    ImporteDelDescuento=0,
                    ImporteConDtoTotal=0,
                    FechaCaducidad=ticket_line.FechaCaducidad,
                    NombreClase="ARTICOLI",  # Default class name
                    Facturada=0,  # Not invoiced yet
                    CantidadFacturada=0,  # Default value
                    CantidadFacturada2=0,  # Default value
                    HayTaraAplicada=0,  # No tare applied
                    Modificado=1,  # Modified flag
                    Operacion="A",  # Add operation
                    Usuario=current_user.username,
                    TimeStamp=datetime.utcnow()
                )
                db.session.add(ddt_line)
                total_amount += ddt_line.Importe
                line_number += 1
    
    # Update DDT totals
    ddt_header.ImporteLineas = total_amount
    ddt_header.ImporteTotal = total_amount
    ddt_header.NumLineas = line_number - 1
    
    # Update all tickets in this task to Enviado = 1 (processed/sent)
    # This marks them as completed and sent via DDT
    for task_ticket in task.task_tickets:
        ticket = task_ticket.ticket
        ticket.Enviado = 1  # Set to processed/sent status
        current_app.logger.info(f"📦 Ticket #{ticket.NumTicket} impostato come inviato (Enviado = 1) via DDT #{ddt_header.IdAlbaran}")
    
    current_app.logger.info(f"✅ DDT #{ddt_header.IdAlbaran} generato con {line_number - 1} linee, totale: €{total_amount:.2f}")
    
    return ddt_header.IdAlbaran


@tasks_bp.route('/notifications')
@login_required
def notifications():
    """View user notifications with day-based pagination"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    day_before_yesterday = today - timedelta(days=2)
    
    # Get notifications grouped by day
    today_notifications = TaskNotification.query.filter(
        TaskNotification.user_id == current_user.id,
        db.func.date(TaskNotification.created_at) == today
    ).order_by(desc(TaskNotification.created_at)).all()
    
    yesterday_notifications = TaskNotification.query.filter(
        TaskNotification.user_id == current_user.id,
        db.func.date(TaskNotification.created_at) == yesterday
    ).order_by(desc(TaskNotification.created_at)).all()
    
    day_before_notifications = TaskNotification.query.filter(
        TaskNotification.user_id == current_user.id,
        db.func.date(TaskNotification.created_at) == day_before_yesterday
    ).order_by(desc(TaskNotification.created_at)).all()
    
    return render_template('tasks/notifications.html', 
                         today_notifications=today_notifications,
                         yesterday_notifications=yesterday_notifications,
                         day_before_notifications=day_before_notifications)


@tasks_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    try:
        unread_notifications = TaskNotification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).all()
        
        for notification in unread_notifications:
            notification.mark_as_read()
        
        return jsonify({'success': True, 'marked_count': len(unread_notifications)})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@tasks_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read"""
    notification = TaskNotification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permesso negato'}), 403
    
    notification.mark_as_read()
    return jsonify({'success': True})


@tasks_bp.route('/api/tickets/<int:ticket_id>/lines')
@login_required
def api_get_ticket_lines(ticket_id):
    """API endpoint to get ticket lines for AJAX"""
    ticket = TicketHeader.query.get_or_404(ticket_id)
    lines = []
    
    for line in ticket.lines:
        lines.append({
            'id': line.IdLineaTicket,
            'product_id': line.IdArticulo,
            'description': line.Descripcion,
            'weight': float(line.Peso) if line.Peso else 0,
            'expiry_date': line.FechaCaducidad.isoformat() if line.FechaCaducidad else None
        })
    
    return jsonify(lines)


@tasks_bp.route('/api/tasks/<int:task_id>/progress')
@login_required
def api_get_task_progress(task_id):
    """Get task progress as JSON"""
    task = Task.query.get_or_404(task_id)
    
    # Check permissions
    if not current_user.is_admin and task.assigned_to != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    task.update_progress()
    
    return jsonify({
        'task_id': task.id_task,
        'total_tickets': task.total_tickets,
        'completed_tickets': task.completed_tickets,
        'progress_percentage': task.progress_percentage,
        'status': task.status,
        'is_completed': task.is_completed
    })


@tasks_bp.route('/api/available-tickets')
@login_required
def api_available_tickets():
    """Get list of available tickets (Enviado=0) as JSON"""
    try:
        tickets = TicketHeader.query.filter_by(Enviado=0).order_by(desc(TicketHeader.Fecha)).all()
        
        tickets_data = []
        for ticket in tickets:
            # Calculate formatted date
            formatted_date = ticket.Fecha.strftime('%d/%m/%Y %H:%M') if ticket.Fecha else 'N/A'
            
            # Get ticket lines for preview
            lines_count = TicketLine.query.filter_by(IdTicket=ticket.IdTicket).count()
            
            tickets_data.append({
                'IdTicket': ticket.IdTicket,
                'NumTicket': ticket.NumTicket,
                'Fecha': formatted_date,
                'NumLineas': lines_count,
                'CodigoBarras': ticket.CodigoBarras[:30] + '...' if ticket.CodigoBarras and len(ticket.CodigoBarras) > 30 else ticket.CodigoBarras,
                'Enviado': ticket.Enviado
            })
        
        return jsonify(tickets_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching available tickets: {str(e)}")
        return jsonify({'error': 'Unable to fetch tickets'}), 500


@tasks_bp.route('/task/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    """Delete a task and reset associated tickets to Enviado=0"""
    task = Task.query.get_or_404(task_id)
    
    try:
        # Get all task tickets before deletion
        task_tickets = TaskTicket.query.filter_by(task_id=task_id).all()
        
        # Reset all associated tickets to Enviado=0
        for task_ticket in task_tickets:
            ticket = TicketHeader.query.get(task_ticket.ticket_id)
            if ticket:
                ticket.Enviado = 0
        
        # Delete task notifications
        TaskNotification.query.filter_by(task_id=task_id).delete()
        
        # Delete task ticket scans
        for task_ticket in task_tickets:
            TaskTicketScan.query.filter_by(task_ticket_id=task_ticket.id).delete()
        
        # Delete task tickets
        TaskTicket.query.filter_by(task_id=task_id).delete()
        
        # Delete the task
        task_number = task.task_number
        db.session.delete(task)
        
        db.session.commit()
        
        flash(f'Task {task_number} eliminato con successo. I ticket sono stati rimessi a disposizione.', 'success')
        return redirect(url_for('tasks.admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting task {task_id}: {str(e)}")
        flash(f'Errore durante l\'eliminazione del task: {str(e)}', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/remove-ticket', methods=['POST'])
@admin_required
def remove_ticket_from_task():
    """Remove a ticket from a task"""
    task_id = request.form.get('task_id')
    task_ticket_id = request.form.get('task_ticket_id')
    
    if not task_id or not task_ticket_id:
        flash('Parametri mancanti per rimuovere il ticket.', 'error')
        return redirect(url_for('tasks.admin_dashboard'))
    
    try:
        task_ticket = TaskTicket.query.get_or_404(task_ticket_id)
        task = Task.query.get_or_404(task_id)
        
        # Get the ticket and reset its status
        ticket = TicketHeader.query.get(task_ticket.ticket_id)
        if ticket:
            ticket.Enviado = 0
        
        # Delete associated scans
        TaskTicketScan.query.filter_by(task_ticket_id=task_ticket_id).delete()
        
        # Remove the task ticket
        ticket_number = task_ticket.ticket.NumTicket
        db.session.delete(task_ticket)
        
        # Update task progress
        task.update_progress()
        
        db.session.commit()
        
        flash(f'Ticket #{ticket_number} rimosso dal task con successo.', 'success')
        return redirect(url_for('tasks.view_task', task_id=task_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing ticket from task: {str(e)}")
        flash(f'Errore durante la rimozione del ticket: {str(e)}', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))


@tasks_bp.route('/delete-all', methods=['POST'])
@admin_required
def delete_all_tasks():
    """Delete all tasks and reset associated tickets to Enviado=0"""
    try:
        # Get all tasks
        all_tasks = Task.query.all()
        total_tasks = len(all_tasks)
        
        if total_tasks == 0:
            flash('Nessun task da eliminare.', 'info')
            return redirect(url_for('tasks.admin_dashboard'))
        
        # Reset all associated tickets to Enviado=0
        for task in all_tasks:
            task_tickets = TaskTicket.query.filter_by(task_id=task.id_task).all()
            for task_ticket in task_tickets:
                ticket = TicketHeader.query.get(task_ticket.ticket_id)
                if ticket:
                    ticket.Enviado = 0
        
        # Delete all task notifications
        TaskNotification.query.delete()
        
        # Delete all task ticket scans
        TaskTicketScan.query.delete()
        
        # Delete all task tickets
        TaskTicket.query.delete()
        
        # Delete all tasks
        Task.query.delete()
        
        db.session.commit()
        
        flash(f'Eliminati {total_tasks} task con successo. Tutti i ticket sono stati rimessi a disposizione.', 'success')
        return redirect(url_for('tasks.admin_dashboard'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting all tasks: {str(e)}")
        flash(f'Errore durante l\'eliminazione di tutti i task: {str(e)}', 'error')
        return redirect(url_for('tasks.admin_dashboard')) 