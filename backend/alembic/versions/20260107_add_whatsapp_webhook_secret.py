"""add whatsapp webhook secret

Revision ID: 20260107_webhook_secret
Revises: 20260106_unification
Create Date: 2026-01-07 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260107_webhook_secret'
down_revision = '20260106_unification'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add whatsapp_webhook_secret column to tenants table
    op.add_column('tenants',
        sa.Column('whatsapp_webhook_secret', sa.String(length=128), nullable=True)
    )

def downgrade() -> None:
    # Remove whatsapp_webhook_secret column from tenants table
    op.drop_column('tenants', 'whatsapp_webhook_secret')
