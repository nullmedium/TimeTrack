"""Add password reset fields to user model

Revision ID: 85d490db548b
Revises: c72667903a91
Create Date: 2025-07-13 12:24:14.261548

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '85d490db548b'
down_revision = 'c72667903a91'
branch_labels = None
depends_on = None


def upgrade():
    # Add password reset fields to user table
    op.add_column('user', sa.Column('password_reset_token', sa.String(length=100), nullable=True))
    op.add_column('user', sa.Column('password_reset_expiry', sa.DateTime(), nullable=True))
    op.create_unique_constraint('uq_user_password_reset_token', 'user', ['password_reset_token'])


def downgrade():
    # Remove password reset fields from user table
    op.drop_constraint('uq_user_password_reset_token', 'user', type_='unique')
    op.drop_column('user', 'password_reset_expiry')
    op.drop_column('user', 'password_reset_token')