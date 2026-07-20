"""Per-source detail — what the Dashboard's "Leads by Source" rows link to."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, update
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.enrichment_attempt import EnrichmentAttempt
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.source import BatchSummaryOut, ReleaseResult, SourceDetail
from app.services.enrichment_signals import notify_work

router = APIRouter()


@router.post(
    "/{source}/release-enrichment",
    response_model=ReleaseResult,
    operation_id="release_enrichment_hold",
)
async def release_enrichment_hold(session: DbSession, source: str) -> ReleaseResult:
    """Lift the import-time hold for this source's leads — they join the
    email finder queue immediately (the worker is woken, not polled)."""
    lead_ids_subq = (
        select(LeadSource.lead_id)
        .join(Batch, LeadSource.batch_id == Batch.id)
        .where(Batch.source == source)
    )
    result = await session.execute(
        update(MasterLead)
        .where(MasterLead.id.in_(lead_ids_subq), MasterLead.enrichment_hold.is_(True))
        .values(enrichment_hold=False)
    )
    # Commit before waking the long-poll — the woken request reads in a
    # fresh session, so the flag flip must be durable first.
    await session.commit()
    if result.rowcount:
        notify_work()
    return ReleaseResult(released=result.rowcount or 0)


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

    # A SUBQUERY, never a materialized list of IDs: passing them back as
    # bind parameters dies at 32,767 (asyncpg's limit), which is a real
    # source size — the 36,535-lead Apollo list 500'd on exactly this.
    # Every count below filters on this, so the IDs stay inside Postgres.
    lead_ids_subq = (
        select(LeadSource.lead_id)
        .join(Batch, LeadSource.batch_id == Batch.id)
        .where(Batch.source == source)
        .distinct()
    )

    lead_count = (
        await session.execute(
            select(func.count()).select_from(lead_ids_subq.subquery())
        )
    ).scalar_one()

    currently_with_email = 0
    with_email_at_upload = 0
    enrichment_tried_no_email = 0
    enrichment_on_hold = 0
    if lead_count:
        currently_with_email = (
            await session.execute(
                select(func.count())
                .select_from(MasterLead)
                .where(MasterLead.id.in_(lead_ids_subq), MasterLead.email.is_not(None))
            )
        ).scalar_one()
        # "Had email at upload" = has an email that did NOT come from the
        # email finder. Now that the enricher writes back (always with
        # email_source='email_finder'), this and currently_with_email are
        # genuinely different questions — enriched emails count in the
        # latter only. (Never compute this by summing
        # batches.row_count_with_email across batches: a lead re-uploaded
        # across N batches gets counted N times — the original
        # double-counting bug.)
        with_email_at_upload = (
            await session.execute(
                select(func.count())
                .select_from(MasterLead)
                .where(
                    MasterLead.id.in_(lead_ids_subq),
                    MasterLead.email.is_not(None),
                    func.coalesce(MasterLead.email_source, "") != "email_finder",
                )
            )
        ).scalar_one()
        # Of the leads still without email: how many the email finder has
        # already tried (any tier). The remainder is the pending queue.
        enrichment_tried_no_email = (
            await session.execute(
                select(func.count(func.distinct(EnrichmentAttempt.lead_id)))
                .select_from(EnrichmentAttempt)
                .join(MasterLead, MasterLead.id == EnrichmentAttempt.lead_id)
                .where(
                    EnrichmentAttempt.lead_id.in_(lead_ids_subq),
                    EnrichmentAttempt.type == "email",
                    MasterLead.email.is_(None),
                )
            )
        ).scalar_one()
        enrichment_on_hold = (
            await session.execute(
                select(func.count())
                .select_from(MasterLead)
                .where(
                    MasterLead.id.in_(lead_ids_subq),
                    MasterLead.email.is_(None),
                    MasterLead.enrichment_hold.is_(True),
                )
            )
        ).scalar_one()

    without_email = lead_count - currently_with_email
    return SourceDetail(
        source=source,
        lead_count=lead_count,
        total_rows_uploaded=sum(b.row_count_raw for b in batches),
        total_quarantined=sum(b.row_count_quarantined for b in batches),
        total_deduped=sum(b.row_count_merged for b in batches),
        total_with_email_at_upload=with_email_at_upload,
        currently_with_email=currently_with_email,
        currently_without_email=without_email,
        enrichment_tried_no_email=enrichment_tried_no_email,
        enrichment_on_hold=enrichment_on_hold,
        # held leads are neither tried nor waiting for the worker
        enrichment_pending=without_email - enrichment_tried_no_email - enrichment_on_hold,
        batches=[BatchSummaryOut(**b.model_dump()) for b in batches],
    )
