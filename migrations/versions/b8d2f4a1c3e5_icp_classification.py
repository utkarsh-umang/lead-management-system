"""add ICP / industry classification columns to master_leads

Revision ID: b8d2f4a1c3e5
Revises: a3c7e1b9d2f4
Create Date: 2026-08-09 16:00:00.000000

Website-content classification (services/classifiers/, run by the ai-agents ICP
classifier). For every lead: `classified_industry` (a controlled-taxonomy bucket,
the LLM may propose a new label when none fit) and `icp_confidence` (0-100
paid-advertising-agency score — accept segment is >= 60). Both indexed because
they ARE the segment keys. Distinct from the source-provided `industry` (Apollo's
loose tag) — this is inferred from the actual site.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8d2f4a1c3e5'
down_revision: Union[str, None] = 'a3c7e1b9d2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('master_leads', sa.Column('classified_industry', sa.String(), nullable=True))
    op.add_column('master_leads', sa.Column('icp_confidence', sa.Integer(), nullable=True))
    op.add_column('master_leads', sa.Column('icp_reasoning', sa.String(), nullable=True))
    op.add_column('master_leads', sa.Column('icp_source', sa.String(), nullable=True))
    op.add_column('master_leads', sa.Column('icp_classified_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_master_leads_classified_industry'), 'master_leads', ['classified_industry'])
    op.create_index(op.f('ix_master_leads_icp_confidence'), 'master_leads', ['icp_confidence'])


def downgrade() -> None:
    op.drop_index(op.f('ix_master_leads_icp_confidence'), table_name='master_leads')
    op.drop_index(op.f('ix_master_leads_classified_industry'), table_name='master_leads')
    op.drop_column('master_leads', 'icp_classified_at')
    op.drop_column('master_leads', 'icp_source')
    op.drop_column('master_leads', 'icp_reasoning')
    op.drop_column('master_leads', 'icp_confidence')
    op.drop_column('master_leads', 'classified_industry')
