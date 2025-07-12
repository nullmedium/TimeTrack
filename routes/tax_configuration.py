"""
Tax configuration management routes
"""

from flask import Blueprint, render_template, request, g, jsonify, redirect, url_for, flash
from models import db, TaxConfiguration, PricingType, CompanySettings
from routes.auth import role_required, company_required, Role
from sqlalchemy.exc import IntegrityError

tax_config_bp = Blueprint('tax_config', __name__, url_prefix='/settings/tax')


@tax_config_bp.route('/')
@role_required(Role.ADMIN)
@company_required
def tax_configuration_list():
    """List all tax configurations for the company"""
    configurations = TaxConfiguration.query.filter_by(
        company_id=g.user.company_id
    ).order_by(TaxConfiguration.country_name).all()
    
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    
    return render_template('admin_tax_configuration.html',
                         title='Tax Configuration',
                         configurations=configurations,
                         company_settings=company_settings,
                         PricingType=PricingType)


@tax_config_bp.route('/add', methods=['GET', 'POST'])
@role_required(Role.ADMIN)
@company_required
def add_tax_configuration():
    """Add new tax configuration"""
    if request.method == 'POST':
        try:
            config = TaxConfiguration(
                company_id=g.user.company_id,
                country_code=request.form.get('country_code').upper(),
                country_name=request.form.get('country_name'),
                standard_tax_rate=request.form.get('standard_tax_rate', type=float),
                reduced_tax_rate=request.form.get('reduced_tax_rate', type=float) or None,
                tax_name=request.form.get('tax_name'),
                is_default=request.form.get('is_default') == 'on',
                is_active=request.form.get('is_active') == 'on'
            )
            
            # If setting as default, unset other defaults
            if config.is_default:
                TaxConfiguration.query.filter_by(
                    company_id=g.user.company_id,
                    is_default=True
                ).update({'is_default': False})
            
            db.session.add(config)
            db.session.commit()
            
            flash('Tax configuration added successfully', 'success')
            return redirect(url_for('tax_config.tax_configuration_list'))
            
        except IntegrityError:
            db.session.rollback()
            flash('A configuration for this country already exists', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding tax configuration: {str(e)}', 'error')
    
    # Get default configurations for easy setup
    default_configs = TaxConfiguration.get_default_configurations()
    
    return render_template('admin_tax_configuration_form.html',
                         title='Add Tax Configuration',
                         default_configs=default_configs)


@tax_config_bp.route('/<int:config_id>/edit', methods=['GET', 'POST'])
@role_required(Role.ADMIN)
@company_required
def edit_tax_configuration(config_id):
    """Edit tax configuration"""
    config = TaxConfiguration.query.filter_by(
        id=config_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    if request.method == 'POST':
        try:
            config.country_name = request.form.get('country_name')
            config.standard_tax_rate = request.form.get('standard_tax_rate', type=float)
            config.reduced_tax_rate = request.form.get('reduced_tax_rate', type=float) or None
            config.tax_name = request.form.get('tax_name')
            config.is_default = request.form.get('is_default') == 'on'
            config.is_active = request.form.get('is_active') == 'on'
            
            # If setting as default, unset other defaults
            if config.is_default:
                TaxConfiguration.query.filter(
                    TaxConfiguration.company_id == g.user.company_id,
                    TaxConfiguration.id != config.id,
                    TaxConfiguration.is_default == True
                ).update({'is_default': False})
            
            db.session.commit()
            flash('Tax configuration updated successfully', 'success')
            return redirect(url_for('tax_config.tax_configuration_list'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating tax configuration: {str(e)}', 'error')
    
    return render_template('admin_tax_configuration_form.html',
                         title='Edit Tax Configuration',
                         config=config)


@tax_config_bp.route('/<int:config_id>/delete', methods=['POST'])
@role_required(Role.ADMIN)
@company_required
def delete_tax_configuration(config_id):
    """Delete tax configuration"""
    config = TaxConfiguration.query.filter_by(
        id=config_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    # Check if it's being used
    if config.invoices:
        flash('Cannot delete tax configuration that is being used by invoices', 'error')
        return redirect(url_for('tax_config.tax_configuration_list'))
    
    db.session.delete(config)
    db.session.commit()
    
    flash('Tax configuration deleted successfully', 'success')
    return redirect(url_for('tax_config.tax_configuration_list'))


@tax_config_bp.route('/pricing-type', methods=['POST'])
@role_required(Role.ADMIN)
@company_required
def update_pricing_type():
    """Update company pricing type"""
    pricing_type = request.form.get('pricing_type')
    
    if pricing_type not in [PricingType.NET, PricingType.GROSS]:
        flash('Invalid pricing type', 'error')
        return redirect(url_for('tax_config.tax_configuration_list'))
    
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    company_settings.pricing_type = pricing_type
    db.session.commit()
    
    flash(f'Pricing type updated to {pricing_type.upper()}', 'success')
    return redirect(url_for('tax_config.tax_configuration_list'))


@tax_config_bp.route('/set-default/<int:config_id>', methods=['POST'])
@role_required(Role.ADMIN)
@company_required
def set_default_tax_configuration(config_id):
    """Set default tax configuration for the company"""
    config = TaxConfiguration.query.filter_by(
        id=config_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    company_settings.default_tax_configuration_id = config.id
    
    # Also set this as the default in tax configurations
    TaxConfiguration.query.filter_by(
        company_id=g.user.company_id
    ).update({'is_default': False})
    
    config.is_default = True
    db.session.commit()
    
    flash(f'Default tax configuration set to {config.country_name}', 'success')
    return redirect(url_for('tax_config.tax_configuration_list'))