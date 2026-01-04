"""unification

Revision ID: 20260106_unification
Revises: 20260105_task_v2
Create Date: 2026-01-06 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260106_unification'
down_revision = '20260105_task_v2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create interactions table
    op.create_table('interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )
    op.create_index(op.f('ix_interactions_tenant_id'), 'interactions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_interactions_user_id'), 'interactions', ['user_id'], unique=False)
    op.create_index(op.f('ix_interactions_session_id'), 'interactions', ['session_id'], unique=False)
    op.create_index(op.f('ix_interactions_created_at'), 'interactions', ['created_at'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_interactions_created_at'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_session_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_user_id'), table_name='interactions')
    op.drop_index(op.f('ix_interactions_tenant_id'), table_name='interactions')
    op.drop_table('interactions')
