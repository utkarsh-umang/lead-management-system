"""add classify_requested flag to batches

Revision ID: c9e3f5b2a1d7
Revises: b8d2f4a1c3e5
Create Date: 2026-08-09 18:00:00.000000

UI-driven ICP classification: the "Classify" button sets classify_requested on
a list; the classification worker daemon polls for requested lists with pending
leads and drains them. "Stop" clears it. A fully-classified list naturally drops
out of the worker's queue (no pending leads), flag or not.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c9e3f5b2a1d7'
down_revision: Union[str, None] = 'b8d2f4a1c3e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'batches',
        sa.Column('classify_requested', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('batches', 'classify_requested')
