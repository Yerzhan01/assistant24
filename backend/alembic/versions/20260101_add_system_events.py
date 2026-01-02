
"""add system events

Revision ID: 20260101_sys_events
Revises: 20260101_add_whatsapp_instances
Create Date: 2026-01-01 23:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260101_sys_events'
down_revision = '20260101_add_whatsapp_instances'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('system_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('reference_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_events_event_type'), 'system_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_system_events_tenant_id'), 'system_events', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_system_events_tenant_id'), table_name='system_events')
    op.drop_index(op.f('ix_system_events_event_type'), table_name='system_events')
    op.drop_table('system_events')
