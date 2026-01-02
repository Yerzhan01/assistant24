"""Add segment and last_interaction to contacts

Revision ID: 20260102_add_contact_crm
Revises: 
Create Date: 2026-01-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260102_add_contact_crm'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add segment column with default value
    op.add_column('contacts', sa.Column('segment', sa.String(50), nullable=True, server_default='other'))
    
    # Add last_interaction column
    op.add_column('contacts', sa.Column('last_interaction', sa.DateTime(timezone=True), nullable=True))
    
    # Create index on segment for faster filtering
    op.create_index('ix_contacts_segment', 'contacts', ['segment'])


def downgrade() -> None:
    op.drop_index('ix_contacts_segment', 'contacts')
    op.drop_column('contacts', 'last_interaction')
    op.drop_column('contacts', 'segment')
