"""add Instascraper Google Maps identity columns

Revision ID: d7a4e2c9b1f6
Revises: c9e3f5b2a1d7
Create Date: 2026-08-09 18:00:00.000000

Google Maps place ID is the stable identity for Instascraper company listings.
The same business can appear in overlapping city searches with different Maps
URLs, so the place ID is indexed for deterministic deduplication. The original
listing URL is retained separately for human navigation.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7a4e2c9b1f6"
down_revision: str | None = "c9e3f5b2a1d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("master_leads", sa.Column("google_place_id", sa.String(), nullable=True))
    op.add_column("master_leads", sa.Column("google_maps_url", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_master_leads_google_place_id"),
        "master_leads",
        ["google_place_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_master_leads_google_place_id"), table_name="master_leads")
    op.drop_column("master_leads", "google_maps_url")
    op.drop_column("master_leads", "google_place_id")
