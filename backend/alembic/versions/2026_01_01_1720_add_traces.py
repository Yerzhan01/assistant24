"""Create traces table for request tracing

Revision ID: 2026_01_01_1720_add_traces
Revises: 
Create Date: 2026-01-01 17:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_01_1720_add_traces'
down_revision = None  # Update this if you have a previous migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create traces table for debugging AI requests
    op.create_table(
        'traces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('trace_id', sa.String(12), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('source', sa.String(20), nullable=True, server_default='web'),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('steps', sa.JSON(), nullable=True),
        sa.Column('gemini_model', sa.String(50), nullable=True),
        sa.Column('gemini_prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('gemini_response_tokens', sa.Integer(), nullable=True),
        sa.Column('gemini_raw_response', sa.Text(), nullable=True),
        sa.Column('classified_intents', sa.JSON(), nullable=True),
        sa.Column('ai_reasoning', sa.Text(), nullable=True),
        sa.Column('final_response', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('total_duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for faster lookups
    op.create_index('ix_traces_trace_id', 'traces', ['trace_id'], unique=True)
    op.create_index('ix_traces_tenant_id', 'traces', ['tenant_id'])
    op.create_index('ix_traces_created_at', 'traces', ['created_at'])
    op.create_index('ix_traces_success', 'traces', ['success'])


def downgrade() -> None:
    op.drop_index('ix_traces_success', table_name='traces')
    op.drop_index('ix_traces_created_at', table_name='traces')
    op.drop_index('ix_traces_tenant_id', table_name='traces')
    op.drop_index('ix_traces_trace_id', table_name='traces')
    op.drop_table('traces')
