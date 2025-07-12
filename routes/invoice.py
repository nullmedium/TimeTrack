"""
Invoice generation and management routes
"""

from flask import Blueprint, render_template, request, g, jsonify, send_file, redirect, url_for, flash
from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_
from models import db, Invoice, InvoiceLineItem, InvoiceStatus, Customer, Project, TimeEntry, CompanySettings, TaxConfiguration
from models.enums import BillingType
from routes.auth import role_required, company_required, Role
from utils.currency import get_currency_symbol, format_money
from routes.billing import get_billing_data
import calendar
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

invoice_bp = Blueprint('invoice', __name__, url_prefix='/invoices')


@invoice_bp.route('/')
@role_required(Role.SUPERVISOR)
@company_required
def invoice_list():
    """List all invoices for the company"""
    # Get filter parameters
    status = request.args.get('status', 'all')
    customer_id = request.args.get('customer_id', type=int)
    
    # Base query
    query = Invoice.query.filter_by(company_id=g.user.company_id)
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    
    # Get invoices
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    
    # Update overdue status
    for invoice in invoices:
        if invoice.is_overdue and invoice.status == InvoiceStatus.SENT:
            invoice.status = InvoiceStatus.OVERDUE
    db.session.commit()
    
    # Get customers for filter
    customers = Customer.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).order_by(Customer.name).all()
    
    # Get company settings
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency_symbol = get_currency_symbol(company_settings.default_currency)
    
    return render_template('invoice_list.html',
                         title='Invoices',
                         invoices=invoices,
                         customers=customers,
                         selected_status=status,
                         selected_customer_id=customer_id,
                         currency_symbol=currency_symbol,
                         InvoiceStatus=InvoiceStatus,
                         format_money=format_money)


@invoice_bp.route('/new', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def new_invoice():
    """Create new invoice from billing data"""
    if request.method == 'POST':
        # Get form data
        customer_id = request.form.get('customer_id', type=int)
        period_start = datetime.strptime(request.form.get('period_start'), '%Y-%m-%d').date()
        period_end = datetime.strptime(request.form.get('period_end'), '%Y-%m-%d').date()
        invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
        due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        tax_configuration_id = request.form.get('tax_configuration_id', type=int)
        notes = request.form.get('notes')
        terms = request.form.get('terms')
        
        # Get company settings
        company_settings = CompanySettings.get_or_create(g.user.company_id)
        
        # Create invoice
        invoice = Invoice(
            company_id=g.user.company_id,
            customer_id=customer_id,
            invoice_date=invoice_date,
            due_date=due_date,
            period_start=period_start,
            period_end=period_end,
            status=InvoiceStatus.DRAFT,
            currency=company_settings.default_currency,
            pricing_type=company_settings.pricing_type,
            tax_configuration_id=tax_configuration_id or company_settings.default_tax_configuration_id,
            notes=notes,
            terms=terms
        )
        
        # If tax configuration is set, use its values
        if invoice.tax_configuration_id:
            tax_config = TaxConfiguration.query.get(invoice.tax_configuration_id)
            if tax_config:
                invoice.tax_rate = tax_config.standard_tax_rate
                invoice.tax_name = tax_config.tax_name
        
        # Generate invoice number
        invoice.generate_invoice_number()
        
        db.session.add(invoice)
        db.session.flush()  # Get invoice ID
        
        # Get billing data for the period
        customer = Customer.query.get(customer_id)
        project_ids = [p.id for p in customer.projects if p.is_active]
        
        billing_data = get_billing_data(
            company_id=g.user.company_id,
            start_date=period_start,
            end_date=period_end
        )
        
        # Create line items from billing data
        for proj_id, proj_data in billing_data['by_project'].items():
            if proj_id in project_ids and proj_data['billable_hours'] > 0:
                project = proj_data['project']
                
                # Create line item based on billing type
                from decimal import Decimal
                if project.billing_type == BillingType.DAILY_RATE:
                    # For daily rate, convert hours to days
                    days = proj_data['billable_hours'] / 8.0
                    line_item = InvoiceLineItem(
                        invoice_id=invoice.id,
                        description=f"{project.name} - {days:.2f} days ({proj_data['billable_hours']:.2f} hours)",
                        quantity=Decimal(str(days)),
                        unit_price=Decimal(str(project.daily_rate or 0)),
                        project_id=project.id
                    )
                else:
                    # Hourly rate
                    line_item = InvoiceLineItem(
                        invoice_id=invoice.id,
                        description=f"{project.name} - {proj_data['billable_hours']:.2f} hours",
                        quantity=Decimal(str(proj_data['billable_hours'])),
                        unit_price=Decimal(str(project.hourly_rate or 0)),
                        project_id=project.id
                    )
                line_item.calculate_amount()
                db.session.add(line_item)
        
        # Calculate totals
        invoice.calculate_totals()
        db.session.commit()
        
        flash('Invoice created successfully', 'success')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))
    
    # GET request - show form
    customers = Customer.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).order_by(Customer.name).all()
    
    # Get company settings and tax configurations
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency = company_settings.default_currency or 'USD'
    currency_symbol = get_currency_symbol(currency)
    
    # Get available tax configurations
    tax_configurations = TaxConfiguration.query.filter_by(
        company_id=g.user.company_id,
        is_active=True
    ).order_by(TaxConfiguration.country_name).all()
    
    # Default dates
    today = date.today()
    period_start = date(today.year, today.month, 1)
    _, last_day = calendar.monthrange(today.year, today.month)
    period_end = date(today.year, today.month, last_day)
    invoice_date = today
    due_date = today + timedelta(days=30)
    
    return render_template('invoice_form.html',
                         title='New Invoice',
                         customers=customers,
                         period_start=period_start,
                         period_end=period_end,
                         invoice_date=invoice_date,
                         due_date=due_date,
                         currency=currency,
                         currency_symbol=currency_symbol,
                         tax_configurations=tax_configurations,
                         company_settings=company_settings)


@invoice_bp.route('/<int:invoice_id>')
@role_required(Role.SUPERVISOR)
@company_required
def view_invoice(invoice_id):
    """View invoice details"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    # Get company settings
    company_settings = CompanySettings.get_or_create(g.user.company_id)
    currency_symbol = get_currency_symbol(invoice.currency)
    
    # Get company details
    company = g.user.company
    
    return render_template('invoice_view.html',
                         title=f'Invoice {invoice.invoice_number}',
                         invoice=invoice,
                         company=company,
                         currency_symbol=currency_symbol,
                         InvoiceStatus=InvoiceStatus,
                         format_money=format_money,
                         today=date.today())


@invoice_bp.route('/<int:invoice_id>/edit', methods=['GET', 'POST'])
@role_required(Role.SUPERVISOR)
@company_required
def edit_invoice(invoice_id):
    """Edit invoice (only if draft)"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id,
        status=InvoiceStatus.DRAFT
    ).first_or_404()
    
    if request.method == 'POST':
        # Update invoice details
        invoice.invoice_date = datetime.strptime(request.form.get('invoice_date'), '%Y-%m-%d').date()
        invoice.due_date = datetime.strptime(request.form.get('due_date'), '%Y-%m-%d').date()
        invoice.tax_rate = request.form.get('tax_rate', type=float)
        invoice.notes = request.form.get('notes')
        invoice.terms = request.form.get('terms')
        
        # Update line items if provided
        line_items_data = request.form.getlist('line_items')
        # Process line items update logic here
        
        # Recalculate totals
        invoice.calculate_totals()
        db.session.commit()
        
        flash('Invoice updated successfully', 'success')
        return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))
    
    # GET request
    currency_symbol = get_currency_symbol(invoice.currency)
    
    return render_template('invoice_edit.html',
                         title=f'Edit Invoice {invoice.invoice_number}',
                         invoice=invoice,
                         currency_symbol=currency_symbol,
                         format_money=format_money)


@invoice_bp.route('/<int:invoice_id>/pdf')
@role_required(Role.SUPERVISOR)
@company_required
def download_invoice_pdf(invoice_id):
    """Generate and download invoice PDF"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    # Create PDF
    pdf_buffer = generate_invoice_pdf(invoice)
    
    filename = f"invoice_{invoice.invoice_number}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@invoice_bp.route('/<int:invoice_id>/send', methods=['POST'])
@role_required(Role.SUPERVISOR)
@company_required
def send_invoice(invoice_id):
    """Mark invoice as sent"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id,
        status=InvoiceStatus.DRAFT
    ).first_or_404()
    
    invoice.status = InvoiceStatus.SENT
    invoice.sent_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Invoice {invoice.invoice_number} marked as sent', 'success')
    return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))


@invoice_bp.route('/<int:invoice_id>/mark-paid', methods=['POST'])
@role_required(Role.SUPERVISOR)
@company_required
def mark_invoice_paid(invoice_id):
    """Mark invoice as paid"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    invoice.status = InvoiceStatus.PAID
    invoice.paid_date = datetime.strptime(request.form.get('paid_date'), '%Y-%m-%d').date()
    invoice.payment_reference = request.form.get('payment_reference')
    db.session.commit()
    
    flash(f'Invoice {invoice.invoice_number} marked as paid', 'success')
    return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))


@invoice_bp.route('/<int:invoice_id>/cancel', methods=['POST'])
@role_required(Role.SUPERVISOR)
@company_required
def cancel_invoice(invoice_id):
    """Cancel invoice"""
    invoice = Invoice.query.filter_by(
        id=invoice_id,
        company_id=g.user.company_id
    ).first_or_404()
    
    if invoice.status == InvoiceStatus.PAID:
        flash('Cannot cancel a paid invoice', 'error')
    else:
        invoice.status = InvoiceStatus.CANCELLED
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} cancelled', 'success')
    
    return redirect(url_for('invoice.view_invoice', invoice_id=invoice.id))


def generate_invoice_pdf(invoice):
    """Generate PDF for invoice using ReportLab"""
    buffer = io.BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=30
    )
    
    # Company and customer info
    company = invoice.company
    customer = invoice.customer
    currency_symbol = get_currency_symbol(invoice.currency)
    
    # Header
    header_data = [
        [Paragraph(f"<b>{company.name}</b>", styles['Normal']), 
         Paragraph(f"<b>INVOICE</b>", title_style)]
    ]
    
    header_table = Table(header_data, colWidths=[4*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Invoice details and customer info
    info_data = [
        [Paragraph("<b>Bill To:</b>", styles['Normal']), 
         Paragraph("<b>Invoice Details:</b>", styles['Normal'])],
        [Paragraph(f"{customer.name}<br/>{customer.address_line1 or ''}<br/>"
                  f"{customer.city or ''} {customer.state or ''} {customer.postal_code or ''}", 
                  styles['Normal']),
         Paragraph(f"Invoice #: {invoice.invoice_number}<br/>"
                  f"Date: {invoice.invoice_date.strftime('%B %d, %Y')}<br/>"
                  f"Due Date: {invoice.due_date.strftime('%B %d, %Y')}<br/>"
                  f"Period: {invoice.period_start.strftime('%b %d')} - {invoice.period_end.strftime('%b %d, %Y')}", 
                  styles['Normal'])]
    ]
    
    info_table = Table(info_data, colWidths=[3.5*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.5*inch))
    
    # Line items table
    items_data = [['Description', 'Quantity', 'Rate', 'Amount']]
    
    for item in invoice.line_items:
        items_data.append([
            item.description,
            f"{item.quantity:.2f}",
            f"{currency_symbol}{item.unit_price:.2f}",
            f"{currency_symbol}{item.amount:.2f}"
        ])
    
    # Add subtotal, tax, and total
    items_data.extend([
        ['', '', 'Subtotal:', f"{currency_symbol}{invoice.subtotal:.2f}"],
        ['', '', f'Tax ({invoice.tax_rate}%):', f"{currency_symbol}{invoice.tax_amount:.2f}"],
        ['', '', Paragraph('<b>Total:</b>', styles['Normal']), 
         Paragraph(f'<b>{currency_symbol}{invoice.total_amount:.2f}</b>', styles['Normal'])]
    ])
    
    items_table = Table(items_data, colWidths=[3.5*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -4), 9),
        ('ALIGN', (1, 1), (1, -4), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
        
        # Grid
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        
        # Summary rows
        ('LINEABOVE', (2, -3), (-1, -3), 1, colors.black),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(items_table)
    
    # Notes and terms
    if invoice.notes:
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("<b>Notes:</b>", styles['Normal']))
        story.append(Paragraph(invoice.notes, styles['Normal']))
    
    if invoice.terms:
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("<b>Terms:</b>", styles['Normal']))
        story.append(Paragraph(invoice.terms, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer


@invoice_bp.route('/api/preview-billing-data')
@role_required(Role.SUPERVISOR)
@company_required
def preview_billing_data():
    """Preview billing data for invoice creation"""
    print(f"Preview billing data called with args: {request.args}")
    try:
        customer_id = request.args.get('customer_id', type=int)
        period_start_str = request.args.get('period_start')
        period_end_str = request.args.get('period_end')
        
        if not customer_id or not period_start_str or not period_end_str:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
        period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
        
        # Get customer and their projects
        customer = Customer.query.filter_by(
            id=customer_id,
            company_id=g.user.company_id
        ).first()
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
            
        project_ids = [p.id for p in customer.projects if p.is_active]
        
        # Get billing data
        billing_data = get_billing_data(
            company_id=g.user.company_id,
            start_date=period_start,
            end_date=period_end
        )
        
        # Filter for customer's projects
        preview_data = {
            'projects': [],
            'total_hours': 0,
            'total_amount': 0
        }
        
        for proj_id, proj_data in billing_data['by_project'].items():
            if proj_id in project_ids and proj_data['billable_hours'] > 0:
                project = proj_data['project']
                
                if project.billing_type == BillingType.DAILY_RATE:
                    # For daily rate projects
                    days = proj_data['billable_hours'] / 8.0
                    preview_data['projects'].append({
                        'name': project.name,
                        'hours': float(proj_data['billable_hours']),
                        'days': float(days),
                        'rate': float(project.daily_rate or 0),
                        'rate_type': 'daily',
                        'amount': float(proj_data['total_amount'])
                    })
                else:
                    # For hourly rate projects
                    preview_data['projects'].append({
                        'name': project.name,
                        'hours': float(proj_data['billable_hours']),
                        'rate': float(project.hourly_rate or 0),
                        'rate_type': 'hourly',
                        'amount': float(proj_data['total_amount'])
                    })
                preview_data['total_hours'] += proj_data['billable_hours']
                preview_data['total_amount'] += proj_data['total_amount']
        
        # Convert totals to float for JSON serialization
        preview_data['total_hours'] = float(preview_data['total_hours'])
        preview_data['total_amount'] = float(preview_data['total_amount'])
        
        return jsonify(preview_data)
    except Exception as e:
        print(f"Error in preview_billing_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500