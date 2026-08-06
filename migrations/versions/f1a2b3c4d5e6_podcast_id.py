"""add podcast_id to master_leads

Revision ID: f1a2b3c4d5e6
Revises: e7a2b9c4d1f8
Create Date: 2026-08-06 12:00:00.000000

Platform-native identity for the Podscan Host source (one row = one podcast).
A podcast that arrives without a brand-matched email has no email, no person,
and no name+company key, so tiers 1-5 can't anchor it and it would duplicate on
every re-pull. Podscan's stable per-podcast id (`pd_...`) is that anchor — it
dedups the list against itself and across re-pulls, exactly like
clutch_profile_url does for the agency scrape. Indexed because it's a
dedup-lookup column (dedup.py tier 7).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e7a2b9c4d1f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('master_leads', sa.Column('podcast_id', sa.String(), nullable=True))
    op.create_index(
        op.f('ix_master_leads_podcast_id'),
        'master_leads',
        ['podcast_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_master_leads_podcast_id'), table_name='master_leads')
    op.drop_column('master_leads', 'podcast_id')
