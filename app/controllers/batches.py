"""Batch upload — the fingerprint fast path from Ingestion Pipeline.md.
A fingerprint miss returns 422: phase 3 (the agentic mapping-drafting loop)
isn't built yet, so an unknown shape needs a mapping authored by hand."""

import csv
import io
import uuid

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.mapping_function import MappingFunction
from app.models.raw_row import RawRow
from app.schemas.batch import BatchDetail, BatchSummary, QuarantinedRowOut
from app.services.enrichment_signals import notify_work
from app.services.ingestion import run_ingestion
from app.services.mapping.fingerprint import compute_fingerprint

router = APIRouter()


@router.post("/upload", response_model=BatchSummary, operation_id="upload_batch")
async def upload_batch(
    session: DbSession,
    file: UploadFile,
    source: str | None = Form(default=None),
    # When true, this upload's NEW leads are held out of the email finder
    # queue until released from the source page (merged leads keep their
    # existing eligibility).
    enrichment_hold: bool = Form(default=False),
) -> BatchSummary:
    raw_bytes = await file.read()
    text = raw_bytes.decode("utf-8-sig")  # -sig strips a BOM if present
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not reader.fieldnames:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV has no header row")

    fingerprint = compute_fingerprint(reader.fieldnames)
    result = await session.execute(
        select(MappingFunction).where(MappingFunction.fingerprint == fingerprint)
    )
    mapping = result.scalars().first()

    if mapping is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Unrecognized CSV shape — no registered mapping function for this fingerprint. "
            "The agentic mapping-drafting layer (phase 3) isn't built yet; "
            "this shape needs a hand-authored mapping spec.",
        )

    # The fingerprint decides HOW to parse (which mapping spec); the source
    # label decides WHAT LIST this is. They default to the same thing, but
    # two different lists exported from the same tool share a fingerprint —
    # an explicit source keeps them distinguishable in provenance/stats.
    source_label = (source or "").strip() or mapping.source_label
    batch = Batch(
        source=source_label,
        filename=file.filename or "unknown.csv",
        mapping_function_id=mapping.id,
        status="processing",
    )
    session.add(batch)
    await session.flush()

    batch = await run_ingestion(
        session, batch, mapping.mapping_spec, rows, enrichment_hold=enrichment_hold
    )
    # Commit before waking the enrichment long-poll: the woken request
    # queries in its own session, so uncommitted leads would be invisible
    # and the wake-up wasted (it would only catch up on the next timeout).
    await session.commit()
    notify_work()
    return BatchSummary(**batch.model_dump())


@router.get("/{batch_id}", response_model=BatchDetail, operation_id="get_batch_detail")
async def get_batch_detail(session: DbSession, batch_id: uuid.UUID) -> BatchDetail:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Batch {batch_id} not found")

    quarantined = (
        (
            await session.execute(
                select(RawRow)
                .where(RawRow.batch_id == batch_id, RawRow.validation_status == "quarantined")
                .order_by(RawRow.row_index)
            )
        )
        .scalars()
        .all()
    )
    return BatchDetail(
        **batch.model_dump(exclude={"mapping_function_id", "source_sheet_url", "updated_at"}),
        quarantined_rows=[
            QuarantinedRowOut(
                row_index=r.row_index,
                quarantine_reason=r.quarantine_reason,
                raw_data=r.raw_data,
            )
            for r in quarantined
        ],
    )
