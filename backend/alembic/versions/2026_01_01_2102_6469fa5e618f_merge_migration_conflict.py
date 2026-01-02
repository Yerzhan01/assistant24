"""merge_migration_conflict

Revision ID: 6469fa5e618f
Revises: c061f32ba806, 2026_01_01_1720_add_traces
Create Date: 2026-01-01 21:02:46.719901+05:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6469fa5e618f'
down_revision: Union[str, None] = ('c061f32ba806', '2026_01_01_1720_add_traces')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
