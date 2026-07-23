"""add lead_tag and identity_key to master_leads

Revision ID: b1f7c2d4e9a0
Revises: 6bc44aaf7c81
Create Date: 2026-07-23 00:00:00.000000

lead_tag: cross-source lead-quality tag (podscan sets prospect/public_figure/
host_or_regular). identity_key: normalized name+company, the tier-5 dedup key
(see app/services/identity.py). Both indexed — lead_tag for UI filtering,
identity_key so the dedup tier is an index lookup, not a scan.

Backfilling identity_key for the 36k existing name+company leads is a separate
Python step (scripts/backfill_identity_key.py) so the stored key uses the exact
same normalization as ingestion — never a hand-written SQL twin that could drift.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'b1f7c2d4e9a0'
down_revision: Union[str, None] = '6bc44aaf7c81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'master_leads',
        sa.Column('lead_tag', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        'master_leads',
        sa.Column('identity_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index('ix_master_leads_lead_tag', 'master_leads', ['lead_tag'])
    op.create_index('ix_master_leads_identity_key', 'master_leads', ['identity_key'])


def downgrade() -> None:
    op.drop_index('ix_master_leads_identity_key', table_name='master_leads')
    op.drop_index('ix_master_leads_lead_tag', table_name='master_leads')
    op.drop_column('master_leads', 'identity_key')
    op.drop_column('master_leads', 'lead_tag')
