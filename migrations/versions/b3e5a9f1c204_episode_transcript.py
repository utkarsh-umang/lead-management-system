"""add episode_transcript to master_leads

Revision ID: b3e5a9f1c204
Revises: d7a4e2c9b1f6
Create Date: 2026-08-14 10:00:00.000000

Caches the full Podscan episode transcript for a podcast-guest lead. Transcripts
are per-EPISODE, not per-lead, so the fetch dedups on episode_id and fans one
transcript out to every guest who appeared on that episode (see
services/messages/transcript_store.py). Stored so `transcript_opener` reads it
locally instead of re-hitting the rate-limited Podscan API on every generation.
Nullable, unindexed (written + read whole, never filtered on); NULL until a
fetch is run for the lead's list.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e5a9f1c204"
down_revision: str | None = "d7a4e2c9b1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("master_leads", sa.Column("episode_transcript", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("master_leads", "episode_transcript")
