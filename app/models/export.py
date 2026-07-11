"""System of record for outbound contact: one Export row per "I set these
leads up in Instantly for <month>" event, with the member leads in
ExportLead. "When was this lead last contacted" is derived from here —
max(scheduled_month) across its export rows — never stored on the lead."""

import uuid
from datetime import date

from sqlmodel import Field

from app.db.base import Base


class Export(Base, table=True):
    __tablename__ = "exports"

    destination: str = Field(default="instantly", index=True)
    # Contact granularity is deliberately month, not day — stored as the
    # first of the month so it stays a real date (sortable, comparable).
    scheduled_month: date = Field(index=True)
    lead_count: int = Field(default=0)


class ExportLead(Base, table=True):
    __tablename__ = "export_leads"

    export_id: uuid.UUID = Field(foreign_key="exports.id", index=True)
    lead_id: uuid.UUID = Field(foreign_key="master_leads.id", index=True)
