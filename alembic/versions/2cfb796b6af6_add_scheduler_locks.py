"""add_scheduler_locks

Revision ID: 2cfb796b6af6
Revises: 5586f31a0822
Create Date: 2026-04-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cfb796b6af6'
down_revision: Union[str, Sequence[str], None] = '5586f31a0822'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('scheduler_locks',
    sa.Column('job_id', sa.String(), nullable=False),
    sa.Column('holder_id', sa.String(), nullable=False),
    sa.Column('acquired_at', sa.DateTime(), server_default='now()', nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('job_id')
    )
    op.create_index(op.f('ix_scheduler_locks_expires_at'), 'scheduler_locks', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_scheduler_locks_expires_at'), table_name='scheduler_locks')
    op.drop_table('scheduler_locks')
