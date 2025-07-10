"""
Customer API endpoints
"""

from flask import Blueprint, jsonify, request, g
from models import db, Customer, Project, Role
from routes.auth import login_required, role_required, company_required
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

customers_api_bp = Blueprint('customers_api', __name__, url_prefix='/api')


@customers_api_bp.route('/customers', methods=['GET'])
@login_required
@company_required
def get_customers():
    """Get all customers for the company"""
    try:
        # Filter by company
        query = Customer.query.filter_by(company_id=g.user.company_id)
        
        # Optional filter by active status
        is_active = request.args.get('is_active')
        if is_active is not None:
            query = query.filter_by(is_active=is_active.lower() == 'true')
        
        # Optional search by name or code
        search = request.args.get('search')
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                db.or_(
                    Customer.name.ilike(search_pattern),
                    Customer.code.ilike(search_pattern)
                )
            )
        
        customers = query.order_by(Customer.name).all()
        
        return jsonify({
            'success': True,
            'customers': [{
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'email': c.email,
                'phone': c.phone,
                'is_active': c.is_active,
                'project_count': len(c.projects)
            } for c in customers]
        })
    except Exception as e:
        logger.error(f"Error getting customers: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@customers_api_bp.route('/customers/<int:customer_id>', methods=['GET'])
@login_required
@company_required
def get_customer(customer_id):
    """Get a specific customer"""
    try:
        customer = Customer.query.filter_by(
            id=customer_id, 
            company_id=g.user.company_id
        ).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'code': customer.code,
                'email': customer.email,
                'phone': customer.phone,
                'address_line1': customer.address_line1,
                'address_line2': customer.address_line2,
                'city': customer.city,
                'state': customer.state,
                'postal_code': customer.postal_code,
                'country': customer.country,
                'billing_email': customer.billing_email,
                'tax_id': customer.tax_id,
                'payment_terms': customer.payment_terms,
                'notes': customer.notes,
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat() if customer.created_at else None,
                'updated_at': customer.updated_at.isoformat() if customer.updated_at else None,
                'projects': [{
                    'id': p.id,
                    'name': p.name,
                    'code': p.code,
                    'is_active': p.is_active
                } for p in customer.projects]
            }
        })
    except Exception as e:
        logger.error(f"Error getting customer {customer_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@customers_api_bp.route('/customers', methods=['POST'])
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def create_customer():
    """Create a new customer"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Customer name is required'}), 400
        
        if not data.get('code'):
            return jsonify({'success': False, 'message': 'Customer code is required'}), 400
        
        # Check if customer code already exists
        existing = Customer.query.filter_by(
            company_id=g.user.company_id,
            code=data['code']
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Customer code already exists'}), 400
        
        # Create new customer
        customer = Customer(
            name=data['name'],
            code=data['code'],
            email=data.get('email'),
            phone=data.get('phone'),
            address_line1=data.get('address_line1'),
            address_line2=data.get('address_line2'),
            city=data.get('city'),
            state=data.get('state'),
            postal_code=data.get('postal_code'),
            country=data.get('country'),
            billing_email=data.get('billing_email'),
            tax_id=data.get('tax_id'),
            payment_terms=data.get('payment_terms', 30),
            notes=data.get('notes'),
            is_active=data.get('is_active', True),
            company_id=g.user.company_id,
            created_by_id=g.user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer created successfully',
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'code': customer.code
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating customer: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@customers_api_bp.route('/customers/<int:customer_id>', methods=['PUT'])
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
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
        
        data = request.get_json()
        
        # Validate unique code if changed
        if data.get('code') and data['code'] != customer.code:
            existing = Customer.query.filter_by(
                company_id=g.user.company_id,
                code=data['code']
            ).first()
            
            if existing:
                return jsonify({'success': False, 'message': 'Customer code already exists'}), 400
        
        # Update fields
        if 'name' in data:
            customer.name = data['name']
        if 'code' in data:
            customer.code = data['code']
        if 'email' in data:
            customer.email = data['email']
        if 'phone' in data:
            customer.phone = data['phone']
        if 'address_line1' in data:
            customer.address_line1 = data['address_line1']
        if 'address_line2' in data:
            customer.address_line2 = data['address_line2']
        if 'city' in data:
            customer.city = data['city']
        if 'state' in data:
            customer.state = data['state']
        if 'postal_code' in data:
            customer.postal_code = data['postal_code']
        if 'country' in data:
            customer.country = data['country']
        if 'billing_email' in data:
            customer.billing_email = data['billing_email']
        if 'tax_id' in data:
            customer.tax_id = data['tax_id']
        if 'payment_terms' in data:
            customer.payment_terms = data['payment_terms']
        if 'notes' in data:
            customer.notes = data['notes']
        if 'is_active' in data:
            customer.is_active = data['is_active']
        
        customer.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating customer {customer_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@customers_api_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
@login_required
@company_required
@role_required(Role.SUPERVISOR)  # Supervisors and Admins can manage customers
def delete_customer(customer_id):
    """Delete a customer (soft delete by deactivating)"""
    try:
        customer = Customer.query.filter_by(
            id=customer_id,
            company_id=g.user.company_id
        ).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'}), 404
        
        # Check if customer has active projects
        active_projects = Project.query.filter_by(
            customer_id=customer_id,
            is_active=True
        ).count()
        
        if active_projects > 0:
            return jsonify({
                'success': False, 
                'message': f'Cannot delete customer with {active_projects} active projects'
            }), 400
        
        # Soft delete by deactivating
        customer.is_active = False
        customer.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Customer deactivated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting customer {customer_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@customers_api_bp.route('/customers/search', methods=['GET'])
@login_required
@company_required
def search_customers():
    """Search customers for autocomplete"""
    try:
        query = request.args.get('q', '')
        if len(query) < 2:
            return jsonify({'success': True, 'customers': []})
        
        search_pattern = f'%{query}%'
        customers = Customer.query.filter_by(
            company_id=g.user.company_id,
            is_active=True
        ).filter(
            db.or_(
                Customer.name.ilike(search_pattern),
                Customer.code.ilike(search_pattern)
            )
        ).limit(10).all()
        
        return jsonify({
            'success': True,
            'customers': [{
                'id': c.id,
                'name': c.name,
                'code': c.code,
                'label': f'{c.name} ({c.code})'
            } for c in customers]
        })
    except Exception as e:
        logger.error(f"Error searching customers: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500