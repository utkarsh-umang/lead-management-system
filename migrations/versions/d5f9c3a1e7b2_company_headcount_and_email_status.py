"""add company_headcount + email_status to master_leads

Revision ID: d5f9c3a1e7b2
Revises: c4e8a1b2f3d6
Create Date: 2026-08-04 10:00:00.000000

Promotes two high-value Apollo fields from raw_rows to first-class columns so
they're queryable/filterable/exportable:
company_headcount (int): Apollo "# Employees" — a primary targeting axis.
email_status (str): Apollo "Email Status" (verified/extrapolated/unavailable) —
the source's own deliverability verdict, distinct from our finder's confidence.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5f9c3a1e7b2'
down_revision: Union[str, None] = 'c4e8a1b2f3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('master_leads', sa.Column('company_headcount', sa.Integer(), nullable=True))
    op.add_column('master_leads', sa.Column('email_status', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('master_leads', 'email_status')
    op.drop_column('master_leads', 'company_headcount')
