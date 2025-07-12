"""
Invoice model for generating customer invoices
"""

from sqlalchemy import Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from models import db
from datetime import datetime
from models.enums import BillingType


class InvoiceStatus:
    """Invoice status constants"""
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    CANCELLED = 'cancelled'
    OVERDUE = 'overdue'


class Invoice(db.Model):
    """Invoice model for billing customers"""
    __tablename__ = 'invoices'
    __table_args__ = (
        UniqueConstraint('company_id', 'invoice_number', name='uq_company_invoice_number'),
    )
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    customer_id = Column(Integer, ForeignKey('customer.id'), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    
    # Dates
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Status and amounts
    status = Column(String(20), nullable=False, default=InvoiceStatus.DRAFT)
    currency = Column(String(3), nullable=False, default='USD')
    
    # Tax configuration
    tax_configuration_id = Column(Integer, ForeignKey('tax_configurations.id'), nullable=True)
    tax_rate = Column(Numeric(5, 2), nullable=True)  # Percentage (can override tax config)
    tax_name = Column(String(50), nullable=True)  # e.g., "VAT", "GST"
    
    # Pricing type
    pricing_type = Column(String(10), nullable=False, default='net')  # 'net' or 'gross'
    
    # Amounts
    subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Payment information
    paid_date = Column(Date, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    
    # Additional fields
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship('Company', backref='invoices')
    customer = relationship('Customer', backref='invoices')
    line_items = relationship('InvoiceLineItem', backref='invoice', cascade='all, delete-orphan')
    tax_configuration = relationship('TaxConfiguration', backref='invoices')
    
    @hybrid_property
    def is_overdue(self):
        """Check if invoice is overdue"""
        if self.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return False
        return datetime.now().date() > self.due_date
    
    def calculate_totals(self):
        """Calculate invoice totals from line items"""
        from decimal import Decimal
        
        # Calculate based on pricing type
        if self.pricing_type == 'gross':
            # Gross pricing: prices include tax
            self.total_amount = sum(item.amount for item in self.line_items)
            if self.tax_rate:
                # Calculate tax amount from gross total
                tax_divisor = Decimal('1') + (Decimal(str(self.tax_rate)) / Decimal('100'))
                self.subtotal = self.total_amount / tax_divisor
                self.tax_amount = self.total_amount - self.subtotal
            else:
                self.subtotal = self.total_amount
                self.tax_amount = Decimal('0')
        else:
            # Net pricing: prices exclude tax
            self.subtotal = sum(item.amount for item in self.line_items)
            if self.tax_rate:
                self.tax_amount = self.subtotal * (Decimal(str(self.tax_rate)) / Decimal('100'))
            else:
                self.tax_amount = Decimal('0')
            self.total_amount = self.subtotal + self.tax_amount
    
    def generate_invoice_number(self):
        """Generate next invoice number for the company"""
        # Get the last invoice number for this company
        last_invoice = Invoice.query.filter_by(
            company_id=self.company_id
        ).order_by(Invoice.id.desc()).first()
        
        if last_invoice and last_invoice.invoice_number:
            # Extract number from last invoice
            try:
                # Assume format like "INV-2024-0001"
                parts = last_invoice.invoice_number.split('-')
                if len(parts) >= 3:
                    number = int(parts[-1]) + 1
                    year = datetime.now().year
                    self.invoice_number = f"INV-{year}-{number:04d}"
                else:
                    self.invoice_number = f"INV-{datetime.now().year}-0001"
            except:
                self.invoice_number = f"INV-{datetime.now().year}-0001"
        else:
            self.invoice_number = f"INV-{datetime.now().year}-0001"
    
    def to_dict(self):
        """Convert invoice to dictionary"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer.name,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'total_amount': float(self.total_amount),
            'currency': self.currency,
            'is_overdue': self.is_overdue
        }


class InvoiceLineItem(db.Model):
    """Line items for invoices"""
    __tablename__ = 'invoice_line_items'
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=False)
    
    # Line item details
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Optional references to time entries
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    project = relationship('Project')
    user = relationship('User')
    
    def calculate_amount(self):
        """Calculate line item amount"""
        from decimal import Decimal
        self.amount = Decimal(str(self.quantity)) * Decimal(str(self.unit_price))