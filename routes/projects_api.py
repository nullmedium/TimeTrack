"""
Project Management API Routes
Handles all project-related API endpoints including categories
"""

from flask import Blueprint, jsonify, request, g
from sqlalchemy import or_ as sql_or
from models import db, Project, ProjectCategory, Role
from routes.auth import role_required, company_required, admin_required
import logging

logger = logging.getLogger(__name__)

projects_api_bp = Blueprint('projects_api', __name__, url_prefix='/api')


# Category Management API Routes
@projects_api_bp.route('/admin/categories', methods=['POST'])
@role_required(Role.ADMIN)
@company_required
def create_category():
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        color = data.get('color', '#007bff')
        icon = data.get('icon', '')

        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'})

        # Check if category already exists
        existing = ProjectCategory.query.filter_by(
            name=name,
            company_id=g.user.company_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Category name already exists'})

        category = ProjectCategory(
            name=name,
            description=description,
            color=color,
            icon=icon,
            company_id=g.user.company_id,
            created_by_id=g.user.id
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category created successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@projects_api_bp.route('/admin/categories/<int:category_id>', methods=['PUT'])
@role_required(Role.ADMIN)
@company_required
def update_category(category_id):
    try:
        category = ProjectCategory.query.filter_by(
            id=category_id,
            company_id=g.user.company_id
        ).first()

        if not category:
            return jsonify({'success': False, 'message': 'Category not found'})

        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'success': False, 'message': 'Category name is required'})

        # Check if name conflicts with another category
        existing = ProjectCategory.query.filter(
            ProjectCategory.name == name,
            ProjectCategory.company_id == g.user.company_id,
            ProjectCategory.id != category_id
        ).first()

        if existing:
            return jsonify({'success': False, 'message': 'Category name already exists'})

        category.name = name
        category.description = data.get('description', '')
        category.color = data.get('color', category.color)
        category.icon = data.get('icon', '')

        db.session.commit()

        return jsonify({'success': True, 'message': 'Category updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@projects_api_bp.route('/admin/categories/<int:category_id>', methods=['DELETE'])
@role_required(Role.ADMIN)
@company_required
def delete_category(category_id):
    try:
        category = ProjectCategory.query.filter_by(
            id=category_id,
            company_id=g.user.company_id
        ).first()

        if not category:
            return jsonify({'success': False, 'message': 'Category not found'})

        # Unassign projects from this category
        projects = Project.query.filter_by(category_id=category_id).all()
        for project in projects:
            project.category_id = None

        db.session.delete(category)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category deleted successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@projects_api_bp.route('/search/projects')
@role_required(Role.TEAM_MEMBER)
@company_required
def search_projects():
    """Search for projects for smart search auto-completion"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({'success': True, 'projects': []})
        
        # Search projects the user has access to
        projects = Project.query.filter(
            Project.company_id == g.user.company_id,
            sql_or(
                Project.code.ilike(f'%{query}%'),
                Project.name.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        # Filter projects user has access to
        accessible_projects = [
            project for project in projects 
            if project.is_user_allowed(g.user)
        ]
        
        project_list = [
            {
                'id': project.id,
                'code': project.code,
                'name': project.name
            }
            for project in accessible_projects
        ]
        
        return jsonify({'success': True, 'projects': project_list})
        
    except Exception as e:
        logger.error(f"Error in search_projects: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})