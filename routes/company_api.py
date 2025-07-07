"""
Company API endpoints
"""

from flask import Blueprint, jsonify, g
from models import db, Company, User, Role, Team, Project, TimeEntry
from routes.auth import system_admin_required
from datetime import datetime, timedelta

company_api_bp = Blueprint('company_api', __name__, url_prefix='/api')


@company_api_bp.route('/system-admin/companies/<int:company_id>/users')
@system_admin_required
def api_company_users(company_id):
    """API: Get users for a specific company (System Admin only)"""
    company = Company.query.get_or_404(company_id)
    users = User.query.filter_by(company_id=company.id).order_by(User.username).all()

    return jsonify({
        'company': {
            'id': company.id,
            'name': company.name,
            'is_personal': company.is_personal
        },
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'is_blocked': user.is_blocked,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat(),
            'team_id': user.team_id
        } for user in users]
    })


@company_api_bp.route('/system-admin/companies/<int:company_id>/stats')
@system_admin_required
def api_company_stats(company_id):
    """API: Get detailed statistics for a specific company"""
    company = Company.query.get_or_404(company_id)

    # User counts by role
    role_counts = {}
    for role in Role:
        count = User.query.filter_by(company_id=company.id, role=role).count()
        if count > 0:
            role_counts[role.value] = count

    # Team and project counts
    team_count = Team.query.filter_by(company_id=company.id).count()
    project_count = Project.query.filter_by(company_id=company.id).count()
    active_projects = Project.query.filter_by(company_id=company.id, is_active=True).count()

    # Time entries statistics
    week_ago = datetime.now() - timedelta(days=7)
    month_ago = datetime.now() - timedelta(days=30)

    weekly_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= week_ago
    ).count()

    monthly_entries = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.arrival_time >= month_ago
    ).count()

    # Active sessions
    active_sessions = TimeEntry.query.join(User).filter(
        User.company_id == company.id,
        TimeEntry.departure_time == None,
        TimeEntry.is_paused == False
    ).count()

    return jsonify({
        'company': {
            'id': company.id,
            'name': company.name,
            'is_personal': company.is_personal,
            'is_active': company.is_active
        },
        'users': {
            'total': User.query.filter_by(company_id=company.id).count(),
            'verified': User.query.filter_by(company_id=company.id, is_verified=True).count(),
            'blocked': User.query.filter_by(company_id=company.id, is_blocked=True).count(),
            'roles': role_counts
        },
        'teams': team_count,
        'projects': {
            'total': project_count,
            'active': active_projects,
            'inactive': project_count - active_projects
        },
        'time_entries': {
            'weekly': weekly_entries,
            'monthly': monthly_entries,
            'active_sessions': active_sessions
        }
    })