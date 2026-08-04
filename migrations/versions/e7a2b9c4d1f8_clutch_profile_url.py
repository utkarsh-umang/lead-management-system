"""add clutch_profile_url to master_leads

Revision ID: e7a2b9c4d1f8
Revises: d5f9c3a1e7b2
Create Date: 2026-08-04 12:00:00.000000

Directory-native identity for company-as-lead sources (Clutch agency scrape).
These leads have no email, no person, and no external website, so none of the
existing dedup tiers can anchor them. The Clutch profile URL is the stable
per-agency key: it dedups the list against itself and against future re-pulls,
and is the handle the later resolution step (profile -> website -> email) hangs
off. Indexed because it's a dedup-lookup column (dedup.py tier 6).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a2b9c4d1f8'
down_revision: Union[str, None] = 'd5f9c3a1e7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('master_leads', sa.Column('clutch_profile_url', sa.String(), nullable=True))
    op.create_index(
        op.f('ix_master_leads_clutch_profile_url'),
        'master_leads',
        ['clutch_profile_url'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_master_leads_clutch_profile_url'), table_name='master_leads')
    op.drop_column('master_leads', 'clutch_profile_url')
