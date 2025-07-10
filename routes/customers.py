"""
Customer management routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
from models import db, Customer, Project, Role
from routes.auth import login_required, role_required, company_required
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

customers_bp = Blueprint('customers', __name__, url_prefix='/admin')


@customers_bp.route('/customers')
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def customers():
    """Display customers list"""
    try:
        # Get customers for the company
        customers = Customer.query.filter_by(company_id=g.user.company_id).order_by(Customer.name).all()
        
        # Calculate statistics
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.is_active])
        customers_with_projects = len([c for c in customers if len(c.projects) > 0])
        
        return render_template('admin_customers.html',
                             customers=customers,
                             total_customers=total_customers,
                             active_customers=active_customers,
                             customers_with_projects=customers_with_projects)
    except Exception as e:
        logger.error(f"Error loading customers: {str(e)}")
        flash('Error loading customers', 'error')
        return redirect(url_for('index'))


@customers_bp.route('/customers/new')
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def new_customer():
    """Display new customer form"""
    return render_template('create_customer.html')


@customers_bp.route('/customers/create', methods=['POST'])
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def create_customer():
    """Create a new customer"""
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validate required fields
        if not name:
            flash('Customer name is required', 'error')
            return redirect(url_for('customers.new_customer'))
        
        if not code:
            flash('Customer code is required', 'error')
            return redirect(url_for('customers.new_customer'))
        
        # Check if customer code already exists
        existing = Customer.query.filter_by(
            company_id=g.user.company_id,
            code=code
        ).first()
        
        if existing:
            flash('Customer code already exists', 'error')
            return redirect(url_for('customers.new_customer'))
        
        # Create new customer
        customer = Customer(
            name=name,
            code=code,
            email=email,
            phone=phone,
            address_line1=request.form.get('address_line1', '').strip(),
            address_line2=request.form.get('address_line2', '').strip(),
            city=request.form.get('city', '').strip(),
            state=request.form.get('state', '').strip(),
            postal_code=request.form.get('postal_code', '').strip(),
            country=request.form.get('country', '').strip(),
            billing_email=request.form.get('billing_email', '').strip(),
            tax_id=request.form.get('tax_id', '').strip(),
            payment_terms=int(request.form.get('payment_terms', 30)),
            notes=request.form.get('notes', '').strip(),
            is_active=True,
            company_id=g.user.company_id,
            created_by_id=g.user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash(f'Customer "{name}" created successfully', 'success')
        return redirect(url_for('customers.customers'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating customer: {str(e)}")
        flash('Error creating customer', 'error')
        return redirect(url_for('customers.new_customer'))


@customers_bp.route('/customers/<int:customer_id>/edit')
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def edit_customer(customer_id):
    """Display edit customer form"""
    try:
        customer = Customer.query.filter_by(
            id=customer_id,
            company_id=g.user.company_id
        ).first()
        
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('customers.customers'))
        
        return render_template('edit_customer.html', customer=customer)
        
    except Exception as e:
        logger.error(f"Error loading customer for edit: {str(e)}")
        flash('Error loading customer', 'error')
        return redirect(url_for('customers.customers'))


@customers_bp.route('/customers/<int:customer_id>/update', methods=['POST'])
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def update_customer(customer_id):
    """Update a customer"""
    try:
        customer = Customer.query.filter_by(
            id=customer_id,
            company_id=g.user.company_id
        ).first()
        
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('customers.customers'))
        
        # Get form data
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        
        # Validate required fields
        if not name:
            flash('Customer name is required', 'error')
            return redirect(url_for('customers.edit_customer', customer_id=customer_id))
        
        if not code:
            flash('Customer code is required', 'error')
            return redirect(url_for('customers.edit_customer', customer_id=customer_id))
        
        # Check if customer code already exists (if changed)
        if code != customer.code:
            existing = Customer.query.filter_by(
                company_id=g.user.company_id,
                code=code
            ).first()
            
            if existing:
                flash('Customer code already exists', 'error')
                return redirect(url_for('customers.edit_customer', customer_id=customer_id))
        
        # Update customer
        customer.name = name
        customer.code = code
        customer.email = request.form.get('email', '').strip()
        customer.phone = request.form.get('phone', '').strip()
        customer.address_line1 = request.form.get('address_line1', '').strip()
        customer.address_line2 = request.form.get('address_line2', '').strip()
        customer.city = request.form.get('city', '').strip()
        customer.state = request.form.get('state', '').strip()
        customer.postal_code = request.form.get('postal_code', '').strip()
        customer.country = request.form.get('country', '').strip()
        customer.billing_email = request.form.get('billing_email', '').strip()
        customer.tax_id = request.form.get('tax_id', '').strip()
        customer.payment_terms = int(request.form.get('payment_terms', 30))
        customer.notes = request.form.get('notes', '').strip()
        customer.is_active = request.form.get('is_active') == 'on'
        customer.updated_at = datetime.now()
        
        db.session.commit()
        
        flash(f'Customer "{name}" updated successfully', 'success')
        return redirect(url_for('customers.customers'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating customer: {str(e)}")
        flash('Error updating customer', 'error')
        return redirect(url_for('customers.edit_customer', customer_id=customer_id))