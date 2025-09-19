"""
DBLogiX - Modulo Chat
Sistema di messaggistica e comunicazione tra utenti
"""

from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app.models import db, ChatMessage, ChatRoom, User
from datetime import datetime, timedelta
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Blueprint per il modulo chat
chat_bp = Blueprint('chat', __name__)

# Store for tracking online users (in production, use Redis or similar)
online_users = {}

def api_login_required(f):
    """
    Decorator personalizzato per API che devono restituire JSON 
    invece di redirect HTML per utenti non autenticati
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False, 
                'error': 'Authentication required',
                'redirect': '/auth/login'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def update_user_activity():
    """Update user's last activity timestamp for online status"""
    if current_user.is_authenticated:
        online_users[current_user.id] = {
            'username': current_user.username,
            'last_activity': datetime.utcnow(),
            'is_admin': current_user.is_admin
        }

def get_online_users():
    """Get list of currently online users"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)  # 5 minutes timeout
    active_users = []
    
    # Remove inactive users
    to_remove = []
    for user_id, user_data in online_users.items():
        if user_data['last_activity'] < cutoff_time:
            to_remove.append(user_id)
        else:
            user_data['is_current'] = (user_id == current_user.id) if current_user.is_authenticated else False
            active_users.append(user_data)
    
    for user_id in to_remove:
        del online_users[user_id]
    
    return active_users

# ===== CHAT ROUTES =====

@chat_bp.route('/api/messages/latest')
@api_login_required
def get_latest_messages():
    """Get latest chat messages"""
    try:
        update_user_activity()
        
        # Get messages from the last 24 hours or last 50 messages, whichever is more recent
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        messages = ChatMessage.query.filter(
            ChatMessage.timestamp >= cutoff_time
        ).order_by(ChatMessage.timestamp.asc()).limit(50).all()
        
        # If less than 10 messages in last 24h, get the last 10 regardless of time
        if len(messages) < 10:
            messages = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(10).all()
            messages.reverse()  # Restore chronological order
        
        # Mark messages as read for current user (if they are recipients)
        unread_messages = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).all()
        
        for message in unread_messages:
            message.is_read = True
        
        if unread_messages:
            db.session.commit()
        
        # Format messages for JSON response
        formatted_messages = []
        for message in messages:
            user = User.query.get(message.user_id)
            formatted_messages.append({
                'id': message.id,
                'user_id': message.user_id,
                'username': user.username if user else 'Utente Sconosciuto',
                'message': message.message,
                'timestamp': message.timestamp.isoformat(),
                'formatted_time': message.timestamp.strftime('%H:%M'),
                'is_read': message.is_read
            })
        
        return jsonify({
            'success': True,
            'messages': formatted_messages
        })
        
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nel caricamento dei messaggi'}), 500

@chat_bp.route('/api/messages', methods=['POST'])
@api_login_required
def send_message():
    """Send a new chat message"""
    try:
        update_user_activity()
        
        from flask import session
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        # Debug logging dettagliato
        logger.info(f"=== SEND MESSAGE DEBUG ===")
        logger.info(f"Current user authenticated: {current_user.is_authenticated}")
        logger.info(f"Current user ID: {current_user.id}")
        logger.info(f"Current user username: {current_user.username}")
        logger.info(f"Flask session keys: {list(session.keys())}")
        logger.info(f"Flask session _user_id: {session.get('_user_id')}")
        logger.info(f"Flask session _fresh: {session.get('_fresh')}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Message text: {message_text}")
        
        if not message_text:
            return jsonify({'success': False, 'error': 'Il messaggio non può essere vuoto'}), 400
        
        if len(message_text) > 1000:
            return jsonify({'success': False, 'error': 'Il messaggio è troppo lungo (max 1000 caratteri)'}), 400
        
        # Create new message - NOT marked as read by default
        # Only recipients should mark messages as read
        message = ChatMessage(
            user_id=current_user.id,
            message=message_text,
            timestamp=datetime.utcnow(),
            is_read=False  # Changed: messages start as unread for notifications
        )
        
        logger.info(f"Created message object with user_id: {message.user_id}")
        
        db.session.add(message)
        db.session.commit()
        
        # Verifico che il messaggio sia stato salvato correttamente
        saved_message = ChatMessage.query.get(message.id)
        logger.info(f"Saved message user_id: {saved_message.user_id}")
        
        # Format message for response
        formatted_message = {
            'id': message.id,
            'user_id': message.user_id,
            'username': current_user.username,
            'message': message.message,
            'timestamp': message.timestamp.isoformat(),
            'formatted_time': message.timestamp.strftime('%H:%M'),
            'is_read': message.is_read
        }
        
        logger.info(f"Chat message sent by user {current_user.username}: {message_text[:50]}...")
        
        return jsonify({
            'success': True,
            'message': formatted_message
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nell\'invio del messaggio'}), 500

@chat_bp.route('/api/messages/poll')
@api_login_required
def poll_messages():
    """Poll for new messages since last timestamp"""
    try:
        update_user_activity()
        
        last_timestamp = request.args.get('since')
        if not last_timestamp:
            return jsonify({'success': False, 'error': 'Timestamp richiesto'}), 400
        
        try:
            since_time = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'success': False, 'error': 'Formato timestamp non valido'}), 400
        
        # Get new messages since the timestamp
        new_messages = ChatMessage.query.filter(
            ChatMessage.timestamp > since_time
        ).order_by(ChatMessage.timestamp.asc()).all()
        
        # Mark unread messages as read for current user (if they are recipients)
        unread_messages = [msg for msg in new_messages if msg.user_id != current_user.id and not msg.is_read]
        for message in unread_messages:
            message.is_read = True
        
        if unread_messages:
            db.session.commit()
        
        # Format messages for JSON response
        formatted_messages = []
        for message in new_messages:
            user = User.query.get(message.user_id)
            formatted_messages.append({
                'id': message.id,
                'user_id': message.user_id,
                'username': user.username if user else 'Utente Sconosciuto',
                'message': message.message,
                'timestamp': message.timestamp.isoformat(),
                'formatted_time': message.timestamp.strftime('%H:%M'),
                'is_read': message.is_read
            })
        
        return jsonify({
            'success': True,
            'messages': formatted_messages,
            'unread_count': len([msg for msg in new_messages if msg.user_id != current_user.id])
        })
        
    except Exception as e:
        logger.error(f"Error polling messages: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nel polling dei messaggi'}), 500

@chat_bp.route('/api/online-users')
@api_login_required
def get_online_users_api():
    """Get list of online users"""
    try:
        update_user_activity()
        online_users_list = get_online_users()
        
        # Sort users: current user first, then by username
        online_users_list.sort(key=lambda u: (not u.get('is_current', False), u['username']))
        
        return jsonify({
            'success': True,
            'users': online_users_list,
            'total_online': len(online_users_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting online users: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nel caricamento utenti online'}), 500

@chat_bp.route('/api/unread-count')
@api_login_required 
def get_unread_count():
    """Get count of unread messages for current user"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Non autenticato'}), 401
        
        # Count unread messages (messages not sent by current user and not read)
        unread_count = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': unread_count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nel conteggio messaggi non letti'}), 500

@chat_bp.route('/api/mark-read', methods=['POST'])
@api_login_required
def mark_messages_read():
    """Mark all messages as read for current user"""
    try:
        # Mark all unread messages (not sent by current user) as read
        unread_messages = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).all()
        
        for message in unread_messages:
            message.is_read = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'marked_count': len(unread_messages)
        })
        
    except Exception as e:
        logger.error(f"Error marking messages as read: {str(e)}")
        return jsonify({'success': False, 'error': 'Errore nell\'aggiornamento stato lettura'}), 500

# ===== HELPER FUNCTIONS =====

def create_chat_backup():
    """Create a backup of all chat messages"""
    import json
    import os
    from datetime import datetime
    
    try:
        # Get all messages
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.asc()).all()
        
        # Format messages for backup
        backup_data = {
            'backup_date': datetime.utcnow().isoformat(),
            'total_messages': len(messages),
            'messages': []
        }
        
        for message in messages:
            user = User.query.get(message.user_id)
            backup_data['messages'].append({
                'id': message.id,
                'user_id': message.user_id,
                'username': user.username if user else 'Utente Sconosciuto',
                'message': message.message,
                'timestamp': message.timestamp.isoformat(),
                'is_read': message.is_read
            })
        
        # Create backup directory
        backup_dir = 'Backup/Chat'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'chat_backup_{timestamp}.json'
        filepath = os.path.join(backup_dir, filename)
        
        # Save backup file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Chat backup created: {filepath}")
        
        return {
            'success': True,
            'filename': filename,
            'path': filepath,
            'message_count': len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error creating chat backup: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 