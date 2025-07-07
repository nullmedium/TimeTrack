"""
Announcement management routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, Announcement, Company, User, Role
from routes.auth import system_admin_required
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

announcements_bp = Blueprint('announcements', __name__, url_prefix='/system-admin/announcements')


@announcements_bp.route('')
@system_admin_required
def index():
    """System Admin: Manage announcements"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    announcements = Announcement.query.order_by(Announcement.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return render_template('system_admin_announcements.html',
                         title='System Admin - Announcements',
                         announcements=announcements)


@announcements_bp.route('/new', methods=['GET', 'POST'])
@system_admin_required
def create():
    """System Admin: Create new announcement"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        announcement_type = request.form.get('announcement_type', 'info')
        is_urgent = request.form.get('is_urgent') == 'on'
        is_active = request.form.get('is_active') == 'on'

        # Handle date fields
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        start_datetime = None
        end_datetime = None

        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass

        # Handle targeting
        target_all_users = request.form.get('target_all_users') == 'on'
        target_roles = None
        target_companies = None

        if not target_all_users:
            selected_roles = request.form.getlist('target_roles')
            selected_companies = request.form.getlist('target_companies')

            if selected_roles:
                target_roles = json.dumps(selected_roles)

            if selected_companies:
                target_companies = json.dumps([int(c) for c in selected_companies])

        announcement = Announcement(
            title=title,
            content=content,
            announcement_type=announcement_type,
            is_urgent=is_urgent,
            is_active=is_active,
            start_date=start_datetime,
            end_date=end_datetime,
            target_all_users=target_all_users,
            target_roles=target_roles,
            target_companies=target_companies,
            created_by_id=g.user.id
        )

        db.session.add(announcement)
        db.session.commit()

        flash('Announcement created successfully.', 'success')
        return redirect(url_for('announcements.index'))

    # Get roles and companies for targeting options
    roles = [role.value for role in Role]
    companies = Company.query.order_by(Company.name).all()

    return render_template('system_admin_announcement_form.html',
                         title='Create Announcement',
                         announcement=None,
                         roles=roles,
                         companies=companies)


@announcements_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@system_admin_required
def edit(id):
    """System Admin: Edit announcement"""
    announcement = Announcement.query.get_or_404(id)

    if request.method == 'POST':
        announcement.title = request.form.get('title')
        announcement.content = request.form.get('content')
        announcement.announcement_type = request.form.get('announcement_type', 'info')
        announcement.is_urgent = request.form.get('is_urgent') == 'on'
        announcement.is_active = request.form.get('is_active') == 'on'

        # Handle date fields
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if start_date:
            try:
                announcement.start_date = datetime.strptime(start_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                announcement.start_date = None
        else:
            announcement.start_date = None

        if end_date:
            try:
                announcement.end_date = datetime.strptime(end_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                announcement.end_date = None
        else:
            announcement.end_date = None

        # Handle targeting
        announcement.target_all_users = request.form.get('target_all_users') == 'on'

        if not announcement.target_all_users:
            selected_roles = request.form.getlist('target_roles')
            selected_companies = request.form.getlist('target_companies')

            if selected_roles:
                announcement.target_roles = json.dumps(selected_roles)
            else:
                announcement.target_roles = None

            if selected_companies:
                announcement.target_companies = json.dumps([int(c) for c in selected_companies])
            else:
                announcement.target_companies = None
        else:
            announcement.target_roles = None
            announcement.target_companies = None

        announcement.updated_at = datetime.now()

        db.session.commit()

        flash('Announcement updated successfully.', 'success')
        return redirect(url_for('announcements.index'))

    # Get roles and companies for targeting options
    roles = [role.value for role in Role]
    companies = Company.query.order_by(Company.name).all()

    return render_template('system_admin_announcement_form.html',
                         title='Edit Announcement',
                         announcement=announcement,
                         roles=roles,
                         companies=companies)


@announcements_bp.route('/<int:id>/delete', methods=['POST'])
@system_admin_required
def delete(id):
    """System Admin: Delete announcement"""
    announcement = Announcement.query.get_or_404(id)

    db.session.delete(announcement)
    db.session.commit()

    flash('Announcement deleted successfully.', 'success')
    return redirect(url_for('announcements.index'))