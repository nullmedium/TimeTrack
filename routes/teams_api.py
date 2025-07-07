"""
Team Management API Routes
Handles all team-related API endpoints
"""

from flask import Blueprint, jsonify, request, g
from datetime import datetime, time, timedelta
from models import Team, User, TimeEntry, Role
from routes.auth import login_required, role_required, company_required, system_admin_required

teams_api_bp = Blueprint('teams_api', __name__, url_prefix='/api')


@teams_api_bp.route('/team/hours_data', methods=['GET'])
@login_required
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can access
@company_required
def team_hours_data():
    # Get the current user's team
    team = Team.query.get(g.user.team_id)

    if not team:
        return jsonify({
            'success': False,
            'message': 'You are not assigned to any team.'
        }), 400

    # Get date range from query parameters or use current week as default
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    start_date_str = request.args.get('start_date', start_of_week.strftime('%Y-%m-%d'))
    end_date_str = request.args.get('end_date', end_of_week.strftime('%Y-%m-%d'))
    include_self = request.args.get('include_self', 'false') == 'true'

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid date format.'
        }), 400

    # Get all team members
    team_members = User.query.filter_by(team_id=team.id).all()

    # Prepare data structure for team members' hours
    team_data = []

    for member in team_members:
        # Skip if the member is the current user (team leader) and include_self is False
        if member.id == g.user.id and not include_self:
            continue

        # Get time entries for this member in the date range
        entries = TimeEntry.query.filter(
            TimeEntry.user_id == member.id,
            TimeEntry.arrival_time >= datetime.combine(start_date, time.min),
            TimeEntry.arrival_time <= datetime.combine(end_date, time.max)
        ).order_by(TimeEntry.arrival_time).all()

        # Calculate daily and total hours
        daily_hours = {}
        total_seconds = 0

        for entry in entries:
            if entry.duration:  # Only count completed entries
                entry_date = entry.arrival_time.date()
                date_str = entry_date.strftime('%Y-%m-%d')

                if date_str not in daily_hours:
                    daily_hours[date_str] = 0

                daily_hours[date_str] += entry.duration
                total_seconds += entry.duration

        # Convert seconds to hours for display
        for date_str in daily_hours:
            daily_hours[date_str] = round(daily_hours[date_str] / 3600, 2)  # Convert to hours

        total_hours = round(total_seconds / 3600, 2)  # Convert to hours

        # Format entries for JSON response
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                'id': entry.id,
                'arrival_time': entry.arrival_time.isoformat(),
                'departure_time': entry.departure_time.isoformat() if entry.departure_time else None,
                'duration': entry.duration,
                'total_break_duration': entry.total_break_duration
            })

        # Add member data to team data
        team_data.append({
            'member_id': member.id,
            'member_name': member.username,
            'daily_hours': daily_hours,
            'total_hours': total_hours,
            'entries': formatted_entries
        })

    return jsonify({
        'success': True,
        'team_name': team.name,
        'team_id': team.id,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'team_data': team_data
    })


@teams_api_bp.route('/companies/<int:company_id>/teams')
@system_admin_required
def api_company_teams(company_id):
    """API: Get teams for a specific company (System Admin only)"""
    teams = Team.query.filter_by(company_id=company_id).order_by(Team.name).all()
    return jsonify([{
        'id': team.id,
        'name': team.name,
        'description': team.description
    } for team in teams])