"""Add daily rate billing and tax configuration

Revision ID: add_daily_rate_tax_config
Revises: add_invoice_models
Create Date: 2025-07-11 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_daily_rate_tax_config'
down_revision = 'add_invoice_models'
branch_labels = None
depends_on = None


def upgrade():
    # Create tax_configurations table
    op.create_table('tax_configurations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('country_code', sa.String(length=2), nullable=False),
        sa.Column('country_name', sa.String(length=100), nullable=False),
        sa.Column('standard_tax_rate', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('reduced_tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('tax_name', sa.String(length=50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'country_code', name='uq_company_country_tax')
    )
    
    # Create index for performance
    op.create_index(op.f('ix_tax_configurations_company_id'), 'tax_configurations', ['company_id'], unique=False)
    
    # Add daily_rate to project table
    op.add_column('project', sa.Column('daily_rate', sa.Numeric(precision=10, scale=2), nullable=True))
    
    # Add pricing settings to company_settings
    op.add_column('company_settings', sa.Column('pricing_type', sa.String(length=10), nullable=True))
    op.add_column('company_settings', sa.Column('default_tax_configuration_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint after column is created
    op.create_foreign_key('fk_company_settings_tax_config', 'company_settings', 'tax_configurations', ['default_tax_configuration_id'], ['id'])
    
    # Update invoices table to support tax configuration
    op.add_column('invoices', sa.Column('tax_configuration_id', sa.Integer(), nullable=True))
    op.add_column('invoices', sa.Column('tax_name', sa.String(length=50), nullable=True))
    op.add_column('invoices', sa.Column('pricing_type', sa.String(length=10), nullable=True))
    
    # Add foreign key constraint for tax configuration
    op.create_foreign_key('fk_invoices_tax_config', 'invoices', 'tax_configurations', ['tax_configuration_id'], ['id'])
    
    # Set default values for existing data
    op.execute("UPDATE company_settings SET pricing_type = 'net' WHERE pricing_type IS NULL")
    op.execute("UPDATE invoices SET pricing_type = 'net' WHERE pricing_type IS NULL")


def downgrade():
    # Drop foreign key constraints first
    op.drop_constraint('fk_invoices_tax_config', 'invoices', type_='foreignkey')
    op.drop_constraint('fk_company_settings_tax_config', 'company_settings', type_='foreignkey')
    
    # Remove columns from invoices
    op.drop_column('invoices', 'pricing_type')
    op.drop_column('invoices', 'tax_name')
    op.drop_column('invoices', 'tax_configuration_id')
    
    # Remove columns from company_settings
    op.drop_column('company_settings', 'default_tax_configuration_id')
    op.drop_column('company_settings', 'pricing_type')
    
    # Remove daily_rate from project
    op.drop_column('project', 'daily_rate')
    
    # Drop index and table
    op.drop_index(op.f('ix_tax_configurations_company_id'), table_name='tax_configurations')
    op.drop_table('tax_configurations')