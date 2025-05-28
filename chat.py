from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from models import db, ChatMessage, ChatRoom, User
from datetime import datetime
import logging
from functools import wraps

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__)

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

@chat_bp.route('/api/messages', methods=['GET'])
@api_login_required
def get_messages():
    """Get chat messages with pagination"""
    try:
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
        data = request.get_json()
        message_text = data.get('message', '').strip()
        
        if not message_text:
            return jsonify({'success': False, 'error': 'Il messaggio non può essere vuoto'}), 400
        
        if len(message_text) > 1000:
            return jsonify({'success': False, 'error': 'Il messaggio è troppo lungo (max 1000 caratteri)'}), 400
        
        # Create new message
        message = ChatMessage(
            user_id=current_user.id,
            message=message_text,
            timestamp=datetime.utcnow()
        )
        
        db.session.add(message)
        db.session.commit()
        
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
    """Get list of online users (simplified - just return all users for now)"""
    try:
        users = User.query.all()
        users_data = [
            {
                'id': user.id,
                'username': user.username,
                'is_current': user.id == current_user.id
            }
            for user in users
        ]
        
        return jsonify({
            'success': True,
            'users': users_data
        })
        
    except Exception as e:
        logger.error(f"Error getting online users: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/messages/<int:message_id>/read', methods=['POST'])
@api_login_required
def mark_message_read(message_id):
    """Mark a message as read"""
    try:
        message = ChatMessage.query.get_or_404(message_id)
        message.is_read = True
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error marking message as read: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@chat_bp.route('/api/unread-count', methods=['GET'])
@api_login_required
def get_unread_count():
    """Get count of unread messages for current user"""
    try:
        # For global chat, we'll consider messages from other users that are newer than user's last seen
        # For simplicity, let's just count recent messages from others
        count = ChatMessage.query.filter(
            ChatMessage.user_id != current_user.id,
            ChatMessage.is_read == False
        ).count()
        
        return jsonify({
            'success': True,
            'unread_count': count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500 