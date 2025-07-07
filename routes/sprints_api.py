"""
Sprint Management API Routes
Handles all sprint-related API endpoints
"""

from flask import Blueprint, jsonify, request, g
from datetime import datetime
from models import db, Role, Project, Sprint, SprintStatus, Task
from routes.auth import login_required, role_required, company_required
import logging

logger = logging.getLogger(__name__)

sprints_api_bp = Blueprint('sprints_api', __name__, url_prefix='/api')


@sprints_api_bp.route('/sprints')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_sprints():
    """Get all sprints for the user's company"""
    try:
        # Base query for sprints in user's company
        query = Sprint.query.filter(Sprint.company_id == g.user.company_id)
        
        # Apply access restrictions based on user role and team
        if g.user.role not in [Role.ADMIN, Role.SUPERVISOR]:
            # Regular users can only see sprints they have access to
            accessible_sprint_ids = []
            sprints = query.all()
            for sprint in sprints:
                if sprint.can_user_access(g.user):
                    accessible_sprint_ids.append(sprint.id)
            
            if accessible_sprint_ids:
                query = query.filter(Sprint.id.in_(accessible_sprint_ids))
            else:
                # No accessible sprints, return empty list
                return jsonify({'success': True, 'sprints': []})
        
        sprints = query.order_by(Sprint.created_at.desc()).all()
        
        sprint_list = []
        for sprint in sprints:
            task_summary = sprint.get_task_summary()
            
            sprint_data = {
                'id': sprint.id,
                'name': sprint.name,
                'description': sprint.description,
                'status': sprint.status.name,
                'company_id': sprint.company_id,
                'project_id': sprint.project_id,
                'project_name': sprint.project.name if sprint.project else None,
                'project_code': sprint.project.code if sprint.project else None,
                'start_date': sprint.start_date.isoformat(),
                'end_date': sprint.end_date.isoformat(),
                'goal': sprint.goal,
                'capacity_hours': sprint.capacity_hours,
                'created_by_id': sprint.created_by_id,
                'created_by_name': sprint.created_by.username if sprint.created_by else None,
                'created_at': sprint.created_at.isoformat(),
                'is_current': sprint.is_current,
                'duration_days': sprint.duration_days,
                'days_remaining': sprint.days_remaining,
                'progress_percentage': sprint.progress_percentage,
                'task_summary': task_summary
            }
            sprint_list.append(sprint_data)
        
        return jsonify({'success': True, 'sprints': sprint_list})
        
    except Exception as e:
        logger.error(f"Error in get_sprints: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@sprints_api_bp.route('/sprints', methods=['POST'])
@role_required(Role.TEAM_LEADER)  # Team leaders and above can create sprints
@company_required
def create_sprint():
    """Create a new sprint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        name = data.get('name')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not name:
            return jsonify({'success': False, 'message': 'Sprint name is required'})
        if not start_date:
            return jsonify({'success': False, 'message': 'Start date is required'})
        if not end_date:
            return jsonify({'success': False, 'message': 'End date is required'})
        
        # Parse dates
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format'})
        
        if start_date >= end_date:
            return jsonify({'success': False, 'message': 'End date must be after start date'})
        
        # Verify project access if project is specified
        project_id = data.get('project_id')
        if project_id:
            project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first()
            if not project or not project.is_user_allowed(g.user):
                return jsonify({'success': False, 'message': 'Project not found or access denied'})
        
        # Create sprint
        sprint = Sprint(
            name=name,
            description=data.get('description', ''),
            status=SprintStatus[data.get('status', 'PLANNING')],
            company_id=g.user.company_id,
            project_id=int(project_id) if project_id else None,
            start_date=start_date,
            end_date=end_date,
            goal=data.get('goal'),
            capacity_hours=int(data.get('capacity_hours')) if data.get('capacity_hours') else None,
            created_by_id=g.user.id
        )
        
        db.session.add(sprint)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sprint created successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sprint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@sprints_api_bp.route('/sprints/<int:sprint_id>', methods=['PUT'])
@role_required(Role.TEAM_LEADER)
@company_required
def update_sprint(sprint_id):
    """Update an existing sprint"""
    try:
        sprint = Sprint.query.filter_by(id=sprint_id, company_id=g.user.company_id).first()
        
        if not sprint or not sprint.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Sprint not found or access denied'})
        
        data = request.get_json()
        
        # Update sprint fields
        if 'name' in data:
            sprint.name = data['name']
        if 'description' in data:
            sprint.description = data['description']
        if 'status' in data:
            sprint.status = SprintStatus[data['status']]
        if 'goal' in data:
            sprint.goal = data['goal']
        if 'capacity_hours' in data:
            sprint.capacity_hours = int(data['capacity_hours']) if data['capacity_hours'] else None
        if 'project_id' in data:
            project_id = data['project_id']
            if project_id:
                project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first()
                if not project or not project.is_user_allowed(g.user):
                    return jsonify({'success': False, 'message': 'Project not found or access denied'})
                sprint.project_id = int(project_id)
            else:
                sprint.project_id = None
        
        # Update dates if provided
        if 'start_date' in data:
            try:
                sprint.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid start date format'})
        
        if 'end_date' in data:
            try:
                sprint.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid end date format'})
        
        # Validate date order
        if sprint.start_date >= sprint.end_date:
            return jsonify({'success': False, 'message': 'End date must be after start date'})
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sprint updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating sprint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@sprints_api_bp.route('/sprints/<int:sprint_id>', methods=['DELETE'])
@role_required(Role.TEAM_LEADER)
@company_required
def delete_sprint(sprint_id):
    """Delete a sprint and remove it from all associated tasks"""
    try:
        sprint = Sprint.query.filter_by(id=sprint_id, company_id=g.user.company_id).first()
        
        if not sprint or not sprint.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Sprint not found or access denied'})
        
        # Remove sprint assignment from all tasks
        Task.query.filter_by(sprint_id=sprint_id).update({'sprint_id': None})
        
        # Delete the sprint
        db.session.delete(sprint)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Sprint deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting sprint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})