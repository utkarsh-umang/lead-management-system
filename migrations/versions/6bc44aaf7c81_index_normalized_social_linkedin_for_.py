"""index normalized social_linkedin for dedup

Revision ID: 6bc44aaf7c81
Revises: aea2243dc6a8
Create Date: 2026-07-20 13:07:27.892351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '6bc44aaf7c81'
down_revision: Union[str, None] = 'aea2243dc6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Must match _sql_normalized_linkedin() in app/services/dedup.py character
# for character — Postgres only uses a functional index when the query
# expression is identical to the indexed one. Without it the LinkedIn dedup
# tier seq-scans master_leads once per ingested row (measured: 9ms/row at
# 31k leads, growing with the table — ~11 min of pure scanning on a 36k-row
# Apollo upload).
_NORMALIZED_LINKEDIN = (
    "rtrim("
    "replace(replace(replace(lower(trim(social_linkedin)),"
    "'https://',''),'http://',''),'www.','')"
    ", '/')"
)


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX ix_master_leads_normalized_linkedin "
        f"ON master_leads (({_NORMALIZED_LINKEDIN}))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_master_leads_normalized_linkedin")
