"""
Company management routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session
from models import db, Company, User, Role, Team, Project, SystemSettings, CompanyWorkConfig, WorkRegion
from routes.auth import admin_required, company_required, login_required
import logging
import re

logger = logging.getLogger(__name__)

companies_bp = Blueprint('companies', __name__, url_prefix='/admin/company')


@companies_bp.route('', methods=['GET', 'POST'])
@admin_required
@company_required
def admin_company():
    """View and manage company settings"""
    company = g.company

    # Handle form submissions
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_company_details':
            # Handle company details update
            name = request.form.get('name')
            description = request.form.get('description', '')
            max_users = request.form.get('max_users')
            is_active = 'is_active' in request.form

            # Validate input
            error = None
            if not name:
                error = 'Company name is required'
            elif name != company.name and Company.query.filter_by(name=name).first():
                error = 'Company name already exists'

            if max_users:
                try:
                    max_users = int(max_users)
                    if max_users < 1:
                        error = 'Maximum users must be at least 1'
                except ValueError:
                    error = 'Maximum users must be a valid number'
            else:
                max_users = None

            if error is None:
                company.name = name
                company.description = description
                company.max_users = max_users
                company.is_active = is_active
                db.session.commit()

                flash('Company details updated successfully!', 'success')
            else:
                flash(error, 'error')
            
            return redirect(url_for('companies.admin_company'))
            
        elif action == 'update_system_settings':
            # Update registration setting
            registration_enabled = 'registration_enabled' in request.form
            reg_setting = SystemSettings.query.filter_by(key='registration_enabled').first()
            if reg_setting:
                reg_setting.value = 'true' if registration_enabled else 'false'

            # Update email verification setting
            email_verification_required = 'email_verification_required' in request.form
            email_setting = SystemSettings.query.filter_by(key='email_verification_required').first()
            if email_setting:
                email_setting.value = 'true' if email_verification_required else 'false'

            db.session.commit()
            flash('System settings updated successfully!', 'success')
            return redirect(url_for('companies.admin_company'))
            
        elif action == 'update_work_policies':
            # Get or create company work config
            work_config = CompanyWorkConfig.query.filter_by(company_id=g.user.company_id).first()
            if not work_config:
                # Create default config for the company
                preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
                work_config = CompanyWorkConfig(
                    company_id=g.user.company_id,
                    standard_hours_per_day=preset['standard_hours_per_day'],
                    standard_hours_per_week=preset['standard_hours_per_week'],
                    work_region=WorkRegion.GERMANY,
                    overtime_enabled=preset['overtime_enabled'],
                    overtime_rate=preset['overtime_rate'],
                    double_time_enabled=preset['double_time_enabled'],
                    double_time_threshold=preset['double_time_threshold'],
                    double_time_rate=preset['double_time_rate'],
                    require_breaks=preset['require_breaks'],
                    break_duration_minutes=preset['break_duration_minutes'],
                    break_after_hours=preset['break_after_hours'],
                    weekly_overtime_threshold=preset['weekly_overtime_threshold'],
                    weekly_overtime_rate=preset['weekly_overtime_rate']
                )
                db.session.add(work_config)
                db.session.flush()
            
            try:
                # Handle regional preset selection
                if request.form.get('apply_preset'):
                    region_code = request.form.get('region_preset')
                    if region_code:
                        region = WorkRegion(region_code)
                        preset = CompanyWorkConfig.get_regional_preset(region)

                        work_config.standard_hours_per_day = preset['standard_hours_per_day']
                        work_config.standard_hours_per_week = preset['standard_hours_per_week']
                        work_config.work_region = region
                        work_config.overtime_enabled = preset['overtime_enabled']
                        work_config.overtime_rate = preset['overtime_rate']
                        work_config.double_time_enabled = preset['double_time_enabled']
                        work_config.double_time_threshold = preset['double_time_threshold']
                        work_config.double_time_rate = preset['double_time_rate']
                        work_config.require_breaks = preset['require_breaks']
                        work_config.break_duration_minutes = preset['break_duration_minutes']
                        work_config.break_after_hours = preset['break_after_hours']
                        work_config.weekly_overtime_threshold = preset['weekly_overtime_threshold']
                        work_config.weekly_overtime_rate = preset['weekly_overtime_rate']

                        db.session.commit()
                        flash(f'Applied {preset["region_name"]} work policy preset', 'success')
                else:
                    # Handle manual configuration update
                    work_config.standard_hours_per_day = float(request.form.get('standard_hours_per_day', 8.0))
                    work_config.standard_hours_per_week = float(request.form.get('standard_hours_per_week', 40.0))
                    work_config.overtime_enabled = request.form.get('overtime_enabled') == 'on'
                    work_config.overtime_rate = float(request.form.get('overtime_rate', 1.5))
                    work_config.double_time_enabled = request.form.get('double_time_enabled') == 'on'
                    work_config.double_time_threshold = float(request.form.get('double_time_threshold', 12.0))
                    work_config.double_time_rate = float(request.form.get('double_time_rate', 2.0))
                    work_config.require_breaks = request.form.get('require_breaks') == 'on'
                    work_config.break_duration_minutes = int(request.form.get('break_duration_minutes', 30))
                    work_config.break_after_hours = float(request.form.get('break_after_hours', 6.0))
                    work_config.weekly_overtime_threshold = float(request.form.get('weekly_overtime_threshold', 40.0))
                    work_config.weekly_overtime_rate = float(request.form.get('weekly_overtime_rate', 1.5))
                    work_config.work_region = WorkRegion.OTHER
                    # region_name removed - using work_region enum value instead

                    db.session.commit()
                    flash('Work policies updated successfully!', 'success')
                    
            except ValueError:
                flash('Please enter valid numbers for all fields', 'error')
                
            return redirect(url_for('companies.admin_company'))

    # Get company statistics
    stats = {
        'total_users': User.query.filter_by(company_id=company.id).count(),
        'total_teams': Team.query.filter_by(company_id=company.id).count(),
        'total_projects': Project.query.filter_by(company_id=company.id).count(),
        'active_projects': Project.query.filter_by(company_id=company.id, is_active=True).count(),
    }
    
    # Get current system settings
    settings = {}
    for setting in SystemSettings.query.all():
        if setting.key == 'registration_enabled':
            settings['registration_enabled'] = setting.value == 'true'
        elif setting.key == 'email_verification_required':
            settings['email_verification_required'] = setting.value == 'true'
    
    # Get or create company work config
    work_config = CompanyWorkConfig.query.filter_by(company_id=g.user.company_id).first()
    if not work_config:
        # Create default config for the company
        preset = CompanyWorkConfig.get_regional_preset(WorkRegion.GERMANY)
        work_config = CompanyWorkConfig(
            company_id=g.user.company_id,
            standard_hours_per_day=preset['standard_hours_per_day'],
            standard_hours_per_week=preset['standard_hours_per_week'],
            work_region=WorkRegion.GERMANY,
            overtime_enabled=preset['overtime_enabled'],
            overtime_rate=preset['overtime_rate'],
            double_time_enabled=preset['double_time_enabled'],
            double_time_threshold=preset['double_time_threshold'],
            double_time_rate=preset['double_time_rate'],
            require_breaks=preset['require_breaks'],
            break_duration_minutes=preset['break_duration_minutes'],
            break_after_hours=preset['break_after_hours'],
            weekly_overtime_threshold=preset['weekly_overtime_threshold'],
            weekly_overtime_rate=preset['weekly_overtime_rate']
        )
        db.session.add(work_config)
        db.session.commit()
    
    # Get available regional presets
    regional_presets = []
    for region in WorkRegion:
        preset = CompanyWorkConfig.get_regional_preset(region)
        regional_presets.append({
            'code': region.value,
            'name': preset['region_name'],
            'description': f"{preset['standard_hours_per_day']}h/day, {preset['break_duration_minutes']}min break after {preset['break_after_hours']}h"
        })

    return render_template('admin_company.html', 
                         title='Company Management', 
                         company=company, 
                         stats=stats,
                         settings=settings,
                         work_config=work_config,
                         regional_presets=regional_presets,
                         WorkRegion=WorkRegion)




@companies_bp.route('/users')
@admin_required
@company_required
def company_users():
    """List all users in the company with detailed information"""
    users = User.query.filter_by(company_id=g.company.id).order_by(User.created_at.desc()).all()

    # Calculate user statistics
    user_stats = {
        'total': len(users),
        'verified': len([u for u in users if u.is_verified]),
        'unverified': len([u for u in users if not u.is_verified]),
        'blocked': len([u for u in users if u.is_blocked]),
        'active': len([u for u in users if not u.is_blocked and u.is_verified]),
        'admins': len([u for u in users if u.role == Role.ADMIN]),
        'supervisors': len([u for u in users if u.role == Role.SUPERVISOR]),
        'team_leaders': len([u for u in users if u.role == Role.TEAM_LEADER]),
        'team_members': len([u for u in users if u.role == Role.TEAM_MEMBER]),
    }

    return render_template('company_users.html', 
                         title='Company Users', 
                         company=g.company,
                         users=users,
                         stats=user_stats)


# Setup company route (separate from company blueprint due to different URL)
def setup_company():
    """Company setup route for creating new companies with admin users"""
    existing_companies = Company.query.count()

    # Determine access level
    is_initial_setup = existing_companies == 0
    is_system_admin = g.user and g.user.role == Role.SYSTEM_ADMIN
    is_authorized = is_initial_setup or is_system_admin

    # Check authorization for non-initial setups
    if not is_initial_setup and not is_system_admin:
        flash('You do not have permission to create new companies.', 'error')
        return redirect(url_for('home') if g.user else url_for('login'))

    if request.method == 'POST':
        company_name = request.form.get('company_name')
        company_description = request.form.get('company_description', '')
        admin_username = request.form.get('admin_username')
        admin_email = request.form.get('admin_email')
        admin_password = request.form.get('admin_password')
        confirm_password = request.form.get('confirm_password')

        # Validate input
        error = None
        if not company_name:
            error = 'Company name is required'
        elif not admin_username:
            error = 'Admin username is required'
        elif not admin_email:
            error = 'Admin email is required'
        elif not admin_password:
            error = 'Admin password is required'
        elif admin_password != confirm_password:
            error = 'Passwords do not match'
        elif len(admin_password) < 6:
            error = 'Password must be at least 6 characters long'

        if error is None:
            try:
                # Generate company slug
                slug = re.sub(r'[^\w\s-]', '', company_name.lower())
                slug = re.sub(r'[-\s]+', '-', slug).strip('-')

                # Ensure slug uniqueness
                base_slug = slug
                counter = 1
                while Company.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Create company
                company = Company(
                    name=company_name,
                    slug=slug,
                    description=company_description,
                    is_active=True
                )
                db.session.add(company)
                db.session.flush()  # Get company.id without committing

                # Check if username/email already exists in this company context
                existing_user_by_username = User.query.filter_by(
                    username=admin_username,
                    company_id=company.id
                ).first()
                existing_user_by_email = User.query.filter_by(
                    email=admin_email,
                    company_id=company.id
                ).first()

                if existing_user_by_username:
                    error = 'Username already exists in this company'
                elif existing_user_by_email:
                    error = 'Email already registered in this company'

                if error is None:
                    # Create admin user
                    admin_user = User(
                        username=admin_username,
                        email=admin_email,
                        company_id=company.id,
                        role=Role.ADMIN,
                        is_verified=True  # Auto-verify company admin
                    )
                    admin_user.set_password(admin_password)
                    db.session.add(admin_user)
                    db.session.commit()

                    if is_initial_setup:
                        # Auto-login the admin user for initial setup
                        session['user_id'] = admin_user.id
                        session['username'] = admin_user.username
                        session['role'] = admin_user.role.value

                        flash(f'Company "{company_name}" created successfully! You are now logged in as the administrator.', 'success')
                        return redirect(url_for('home'))
                    else:
                        # For super admin creating additional companies, don't auto-login
                        flash(f'Company "{company_name}" created successfully! Admin user "{admin_username}" has been created with the company code "{slug}".', 'success')
                        return redirect(url_for('companies.admin_company') if g.user else url_for('login'))
                else:
                    db.session.rollback()

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error during company setup: {str(e)}")
                error = f"An error occurred during setup: {str(e)}"

        if error:
            flash(error, 'error')

    return render_template('setup_company.html',
                         title='Company Setup',
                         existing_companies=existing_companies,
                         is_initial_setup=is_initial_setup,
                         is_super_admin=is_system_admin)