"""Traces a canonical lead back to every raw row/batch that contributed to
it. A lead can accumulate multiple rows here over time as it's re-seen
across different sources — that's what makes dedup provenance auditable."""

import uuid

from sqlmodel import Field

from app.db.base import Base


class LeadSource(Base, table=True):
    __tablename__ = "lead_sources"

    lead_id: uuid.UUID = Field(foreign_key="master_leads.id", index=True)
    batch_id: uuid.UUID = Field(foreign_key="batches.id", index=True)
    row_id: uuid.UUID = Field(foreign_key="raw_rows.id")
