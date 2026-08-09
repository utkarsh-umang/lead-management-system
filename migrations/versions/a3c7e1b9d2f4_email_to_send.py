"""add email_to_send to master_leads

Revision ID: a3c7e1b9d2f4
Revises: f1a2b3c4d5e6
Create Date: 2026-08-09 14:00:00.000000

Holds a per-lead outreach opening line, generated on demand by a named method
(see services/messages/). Single column, latest-generation-wins (regenerate
overwrites). Read by the Instantly export as the {{email_to_send}} column; NULL
until a generation is run for the lead's list. Not indexed — it's written and
exported, never filtered on.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c7e1b9d2f4'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('master_leads', sa.Column('email_to_send', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('master_leads', 'email_to_send')
