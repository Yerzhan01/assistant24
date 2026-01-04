"""task system v2

Revision ID: 20260105_task_v2
Revises: 20260102_add_dnd
Create Date: 2026-01-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260105_task_v2'
down_revision = '20260101_sys_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create task_reminders table
    op.create_table('task_reminders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('remind_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('is_sent', sa.Boolean(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_reminders_task_id'), 'task_reminders', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_reminders_remind_at'), 'task_reminders', ['remind_at'], unique=False)
    op.create_index(op.f('ix_task_reminders_is_sent'), 'task_reminders', ['is_sent'], unique=False)

    # 2. Add columns to tasks
    op.add_column('tasks', sa.Column('parent_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_tasks_parent_id'), 'tasks', ['parent_id'], unique=False)
    # Note: Explicitly naming the FK constraint is good practice but auto-naming works too
    op.create_foreign_key(None, 'tasks', 'tasks', ['parent_id'], ['id'], ondelete='CASCADE')

    op.add_column('tasks', sa.Column('recurrence_rule', sa.String(length=255), nullable=True))
    op.add_column('tasks', sa.Column('tags', sa.String(length=500), nullable=True))
    op.add_column('tasks', sa.Column('is_supervisor_mode', sa.Boolean(), server_default='false', nullable=False))
    
    # 3. Add completed_at to tasks



def downgrade() -> None:

    op.drop_column('tasks', 'is_supervisor_mode')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'recurrence_rule')
    op.drop_constraint(None, 'tasks', type_='foreignkey')
    op.drop_index(op.f('ix_tasks_parent_id'), table_name='tasks')
    op.drop_column('tasks', 'parent_id')
    op.drop_index(op.f('ix_task_reminders_is_sent'), table_name='task_reminders')
    op.drop_index(op.f('ix_task_reminders_remind_at'), table_name='task_reminders')
    op.drop_index(op.f('ix_task_reminders_task_id'), table_name='task_reminders')
    op.drop_table('task_reminders')
