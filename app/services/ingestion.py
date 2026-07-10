"""Orchestrates one batch: apply the mapping spec to every raw row, dedup/
upsert into master_leads, and record full provenance (raw_rows,
lead_sources). This is the Executor from Ingestion Pipeline.md — the
deterministic path a fingerprint hit always takes, no LLM involved."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.raw_row import RawRow
from app.services.dedup import upsert_lead
from app.services.mapping.interpreter import apply_mapping


def _is_empty_row(raw_row: dict[str, Any]) -> bool:
    return not any(str(v).strip() for v in raw_row.values() if v is not None)


async def run_ingestion(
    session: AsyncSession, batch: Batch, mapping_spec: dict, rows: list[dict]
) -> Batch:
    batch.row_count_raw = len(rows)

    for index, raw_row in enumerate(rows):
        if _is_empty_row(raw_row):
            db_raw_row = RawRow(
                batch_id=batch.id,
                row_index=index,
                raw_data=raw_row,
                validation_status="quarantined",
                quarantine_reason="empty row",
            )
            session.add(db_raw_row)
            batch.row_count_quarantined += 1
            continue

        canonical = apply_mapping(mapping_spec, raw_row)

        db_raw_row = RawRow(
            batch_id=batch.id,
            row_index=index,
            raw_data=raw_row,
            validation_status="valid",
        )
        session.add(db_raw_row)
        await session.flush()  # get db_raw_row.id

        lead, is_new = await upsert_lead(session, canonical)

        session.add(LeadSource(lead_id=lead.id, batch_id=batch.id, row_id=db_raw_row.id))

        batch.row_count_valid += 1
        if is_new:
            batch.row_count_new_leads += 1
        else:
            batch.row_count_merged += 1
        if canonical.get("email"):
            batch.row_count_with_email += 1

    batch.status = "completed"
    session.add(batch)
    await session.commit()
    await session.refresh(batch)
    return batch
