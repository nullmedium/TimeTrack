"""
User API endpoints
"""

from flask import Blueprint, jsonify, request, g
from models import db, User, Role
from routes.auth import system_admin_required, role_required
from sqlalchemy import or_

users_api_bp = Blueprint('users_api', __name__, url_prefix='/api')


@users_api_bp.route('/system-admin/users/<int:user_id>/toggle-block', methods=['POST'])
@system_admin_required
def api_toggle_user_block(user_id):
    """API: Toggle user blocked status (System Admin only)"""
    user = User.query.get_or_404(user_id)

    # Safety check: prevent blocking yourself
    if user.id == g.user.id:
        return jsonify({'error': 'Cannot block your own account'}), 400

    # Safety check: prevent blocking the last system admin
    if user.role == Role.SYSTEM_ADMIN and not user.is_blocked:
        system_admin_count = User.query.filter_by(role=Role.SYSTEM_ADMIN, is_blocked=False).count()
        if system_admin_count <= 1:
            return jsonify({'error': 'Cannot block the last system administrator'}), 400

    user.is_blocked = not user.is_blocked
    db.session.commit()

    return jsonify({
        'id': user.id,
        'username': user.username,
        'is_blocked': user.is_blocked,
        'message': f'User {"blocked" if user.is_blocked else "unblocked"} successfully'
    })


@users_api_bp.route('/search/users')
@role_required(Role.TEAM_MEMBER)
def search_users():
    """Search for users within the company"""
    query = request.args.get('q', '').strip()
    exclude_id = request.args.get('exclude', type=int)
    
    if not query or len(query) < 2:
        return jsonify({'users': []})
    
    # Search users in the same company
    users_query = User.query.filter(
        User.company_id == g.user.company_id,
        or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        ),
        User.is_blocked == False,
        User.is_verified == True
    )
    
    if exclude_id:
        users_query = users_query.filter(User.id != exclude_id)
    
    users = users_query.limit(10).all()
    
    return jsonify({
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar_url': user.get_avatar_url(32),
            'role': user.role.value,
            'team': user.team.name if user.team else None
        } for user in users]
    })