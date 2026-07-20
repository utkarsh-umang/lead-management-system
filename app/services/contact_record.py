"""Recording that leads were sent to Instantly.

One definition, two callers: the export endpoint (you're generating the
CSV now) and batch upload (the list was already sent before it ever
reached LMS — an import-time backfill). Both produce the same thing, an
`exports` row plus its `export_leads` members, because "who was contacted
when" has to mean one thing regardless of which door the fact came in
through.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.export import Export, ExportLead


async def record_contact_event(
    session: AsyncSession,
    lead_ids: list[uuid.UUID],
    scheduled_month: date,
    destination: str = "instantly",
) -> Export:
    """Records these leads as contacted in `scheduled_month`. Callers decide
    which leads qualify (has an email, not already exported, ...) — this
    only writes the fact. Takes ids, not ORM objects, so a caller recording
    tens of thousands of leads doesn't have to load them all first.

    Does NOT commit: the caller owns the transaction, so the contact record
    lands atomically with whatever prompted it."""
    export = Export(
        destination=destination,
        scheduled_month=scheduled_month,
        lead_count=len(lead_ids),
    )
    session.add(export)
    await session.flush()  # need export.id for the join rows
    session.add_all([ExportLead(export_id=export.id, lead_id=lead_id) for lead_id in lead_ids])
    return export
