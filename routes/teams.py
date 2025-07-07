"""
Team Management Routes
Handles all team-related views and operations
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort
from models import db, Team, User
from routes.auth import admin_required, company_required
from utils.validation import FormValidator
from utils.repository import TeamRepository

teams_bp = Blueprint('teams', __name__, url_prefix='/admin/teams')


@teams_bp.route('')
@admin_required
@company_required
def admin_teams():
    team_repo = TeamRepository()
    teams = team_repo.get_with_member_count(g.user.company_id)
    return render_template('admin_teams.html', title='Team Management', teams=teams)


@teams_bp.route('/create', methods=['GET', 'POST'])
@admin_required
@company_required
def create_team():
    if request.method == 'POST':
        validator = FormValidator()
        team_repo = TeamRepository()
        
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate input
        validator.validate_required(name, 'Team name')
        
        if validator.is_valid() and team_repo.exists_by_name_in_company(name, g.user.company_id):
            validator.errors.add('Team name already exists in your company')

        if validator.is_valid():
            new_team = team_repo.create(
                name=name, 
                description=description, 
                company_id=g.user.company_id
            )
            team_repo.save()

            flash(f'Team "{name}" created successfully!', 'success')
            return redirect(url_for('teams.admin_teams'))

        validator.flash_errors()

    return render_template('team_form.html', title='Create Team', team=None)


@teams_bp.route('/edit/<int:team_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def edit_team(team_id):
    team_repo = TeamRepository()
    team = team_repo.get_by_id_and_company(team_id, g.user.company_id)
    
    if not team:
        abort(404)

    if request.method == 'POST':
        validator = FormValidator()
        
        name = request.form.get('name')
        description = request.form.get('description')

        # Validate input
        validator.validate_required(name, 'Team name')
        
        if validator.is_valid() and name != team.name:
            if team_repo.exists_by_name_in_company(name, g.user.company_id):
                validator.errors.add('Team name already exists in your company')

        if validator.is_valid():
            team_repo.update(team, name=name, description=description)
            team_repo.save()

            flash(f'Team "{name}" updated successfully!', 'success')
            return redirect(url_for('teams.admin_teams'))

        validator.flash_errors()

    return render_template('edit_team.html', title='Edit Team', team=team)


@teams_bp.route('/delete/<int:team_id>', methods=['POST'])
@admin_required
@company_required
def delete_team(team_id):
    team_repo = TeamRepository()
    team = team_repo.get_by_id_and_company(team_id, g.user.company_id)
    
    if not team:
        abort(404)

    # Check if team has members
    if team.users:
        flash('Cannot delete team with members. Remove all members first.', 'error')
        return redirect(url_for('teams.admin_teams'))

    team_name = team.name
    team_repo.delete(team)
    team_repo.save()

    flash(f'Team "{team_name}" deleted successfully!', 'success')
    return redirect(url_for('teams.admin_teams'))


@teams_bp.route('/<int:team_id>', methods=['GET', 'POST'])
@admin_required
@company_required
def manage_team(team_id):
    team_repo = TeamRepository()
    team = team_repo.get_by_id_and_company(team_id, g.user.company_id)
    
    if not team:
        abort(404)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_team':
            # Update team details
            validator = FormValidator()
            name = request.form.get('name')
            description = request.form.get('description')

            # Validate input
            validator.validate_required(name, 'Team name')
            
            if validator.is_valid() and name != team.name:
                if team_repo.exists_by_name_in_company(name, g.user.company_id):
                    validator.errors.add('Team name already exists in your company')

            if validator.is_valid():
                team_repo.update(team, name=name, description=description)
                team_repo.save()
                flash(f'Team "{name}" updated successfully!', 'success')
            else:
                validator.flash_errors()

        elif action == 'add_member':
            # Add user to team
            user_id = request.form.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user.team_id = team.id
                    db.session.commit()
                    flash(f'User {user.username} added to team!', 'success')
                else:
                    flash('User not found', 'error')
            else:
                flash('No user selected', 'error')

        elif action == 'remove_member':
            # Remove user from team
            user_id = request.form.get('user_id')
            if user_id:
                user = User.query.get(user_id)
                if user and user.team_id == team.id:
                    user.team_id = None
                    db.session.commit()
                    flash(f'User {user.username} removed from team!', 'success')
                else:
                    flash('User not found or not in this team', 'error')
            else:
                flash('No user selected', 'error')

    # Get team members
    team_members = User.query.filter_by(team_id=team.id).all()

    # Get users not in this team for the add member form (company-scoped)
    available_users = User.query.filter(
        User.company_id == g.user.company_id,
        (User.team_id != team.id) | (User.team_id == None)
    ).all()

    return render_template(
        'team_form.html',
        title=f'Manage Team: {team.name}',
        team=team,
        team_members=team_members,
        available_users=available_users
    )