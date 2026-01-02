"""Add DND fields to User model

Revision ID: 20260102_add_dnd
Revises: 20260101_whatsapp
Create Date: 2026-01-02 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260102_add_dnd'
down_revision = '20260101_whatsapp'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add dnd_enabled and dnd_until to users table
    op.add_column('users', sa.Column('dnd_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('dnd_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'dnd_until')
    op.drop_column('users', 'dnd_enabled')
