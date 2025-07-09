from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, g
from models import db, User, Team, Role, Company
from routes.auth import login_required, admin_required, company_required
from sqlalchemy import or_

# Create the blueprint
organization_bp = Blueprint('organization', __name__)

@organization_bp.route('/admin/organization')
@login_required
@company_required
@admin_required
def admin_organization():
    """Comprehensive organization management interface"""
    company = g.user.company
    
    # Get all teams and users for the company
    teams = Team.query.filter_by(company_id=company.id).order_by(Team.name).all()
    users = User.query.filter_by(company_id=company.id).order_by(User.username).all()
    
    return render_template('admin_organization.html',
                         title='Organization Management',
                         teams=teams,
                         users=users,
                         Role=Role)

@organization_bp.route('/api/organization/teams/<int:team_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@company_required
@admin_required
def api_team(team_id):
    """API endpoint for team operations"""
    team = Team.query.filter_by(id=team_id, company_id=g.user.company_id).first_or_404()
    
    if request.method == 'GET':
        return jsonify({
            'id': team.id,
            'name': team.name,
            'description': team.description,
            'members': [{'id': u.id, 'username': u.username} for u in team.users]
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        team.name = data.get('name', team.name)
        team.description = data.get('description', team.description)
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'Team updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    elif request.method == 'DELETE':
        # Unassign all users from the team
        for user in team.users:
            user.team_id = None
        
        db.session.delete(team)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Team deleted successfully'})

@organization_bp.route('/api/organization/teams', methods=['POST'])
@login_required
@company_required
@admin_required
def api_create_team():
    """API endpoint to create a new team"""
    data = request.get_json()
    
    team = Team(
        name=data.get('name'),
        description=data.get('description'),
        company_id=g.user.company_id
    )
    
    try:
        db.session.add(team)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Team created successfully', 'team_id': team.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@organization_bp.route('/api/organization/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@company_required
@admin_required
def api_user(user_id):
    """API endpoint for user operations"""
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()
    
    if request.method == 'GET':
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.name if user.role else 'TEAM_MEMBER',
            'team_id': user.team_id,
            'is_blocked': user.is_blocked
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        
        # Update user fields
        if 'email' in data:
            user.email = data['email']
        if 'role' in data:
            user.role = Role[data['role']]
        if 'team_id' in data:
            user.team_id = data['team_id'] if data['team_id'] else None
        if 'is_blocked' in data:
            user.is_blocked = data['is_blocked']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        try:
            db.session.commit()
            return jsonify({'success': True, 'message': 'User updated successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
    
    elif request.method == 'DELETE':
        if user.id == g.user.id:
            return jsonify({'success': False, 'message': 'Cannot delete your own account'}), 400
        
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})

@organization_bp.route('/api/organization/users', methods=['POST'])
@login_required
@company_required
@admin_required
def api_create_user():
    """API endpoint to create a new user"""
    data = request.get_json()
    
    # Check if username already exists
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 400
    
    user = User(
        username=data.get('username'),
        email=data.get('email'),
        company_id=g.user.company_id,
        role=Role[data.get('role', 'TEAM_MEMBER')],
        team_id=data.get('team_id') if data.get('team_id') else None
    )
    user.set_password(data.get('password'))
    
    try:
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User created successfully', 'user_id': user.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@organization_bp.route('/api/organization/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@company_required
@admin_required
def api_toggle_user_status(user_id):
    """Toggle user active/blocked status"""
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()
    
    if user.id == g.user.id:
        return jsonify({'success': False, 'message': 'Cannot block your own account'}), 400
    
    user.is_blocked = not user.is_blocked
    db.session.commit()
    
    status = 'blocked' if user.is_blocked else 'unblocked'
    return jsonify({'success': True, 'message': f'User {status} successfully'})

@organization_bp.route('/api/organization/users/<int:user_id>/assign-team', methods=['POST'])
@login_required
@company_required
@admin_required
def api_assign_team(user_id):
    """Assign user to a team"""
    user = User.query.filter_by(id=user_id, company_id=g.user.company_id).first_or_404()
    data = request.get_json()
    
    team_id = data.get('team_id')
    if team_id:
        team = Team.query.filter_by(id=team_id, company_id=g.user.company_id).first_or_404()
        user.team_id = team.id
    else:
        user.team_id = None
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Team assignment updated'})

@organization_bp.route('/api/organization/search', methods=['GET'])
@login_required
@company_required
@admin_required
def api_organization_search():
    """Search users and teams"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({'users': [], 'teams': []})
    
    # Search users
    users = User.query.filter(
        User.company_id == g.user.company_id,
        or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    # Search teams
    teams = Team.query.filter(
        Team.company_id == g.user.company_id,
        or_(
            Team.name.ilike(f'%{query}%'),
            Team.description.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify({
        'users': [{'id': u.id, 'username': u.username, 'email': u.email} for u in users],
        'teams': [{'id': t.id, 'name': t.name, 'description': t.description} for t in teams]
    })