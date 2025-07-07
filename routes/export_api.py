"""
Export API routes for TimeTrack application.
Handles API endpoints for data export functionality.
"""

from flask import Blueprint, request, redirect, url_for, flash, g
from datetime import datetime
from models import Role
from routes.auth import login_required, role_required, company_required
from data_export import export_analytics_csv, export_analytics_excel
import logging

logger = logging.getLogger(__name__)

# Create blueprint
export_api_bp = Blueprint('export_api', __name__, url_prefix='/api')


def get_filtered_analytics_data(user, mode, start_date=None, end_date=None, project_filter=None):
    """Get filtered time entry data for analytics"""
    from models import TimeEntry, User
    from sqlalchemy import func
    
    # Base query
    query = TimeEntry.query

    # Apply user/team filter
    if mode == 'personal':
        query = query.filter(TimeEntry.user_id == user.id)
    elif mode == 'team' and user.team_id:
        team_user_ids = [u.id for u in User.query.filter_by(team_id=user.team_id).all()]
        query = query.filter(TimeEntry.user_id.in_(team_user_ids))

    # Apply date filters
    if start_date:
        query = query.filter(func.date(TimeEntry.arrival_time) >= start_date)
    if end_date:
        query = query.filter(func.date(TimeEntry.arrival_time) <= end_date)

    # Apply project filter
    if project_filter:
        if project_filter == 'none':
            query = query.filter(TimeEntry.project_id.is_(None))
        else:
            try:
                project_id = int(project_filter)
                query = query.filter(TimeEntry.project_id == project_id)
            except ValueError:
                pass

    return query.order_by(TimeEntry.arrival_time.desc()).all()


@export_api_bp.route('/analytics/export')
@login_required
@company_required
def analytics_export():
    """Export analytics data in various formats"""
    export_format = request.args.get('format', 'csv')
    view_type = request.args.get('view', 'table')
    mode = request.args.get('mode', 'personal')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    project_filter = request.args.get('project_id')

    # Validate permissions
    if mode == 'team':
        if not g.user.team_id:
            flash('No team assigned', 'error')
            return redirect(url_for('analytics'))
        if g.user.role not in [Role.TEAM_LEADER, Role.SUPERVISOR, Role.ADMIN]:
            flash('Insufficient permissions', 'error')
            return redirect(url_for('analytics'))

    try:
        # Parse dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Get data
        data = get_filtered_analytics_data(g.user, mode, start_date, end_date, project_filter)

        if export_format == 'csv':
            return export_analytics_csv(data, view_type, mode)
        elif export_format == 'excel':
            return export_analytics_excel(data, view_type, mode)
        else:
            flash('Invalid export format', 'error')
            return redirect(url_for('analytics'))

    except Exception as e:
        logger.error(f"Error in analytics export: {str(e)}")
        flash('Error generating export', 'error')
        return redirect(url_for('analytics'))