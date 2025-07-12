"""
Tax configuration model for country-specific tax rates
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, UniqueConstraint
from models import db
from datetime import datetime


class PricingType:
    """Pricing type constants"""
    NET = 'net'
    GROSS = 'gross'


class TaxConfiguration(db.Model):
    """Tax configuration for different countries"""
    __tablename__ = 'tax_configurations'
    __table_args__ = (
        UniqueConstraint('company_id', 'country_code', name='uq_company_country_tax'),
    )
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, db.ForeignKey('company.id'), nullable=False)
    
    # Country information
    country_code = Column(String(2), nullable=False)  # ISO 3166-1 alpha-2
    country_name = Column(String(100), nullable=False)
    
    # Tax rates
    standard_tax_rate = Column(Numeric(5, 2), nullable=False)  # Standard VAT/GST rate
    reduced_tax_rate = Column(Numeric(5, 2), nullable=True)   # Reduced rate (if applicable)
    tax_name = Column(String(50), nullable=False)  # e.g., "VAT", "GST", "Sales Tax"
    
    # Additional settings
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(db.DateTime, default=datetime.utcnow)
    updated_at = Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = db.relationship('Company', backref='tax_configurations')
    
    def __repr__(self):
        return f'<TaxConfiguration {self.country_name} - {self.standard_tax_rate}%>'
    
    @staticmethod
    def get_default_configurations():
        """Get default tax configurations for common countries"""
        return [
            {
                'country_code': 'US',
                'country_name': 'United States',
                'standard_tax_rate': 0,  # No federal VAT
                'tax_name': 'Sales Tax'
            },
            {
                'country_code': 'GB',
                'country_name': 'United Kingdom',
                'standard_tax_rate': 20,
                'reduced_tax_rate': 5,
                'tax_name': 'VAT'
            },
            {
                'country_code': 'DE',
                'country_name': 'Germany',
                'standard_tax_rate': 19,
                'reduced_tax_rate': 7,
                'tax_name': 'MwSt'
            },
            {
                'country_code': 'FR',
                'country_name': 'France',
                'standard_tax_rate': 20,
                'reduced_tax_rate': 5.5,
                'tax_name': 'TVA'
            },
            {
                'country_code': 'CA',
                'country_name': 'Canada',
                'standard_tax_rate': 5,  # Federal GST only
                'tax_name': 'GST'
            },
            {
                'country_code': 'AU',
                'country_name': 'Australia',
                'standard_tax_rate': 10,
                'tax_name': 'GST'
            },
            {
                'country_code': 'NL',
                'country_name': 'Netherlands',
                'standard_tax_rate': 21,
                'reduced_tax_rate': 9,
                'tax_name': 'BTW'
            },
            {
                'country_code': 'ES',
                'country_name': 'Spain',
                'standard_tax_rate': 21,
                'reduced_tax_rate': 10,
                'tax_name': 'IVA'
            },
            {
                'country_code': 'IT',
                'country_name': 'Italy',
                'standard_tax_rate': 22,
                'reduced_tax_rate': 10,
                'tax_name': 'IVA'
            },
            {
                'country_code': 'SE',
                'country_name': 'Sweden',
                'standard_tax_rate': 25,
                'reduced_tax_rate': 12,
                'tax_name': 'Moms'
            }
        ]