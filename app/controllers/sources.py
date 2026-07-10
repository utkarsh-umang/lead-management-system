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
        total_with_email_at_upload=sum(b.row_count_with_email for b in batches),
        currently_with_email=currently_with_email,
        currently_without_email=len(lead_ids) - currently_with_email,
        batches=[BatchSummaryOut(**b.model_dump()) for b in batches],
    )
