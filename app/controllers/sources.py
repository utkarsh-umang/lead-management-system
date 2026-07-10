"""Per-source detail — what the Dashboard's "Leads by Source" rows link to."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.source import BatchSummaryOut, SourceDetail

router = APIRouter()


@router.get("/{source}", response_model=SourceDetail, operation_id="get_source_detail")
async def get_source_detail(session: DbSession, source: str) -> SourceDetail:
    batches = (
        (
            await session.execute(
                select(Batch).where(Batch.source == source).order_by(Batch.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    if not batches:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No batches found for source {source!r}")

    lead_ids_result = await session.execute(
        select(LeadSource.lead_id)
        .join(Batch, LeadSource.batch_id == Batch.id)
        .where(Batch.source == source)
        .distinct()
    )
    lead_ids = [row[0] for row in lead_ids_result.all()]

    currently_with_email = 0
    if lead_ids:
        currently_with_email = (
            await session.execute(
                select(func.count())
                .select_from(MasterLead)
                .where(MasterLead.id.in_(lead_ids), MasterLead.email.is_not(None))
            )
        ).scalar_one()

    return SourceDetail(
        source=source,
        lead_count=len(lead_ids),
        total_rows_uploaded=sum(b.row_count_raw for b in batches),
        total_quarantined=sum(b.row_count_quarantined for b in batches),
        total_deduped=sum(b.row_count_merged for b in batches),
        # NOT sum(b.row_count_with_email for b in batches) — that was a real
        # bug: a lead re-uploaded across N batches (dedup) got its email
        # counted N times, so 4 duplicate leads with email inflated to
        # "8 emails" instead of staying 4. row_count_with_email is still
        # correct *per batch* (shown in batches[].row_count_with_email
        # below, for the upload-history table) — the bug was only in
        # summing it across batches that overlap on the same leads.
        # Distinct-lead currently_with_email is the correct number here:
        # upsert only ever fills a null email, never overwrites, and no
        # enricher exists yet to change it later — so "had email at
        # upload" and "currently has email" are provably the same value
        # for every lead right now. Revisit if/when the email finder
        # writes back and the two can actually diverge.
        total_with_email_at_upload=currently_with_email,
        currently_with_email=currently_with_email,
        currently_without_email=len(lead_ids) - currently_with_email,
        batches=[BatchSummaryOut(**b.model_dump()) for b in batches],
    )
