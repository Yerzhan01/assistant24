"""add whatsapp instances table

Revision ID: 20260101_whatsapp
Revises: 
Create Date: 2026-01-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260101_whatsapp'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create whatsapp_instances table
    op.create_table(
        'whatsapp_instances',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('instance_id', sa.String(), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('available', 'assigned', 'expired', name='instancestatus'), nullable=False),
        sa.Column('assigned_to_tenant_id', sa.String(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assigned_to_tenant_id'], ['tenants.id'], ),
        sa.UniqueConstraint('instance_id')
    )
    op.create_index(op.f('ix_whatsapp_instances_id'), 'whatsapp_instances', ['id'], unique=False)
    op.create_index(op.f('ix_whatsapp_instances_instance_id'), 'whatsapp_instances', ['instance_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_whatsapp_instances_instance_id'), table_name='whatsapp_instances')
    op.drop_index(op.f('ix_whatsapp_instances_id'), table_name='whatsapp_instances')
    op.drop_table('whatsapp_instances')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS instancestatus')
