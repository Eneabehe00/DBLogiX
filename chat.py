from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from models import db, ChatMessage, ChatRoom, User
from datetime import datetime, timedelta
import logging
from functools import wraps

logger = logging.getLogger(__name__)

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
    """Update user's last activity timestamp"""
    if current_user.is_authenticated:
        online_users[current_user.id] = {
            'user_id': current_user.id,
            'username': current_user.username,
            'last_activity': datetime.utcnow()
        }

def get_online_users_list():
    """Get list of users active in the last 5 minutes"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    active_users = []
    
    # Clean up old entries
    to_remove = []
    for user_id, user_data in online_users.items():
        if user_data['last_activity'] < cutoff_time:
            to_remove.append(user_id)
        else:
            active_users.append(user_data)
    
    for user_id in to_remove:
        del online_users[user_id]
    
    return active_users

@chat_bp.route('/api/messages', methods=['GET'])
@api_login_required
def get_messages():
    """Get chat messages with pagination"""
    try:
        update_user_activity()
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Get messages ordered by timestamp (newest first for pagination, but we'll reverse for display)
        messages = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Convert to dict and reverse order for proper display (oldest first)
        messages_data = [msg.to_dict() for msg in reversed(messages.items)]
        
        return jsonify({
            'success': True,
            'messages': messages_data,
            'has_more': messages.has_next,
            'total': messages.total
        })
    except Exception as e:
        logger.error(f"Error getting messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        logger.info(f"Saved message username: {saved_message.user.username}")
        logger.info(f"Saved message is_read: {saved_message.is_read}")
        
        # Return the message data
        return jsonify({
            'success': True,
            'message': message.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/messages/latest', methods=['GET'])
@api_login_required
def get_latest_messages():
    """Get messages newer than a specific timestamp"""
    try:
        update_user_activity()
        
        since = request.args.get('since')
        if since:
            since_datetime = datetime.fromisoformat(since.replace('Z', '+00:00'))
            messages = ChatMessage.query.filter(
                ChatMessage.timestamp > since_datetime
            ).order_by(ChatMessage.timestamp.asc()).all()
        else:
            # Get last 20 messages if no timestamp provided
            messages = ChatMessage.query.order_by(
                ChatMessage.timestamp.desc()
            ).limit(20).all()
            messages = list(reversed(messages))
        
        messages_data = [msg.to_dict() for msg in messages]
        
        return jsonify({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        logger.error(f"Error getting latest messages: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/users/online', methods=['GET'])
@api_login_required
def get_online_users():
    """Get list of online users"""
    try:
        update_user_activity()
        
        active_users = get_online_users_list()
        
        # Add current user status for each user
        users_data = []
        for user_data in active_users:
            users_data.append({
                'id': user_data['user_id'],
                'username': user_data['username'],
                'is_current': user_data['user_id'] == current_user.id,
                'last_activity': user_data['last_activity'].isoformat()
            })
        
        return jsonify({
            'success': True,
            'users': users_data,
            'total_online': len(users_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting online users: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/unread-count', methods=['GET'])
@api_login_required
def get_unread_count():
    """Get count of unread messages for current user"""
    try:
        update_user_activity()
        
        # Count only messages from OTHER users that are not read
        count = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        logger.info(f"Unread count for user {current_user.id}: {count}")
        
        return jsonify({
            'success': True,
            'unread_count': count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/messages/mark-read', methods=['POST'])
@api_login_required
def mark_messages_read():
    """Mark all unread messages as read for current user"""
    try:
        update_user_activity()
        
        # Mark only messages from OTHER users as read
        unread_messages = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).all()
        
        logger.info(f"Marking {len(unread_messages)} messages as read for user {current_user.id}")
        
        for message in unread_messages:
            message.is_read = True
            logger.info(f"Marked message {message.id} from user {message.user_id} as read")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'marked_count': len(unread_messages)
        })
        
    except Exception as e:
        logger.error(f"Error marking messages as read: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/messages/<int:message_id>/read', methods=['POST'])
@api_login_required
def mark_message_read(message_id):
    """Mark a specific message as read (only if it's not from current user)"""
    try:
        update_user_activity()
        
        message = ChatMessage.query.get_or_404(message_id)
        
        # Only mark as read if the message is NOT from the current user
        if message.user_id != current_user.id:
            message.is_read = True
            db.session.commit()
            logger.info(f"Message {message_id} marked as read by user {current_user.id}")
        else:
            logger.info(f"User {current_user.id} tried to mark their own message {message_id} as read - ignored")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/debug/current-user', methods=['GET'])
@api_login_required
def debug_current_user():
    """Debug endpoint to check current user"""
    from flask import session
    
    return jsonify({
        'success': True,
        'debug_info': {
            'current_user_id': current_user.id,
            'current_user_username': current_user.username,
            'current_user_authenticated': current_user.is_authenticated,
            'session_user_id': session.get('_user_id'),
            'session_fresh': session.get('_fresh'),
            'session_keys': list(session.keys())
        }
    }) 