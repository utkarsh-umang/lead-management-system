"""Append-only enrichment attempt log — the email finder's work queue is
derived from this, never from a status column on the lead. "Not found" is
always "not found at a specific cost tier": a low-cost miss stays eligible
for a deliberate high-cost run later, and nothing ever gets re-paid at a
tier it already ran at. created_at is the attempt timestamp."""

import uuid

from sqlmodel import Field

from app.db.base import Base


class EnrichmentAttempt(Base, table=True):
    __tablename__ = "enrichment_attempts"

    lead_id: uuid.UUID = Field(foreign_key="master_leads.id", index=True)
    type: str = Field(default="email", index=True)  # future: other enrichers
    cost_mode: str = Field(index=True)  # low | high
    status: str  # found | not_found | failed
    value: str | None = Field(default=None)  # the email, when found
    provider: str | None = Field(default=None)  # e.g. "email_finder@ai-agents-service"
    cost_incurred: float | None = Field(default=None)
