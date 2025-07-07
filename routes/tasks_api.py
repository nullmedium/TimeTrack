"""
Task Management API Routes
Handles all task-related API endpoints including subtasks and dependencies
"""

from flask import Blueprint, jsonify, request, g
from datetime import datetime
from models import (db, Role, Project, Task, User, TaskStatus, TaskPriority, SubTask, 
                   TaskDependency, Sprint, CompanySettings, Comment, CommentVisibility)
from routes.auth import login_required, role_required, company_required
import logging

logger = logging.getLogger(__name__)

tasks_api_bp = Blueprint('tasks_api', __name__, url_prefix='/api')


@tasks_api_bp.route('/tasks', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def create_task():
    try:
        data = request.get_json()
        project_id = data.get('project_id')

        # Verify project access
        project = Project.query.filter_by(id=project_id, company_id=g.user.company_id).first()
        if not project or not project.is_user_allowed(g.user):
            return jsonify({'success': False, 'message': 'Project not found or access denied'})

        # Validate required fields
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Task name is required'})

        # Parse dates
        start_date = None
        due_date = None
        if data.get('start_date'):
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        if data.get('due_date'):
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()

        # Generate task number
        task_number = Task.generate_task_number(g.user.company_id)
        
        # Create task
        task = Task(
            task_number=task_number,
            name=name,
            description=data.get('description', ''),
            status=TaskStatus[data.get('status', 'TODO')],
            priority=TaskPriority[data.get('priority', 'MEDIUM')],
            estimated_hours=float(data.get('estimated_hours')) if data.get('estimated_hours') else None,
            project_id=project_id,
            assigned_to_id=int(data.get('assigned_to_id')) if data.get('assigned_to_id') else None,
            sprint_id=int(data.get('sprint_id')) if data.get('sprint_id') else None,
            start_date=start_date,
            due_date=due_date,
            created_by_id=g.user.id
        )

        db.session.add(task)
        db.session.commit()

        return jsonify({
            'success': True, 
            'message': 'Task created successfully',
            'task': {
                'id': task.id,
                'task_number': task.task_number
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@role_required(Role.TEAM_MEMBER)
@company_required
def get_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        task_data = {
            'id': task.id,
            'task_number': getattr(task, 'task_number', f'TSK-{task.id:03d}'),
            'name': task.name,
            'description': task.description,
            'status': task.status.name,
            'priority': task.priority.name,
            'estimated_hours': task.estimated_hours,
            'assigned_to_id': task.assigned_to_id,
            'assigned_to_name': task.assigned_to.username if task.assigned_to else None,
            'project_id': task.project_id,
            'project_name': task.project.name if task.project else None,
            'project_code': task.project.code if task.project else None,
            'start_date': task.start_date.isoformat() if task.start_date else None,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'completed_date': task.completed_date.isoformat() if task.completed_date else None,
            'archived_date': task.archived_date.isoformat() if task.archived_date else None,
            'sprint_id': task.sprint_id,
            'subtasks': [{
                'id': subtask.id,
                'name': subtask.name,
                'status': subtask.status.name,
                'priority': subtask.priority.name,
                'assigned_to_id': subtask.assigned_to_id,
                'assigned_to_name': subtask.assigned_to.username if subtask.assigned_to else None
            } for subtask in task.subtasks] if task.subtasks else []
        }

        return jsonify(task_data)

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        data = request.get_json()

        # Update task fields
        if 'name' in data:
            task.name = data['name']
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            task.status = TaskStatus[data['status']]
            if data['status'] == 'COMPLETED':
                task.completed_date = datetime.now().date()
            else:
                task.completed_date = None
        if 'priority' in data:
            task.priority = TaskPriority[data['priority']]
        if 'estimated_hours' in data:
            task.estimated_hours = float(data['estimated_hours']) if data['estimated_hours'] else None
        if 'assigned_to_id' in data:
            task.assigned_to_id = int(data['assigned_to_id']) if data['assigned_to_id'] else None
        if 'sprint_id' in data:
            task.sprint_id = int(data['sprint_id']) if data['sprint_id'] else None
        if 'start_date' in data:
            task.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'due_date' in data:
            task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None

        db.session.commit()

        return jsonify({'success': True, 'message': 'Task updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can delete tasks
@company_required
def delete_task(task_id):
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        db.session.delete(task)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Task deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/unified')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_unified_tasks():
    """Get all tasks for unified task view"""
    try:
        # Base query for tasks in user's company
        query = Task.query.join(Project).filter(Project.company_id == g.user.company_id)
        
        # Apply access restrictions based on user role and team
        if g.user.role not in [Role.ADMIN, Role.SUPERVISOR]:
            # Regular users can only see tasks from projects they have access to
            accessible_project_ids = []
            projects = Project.query.filter_by(company_id=g.user.company_id).all()
            for project in projects:
                if project.is_user_allowed(g.user):
                    accessible_project_ids.append(project.id)
            
            if accessible_project_ids:
                query = query.filter(Task.project_id.in_(accessible_project_ids))
            else:
                # No accessible projects, return empty list
                return jsonify({'success': True, 'tasks': []})
        
        tasks = query.order_by(Task.created_at.desc()).all()
        
        task_list = []
        for task in tasks:
            # Determine if this is a team task
            is_team_task = (
                g.user.team_id and 
                task.project and 
                task.project.team_id == g.user.team_id
            )
            
            task_data = {
                'id': task.id,
                'task_number': getattr(task, 'task_number', f'TSK-{task.id:03d}'),  # Fallback for existing tasks
                'name': task.name,
                'description': task.description,
                'status': task.status.name,
                'priority': task.priority.name,
                'estimated_hours': task.estimated_hours,
                'project_id': task.project_id,
                'project_name': task.project.name if task.project else None,
                'project_code': task.project.code if task.project else None,
                'assigned_to_id': task.assigned_to_id,
                'assigned_to_name': task.assigned_to.username if task.assigned_to else None,
                'created_by_id': task.created_by_id,
                'created_by_name': task.created_by.username if task.created_by else None,
                'start_date': task.start_date.isoformat() if task.start_date else None,
                'due_date': task.due_date.isoformat() if task.due_date else None,
                'completed_date': task.completed_date.isoformat() if task.completed_date else None,
                'created_at': task.created_at.isoformat(),
                'is_team_task': is_team_task,
                'subtask_count': len(task.subtasks) if task.subtasks else 0,
                'subtasks': [{
                    'id': subtask.id,
                    'name': subtask.name,
                    'status': subtask.status.name,
                    'priority': subtask.priority.name,
                    'assigned_to_id': subtask.assigned_to_id,
                    'assigned_to_name': subtask.assigned_to.username if subtask.assigned_to else None
                } for subtask in task.subtasks] if task.subtasks else [],
                'sprint_id': task.sprint_id,
                'sprint_name': task.sprint.name if task.sprint else None,
                'is_current_sprint': task.sprint.is_current if task.sprint else False
            }
            task_list.append(task_data)
        
        return jsonify({'success': True, 'tasks': task_list})
        
    except Exception as e:
        logger.error(f"Error in get_unified_tasks: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>/status', methods=['PUT'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_task_status(task_id):
    """Update task status"""
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'message': 'Status is required'})
        
        # Validate status value - convert from enum name to enum object
        try:
            task_status = TaskStatus[new_status]
        except KeyError:
            return jsonify({'success': False, 'message': 'Invalid status value'})
        
        # Update task status
        old_status = task.status
        task.status = task_status
        
        # Set completion date if status is DONE
        if task_status == TaskStatus.DONE:
            task.completed_date = datetime.now().date()
        elif old_status == TaskStatus.DONE:
            # Clear completion date if moving away from done
            task.completed_date = None
        
        # Set archived date if status is ARCHIVED
        if task_status == TaskStatus.ARCHIVED:
            task.archived_date = datetime.now().date()
        elif old_status == TaskStatus.ARCHIVED:
            # Clear archived date if moving away from archived
            task.archived_date = None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Task status updated successfully',
            'old_status': old_status.name,
            'new_status': task_status.name
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating task status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# Task Dependencies APIs
@tasks_api_bp.route('/tasks/<int:task_id>/dependencies')
@role_required(Role.TEAM_MEMBER)
@company_required
def get_task_dependencies(task_id):
    """Get dependencies for a specific task"""
    try:
        # Get the task and verify ownership through project
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Get blocked by dependencies (tasks that block this one)
        blocked_by_query = db.session.query(Task).join(
            TaskDependency, Task.id == TaskDependency.blocking_task_id
        ).filter(TaskDependency.blocked_task_id == task_id)
        
        # Get blocks dependencies (tasks that this one blocks)
        blocks_query = db.session.query(Task).join(
            TaskDependency, Task.id == TaskDependency.blocked_task_id
        ).filter(TaskDependency.blocking_task_id == task_id)
        
        blocked_by_tasks = blocked_by_query.all()
        blocks_tasks = blocks_query.all()
        
        def task_to_dict(t):
            return {
                'id': t.id,
                'name': t.name,
                'task_number': t.task_number
            }
        
        return jsonify({
            'success': True,
            'dependencies': {
                'blocked_by': [task_to_dict(t) for t in blocked_by_tasks],
                'blocks': [task_to_dict(t) for t in blocks_tasks]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting task dependencies: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>/dependencies', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def add_task_dependency(task_id):
    """Add a dependency for a task"""
    try:
        data = request.get_json()
        task_number = data.get('task_number')
        dependency_type = data.get('type')  # 'blocked_by' or 'blocks'
        
        if not task_number or not dependency_type:
            return jsonify({'success': False, 'message': 'Task number and type are required'})
        
        # Get the main task
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Find the dependency task by task number
        dependency_task = Task.query.join(Project).filter(
            Task.task_number == task_number,
            Project.company_id == g.user.company_id
        ).first()
        
        if not dependency_task:
            return jsonify({'success': False, 'message': f'Task {task_number} not found'})
        
        # Prevent self-dependency
        if dependency_task.id == task_id:
            return jsonify({'success': False, 'message': 'A task cannot depend on itself'})
        
        # Create the dependency based on type
        if dependency_type == 'blocked_by':
            # Current task is blocked by the dependency task
            blocked_task_id = task_id
            blocking_task_id = dependency_task.id
        elif dependency_type == 'blocks':
            # Current task blocks the dependency task
            blocked_task_id = dependency_task.id
            blocking_task_id = task_id
        else:
            return jsonify({'success': False, 'message': 'Invalid dependency type'})
        
        # Check if dependency already exists
        existing_dep = TaskDependency.query.filter_by(
            blocked_task_id=blocked_task_id,
            blocking_task_id=blocking_task_id
        ).first()
        
        if existing_dep:
            return jsonify({'success': False, 'message': 'This dependency already exists'})
        
        # Check for circular dependencies
        def would_create_cycle(blocked_id, blocking_id):
            # Use a simple DFS to check if adding this dependency would create a cycle
            visited = set()
            
            def dfs(current_blocked_id):
                if current_blocked_id in visited:
                    return False
                visited.add(current_blocked_id)
                
                # If we reach the original blocking task, we have a cycle
                if current_blocked_id == blocking_id:
                    return True
                
                # Check all tasks that block the current task
                dependencies = TaskDependency.query.filter_by(blocked_task_id=current_blocked_id).all()
                for dep in dependencies:
                    if dfs(dep.blocking_task_id):
                        return True
                
                return False
            
            return dfs(blocked_id)
        
        if would_create_cycle(blocked_task_id, blocking_task_id):
            return jsonify({'success': False, 'message': 'This dependency would create a circular dependency'})
        
        # Create the new dependency
        new_dependency = TaskDependency(
            blocked_task_id=blocked_task_id,
            blocking_task_id=blocking_task_id
        )
        
        db.session.add(new_dependency)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Dependency added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding task dependency: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>/dependencies/<int:dependency_task_id>', methods=['DELETE'])
@role_required(Role.TEAM_MEMBER)
@company_required
def remove_task_dependency(task_id, dependency_task_id):
    """Remove a dependency for a task"""
    try:
        data = request.get_json()
        dependency_type = data.get('type')  # 'blocked_by' or 'blocks'
        
        if not dependency_type:
            return jsonify({'success': False, 'message': 'Dependency type is required'})
        
        # Get the main task
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Determine which dependency to remove based on type
        if dependency_type == 'blocked_by':
            # Remove dependency where current task is blocked by dependency_task_id
            dependency = TaskDependency.query.filter_by(
                blocked_task_id=task_id,
                blocking_task_id=dependency_task_id
            ).first()
        elif dependency_type == 'blocks':
            # Remove dependency where current task blocks dependency_task_id
            dependency = TaskDependency.query.filter_by(
                blocked_task_id=dependency_task_id,
                blocking_task_id=task_id
            ).first()
        else:
            return jsonify({'success': False, 'message': 'Invalid dependency type'})
        
        if not dependency:
            return jsonify({'success': False, 'message': 'Dependency not found'})
        
        db.session.delete(dependency)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Dependency removed successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing task dependency: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# Task Archive/Restore APIs
@tasks_api_bp.route('/tasks/<int:task_id>/archive', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def archive_task(task_id):
    """Archive a completed task"""
    try:
        # Get the task and verify ownership through project
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Only allow archiving completed tasks
        if task.status != TaskStatus.COMPLETED:
            return jsonify({'success': False, 'message': 'Only completed tasks can be archived'})
        
        # Archive the task
        task.status = TaskStatus.ARCHIVED
        task.archived_date = datetime.now().date()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Task archived successfully',
            'archived_date': task.archived_date.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error archiving task: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/tasks/<int:task_id>/restore', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def restore_task(task_id):
    """Restore an archived task to completed status"""
    try:
        # Get the task and verify ownership through project
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Only allow restoring archived tasks
        if task.status != TaskStatus.ARCHIVED:
            return jsonify({'success': False, 'message': 'Only archived tasks can be restored'})
        
        # Restore the task to completed status
        task.status = TaskStatus.COMPLETED
        task.archived_date = None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Task restored successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error restoring task: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# Subtask API Routes
@tasks_api_bp.route('/subtasks', methods=['POST'])
@role_required(Role.TEAM_MEMBER)
@company_required
def create_subtask():
    try:
        data = request.get_json()
        task_id = data.get('task_id')

        # Verify task access
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()

        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})

        # Validate required fields
        name = data.get('name')
        if not name:
            return jsonify({'success': False, 'message': 'Subtask name is required'})

        # Parse dates
        start_date = None
        due_date = None
        if data.get('start_date'):
            start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        if data.get('due_date'):
            due_date = datetime.strptime(data.get('due_date'), '%Y-%m-%d').date()

        # Create subtask
        subtask = SubTask(
            name=name,
            description=data.get('description', ''),
            status=TaskStatus[data.get('status', 'TODO')],
            priority=TaskPriority[data.get('priority', 'MEDIUM')],
            estimated_hours=float(data.get('estimated_hours')) if data.get('estimated_hours') else None,
            task_id=task_id,
            assigned_to_id=int(data.get('assigned_to_id')) if data.get('assigned_to_id') else None,
            start_date=start_date,
            due_date=due_date,
            created_by_id=g.user.id
        )

        db.session.add(subtask)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask created successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/subtasks/<int:subtask_id>', methods=['GET'])
@role_required(Role.TEAM_MEMBER)
@company_required
def get_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        subtask_data = {
            'id': subtask.id,
            'name': subtask.name,
            'description': subtask.description,
            'status': subtask.status.name,
            'priority': subtask.priority.name,
            'estimated_hours': subtask.estimated_hours,
            'assigned_to_id': subtask.assigned_to_id,
            'start_date': subtask.start_date.isoformat() if subtask.start_date else None,
            'due_date': subtask.due_date.isoformat() if subtask.due_date else None
        }

        return jsonify({'success': True, 'subtask': subtask_data})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/subtasks/<int:subtask_id>', methods=['PUT'])
@role_required(Role.TEAM_MEMBER)
@company_required
def update_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        data = request.get_json()

        # Update subtask fields
        if 'name' in data:
            subtask.name = data['name']
        if 'description' in data:
            subtask.description = data['description']
        if 'status' in data:
            subtask.status = TaskStatus[data['status']]
            if data['status'] == 'COMPLETED':
                subtask.completed_date = datetime.now().date()
            else:
                subtask.completed_date = None
        if 'priority' in data:
            subtask.priority = TaskPriority[data['priority']]
        if 'estimated_hours' in data:
            subtask.estimated_hours = float(data['estimated_hours']) if data['estimated_hours'] else None
        if 'assigned_to_id' in data:
            subtask.assigned_to_id = int(data['assigned_to_id']) if data['assigned_to_id'] else None
        if 'start_date' in data:
            subtask.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date() if data['start_date'] else None
        if 'due_date' in data:
            subtask.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data['due_date'] else None

        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_api_bp.route('/subtasks/<int:subtask_id>', methods=['DELETE'])
@role_required(Role.TEAM_LEADER)  # Only team leaders and above can delete subtasks
@company_required
def delete_subtask(subtask_id):
    try:
        subtask = SubTask.query.join(Task).join(Project).filter(
            SubTask.id == subtask_id,
            Project.company_id == g.user.company_id
        ).first()

        if not subtask or not subtask.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Subtask not found or access denied'})

        db.session.delete(subtask)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subtask deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# Comment API Routes
@tasks_api_bp.route('/tasks/<int:task_id>/comments', methods=['GET', 'POST'])
@login_required
@company_required
def handle_task_comments(task_id):
    """Handle GET and POST requests for task comments"""
    if request.method == 'GET':
        return get_task_comments(task_id)
    else:  # POST
        return create_task_comment(task_id)


@tasks_api_bp.route('/comments/<int:comment_id>', methods=['PUT', 'DELETE'])
@login_required
@company_required
def handle_comment(comment_id):
    """Handle PUT and DELETE requests for a specific comment"""
    if request.method == 'DELETE':
        return delete_comment(comment_id)
    else:  # PUT
        return update_comment(comment_id)


def delete_comment(comment_id):
    """Delete a comment"""
    try:
        comment = Comment.query.join(Task).join(Project).filter(
            Comment.id == comment_id,
            Project.company_id == g.user.company_id
        ).first()
        
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found'}), 404
        
        # Check if user can delete this comment
        if not comment.can_user_delete(g.user):
            return jsonify({'success': False, 'message': 'You do not have permission to delete this comment'}), 403
        
        # Delete the comment (replies will be cascade deleted)
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Comment deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment {comment_id}: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete comment'}), 500


def update_comment(comment_id):
    """Update a comment"""
    try:
        comment = Comment.query.join(Task).join(Project).filter(
            Comment.id == comment_id,
            Project.company_id == g.user.company_id
        ).first()
        
        if not comment:
            return jsonify({'success': False, 'message': 'Comment not found'}), 404
        
        # Check if user can edit this comment
        if not comment.can_user_edit(g.user):
            return jsonify({'success': False, 'message': 'You do not have permission to edit this comment'}), 403
        
        data = request.json
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return jsonify({'success': False, 'message': 'Comment content is required'}), 400
        
        # Update the comment
        comment.content = new_content
        comment.is_edited = True
        comment.edited_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment updated successfully',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'is_edited': comment.is_edited,
                'edited_at': comment.edited_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating comment {comment_id}: {e}")
        return jsonify({'success': False, 'message': 'Failed to update comment'}), 500


def get_task_comments(task_id):
    """Get all comments for a task that the user can view"""
    try:
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        
        if not task or not task.can_user_access(g.user):
            return jsonify({'success': False, 'message': 'Task not found or access denied'})
        
        # Get all comments for the task
        comments = []
        for comment in task.comments.order_by(Comment.created_at.desc()):
            if comment.can_user_view(g.user):
                comment_data = {
                    'id': comment.id,
                    'content': comment.content,
                    'visibility': comment.visibility.value,
                    'is_edited': comment.is_edited,
                    'edited_at': comment.edited_at.isoformat() if comment.edited_at else None,
                    'created_at': comment.created_at.isoformat(),
                    'author': {
                        'id': comment.created_by.id,
                        'username': comment.created_by.username,
                        'avatar_url': comment.created_by.get_avatar_url(40)
                    },
                    'can_edit': comment.can_user_edit(g.user),
                    'can_delete': comment.can_user_delete(g.user),
                    'replies': []
                }
                
                # Add replies if any
                for reply in comment.replies:
                    if reply.can_user_view(g.user):
                        reply_data = {
                            'id': reply.id,
                            'content': reply.content,
                            'is_edited': reply.is_edited,
                            'edited_at': reply.edited_at.isoformat() if reply.edited_at else None,
                            'created_at': reply.created_at.isoformat(),
                            'author': {
                                'id': reply.created_by.id,
                                'username': reply.created_by.username,
                                'avatar_url': reply.created_by.get_avatar_url(40)
                            },
                            'can_edit': reply.can_user_edit(g.user),
                            'can_delete': reply.can_user_delete(g.user)
                        }
                        comment_data['replies'].append(reply_data)
                
                comments.append(comment_data)
        
        # Check if user can use team visibility
        company_settings = CompanySettings.query.filter_by(company_id=g.user.company_id).first()
        allow_team_visibility = company_settings.allow_team_visibility_comments if company_settings else True
        
        return jsonify({
            'success': True,
            'comments': comments,
            'allow_team_visibility': allow_team_visibility
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


def create_task_comment(task_id):
    """Create a new comment on a task"""
    try:
        # Get the task and verify access through project
        task = Task.query.join(Project).filter(
            Task.id == task_id,
            Project.company_id == g.user.company_id
        ).first()
        
        if not task:
            return jsonify({'success': False, 'message': 'Task not found'})
        
        # Check if user has access to this task's project
        if not task.project.is_user_allowed(g.user):
            return jsonify({'success': False, 'message': 'Access denied'})
        
        data = request.json
        content = data.get('content', '').strip()
        visibility = data.get('visibility', CommentVisibility.COMPANY.value)
        
        if not content:
            return jsonify({'success': False, 'message': 'Comment content is required'})
        
        # Validate visibility - handle case conversion
        try:
            # Convert from frontend format (TEAM/COMPANY) to enum format (Team/Company)
            if visibility == 'TEAM':
                visibility_enum = CommentVisibility.TEAM
            elif visibility == 'COMPANY':
                visibility_enum = CommentVisibility.COMPANY
            else:
                # Try to use the value directly in case it's already in the right format
                visibility_enum = CommentVisibility(visibility)
        except ValueError:
            return jsonify({'success': False, 'message': f'Invalid visibility option: {visibility}'})
        
        # Create the comment
        comment = Comment(
            content=content,
            task_id=task_id,
            created_by_id=g.user.id,
            visibility=visibility_enum
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Comment added successfully',
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'visibility': comment.visibility.value,
                'created_at': comment.created_at.isoformat(),
                'user': {
                    'id': comment.created_by.id,
                    'username': comment.created_by.username
                }
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating task comment: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})