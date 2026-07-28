"""add evidence + superseded to enrichment_attempts

Revision ID: c4e8a1b2f3d6
Revises: b1f7c2d4e9a0
Create Date: 2026-07-28 10:00:00.000000

evidence (JSONB): the candidate context the enricher gathered, so a later logic
change can re-score an attempt offline instead of re-running the search/scrape.
superseded (bool): ledger-preserving re-queue — mark an attempt superseded (the
row stays) rather than deleting it; the work queue ignores superseded attempts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c4e8a1b2f3d6'
down_revision: Union[str, None] = 'b1f7c2d4e9a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('enrichment_attempts', sa.Column('evidence', postgresql.JSONB(), nullable=True))
    op.add_column('enrichment_attempts', sa.Column('superseded', sa.Boolean(), nullable=False,
                                                   server_default=sa.false()))
    op.create_index('ix_enrichment_attempts_superseded', 'enrichment_attempts', ['superseded'])


def downgrade() -> None:
    op.drop_index('ix_enrichment_attempts_superseded', table_name='enrichment_attempts')
    op.drop_column('enrichment_attempts', 'superseded')
    op.drop_column('enrichment_attempts', 'evidence')
