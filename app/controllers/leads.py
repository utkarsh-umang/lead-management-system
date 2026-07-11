"""Read access to the master table — paginated, with optional search."""

import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, or_
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.enrichment_attempt import EnrichmentAttempt
from app.models.export import Export, ExportLead
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.models.raw_row import RawRow
from app.schemas.enrichment import EnrichmentAttemptOut
from app.schemas.lead import (
    LeadOut,
    LeadPage,
    LeadRawRowOut,
    LeadStats,
    SourceCount,
    SourceFileOut,
)

router = APIRouter()


@router.get("/stats", response_model=LeadStats, operation_id="get_lead_stats")
async def get_lead_stats(session: DbSession) -> LeadStats:
    total = (await session.execute(select(func.count()).select_from(MasterLead))).scalar_one()
    with_email = (
        await session.execute(
            select(func.count()).select_from(MasterLead).where(MasterLead.email.is_not(None))
        )
    ).scalar_one()

    rows = await session.execute(
        select(Batch.source, func.count(func.distinct(LeadSource.lead_id)))
        .join(LeadSource, LeadSource.batch_id == Batch.id)
        .group_by(Batch.source)
        .order_by(func.count(func.distinct(LeadSource.lead_id)).desc())
    )
    by_source = [SourceCount(source=source, lead_count=count) for source, count in rows.all()]

    return LeadStats(
        total=total,
        with_email=with_email,
        without_email=total - with_email,
        by_source=by_source,
    )


@router.get("", response_model=LeadPage, operation_id="list_leads")
async def list_leads(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
    source: str | None = Query(default=None),
    has_email: bool | None = Query(default=None),
) -> LeadPage:
    query = select(MasterLead)
    count_query = select(func.count()).select_from(MasterLead)

    if search:
        pattern = f"%{search}%"
        condition = or_(
            MasterLead.youtube_channel_name.ilike(pattern),
            MasterLead.email.ilike(pattern),
        )
        query = query.where(condition)
        count_query = count_query.where(condition)

    if source:
        source_subquery = (
            select(LeadSource.lead_id).join(Batch, LeadSource.batch_id == Batch.id).where(Batch.source == source)
        )
        query = query.where(MasterLead.id.in_(source_subquery))
        count_query = count_query.where(MasterLead.id.in_(source_subquery))

    if has_email is not None:
        condition = MasterLead.email.is_not(None) if has_email else MasterLead.email.is_(None)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await session.execute(count_query)).scalar_one()

    query = (
        query.order_by(MasterLead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    leads = (await session.execute(query)).scalars().all()

    lead_ids = [lead.id for lead in leads]
    sources_by_lead: dict = {lid: [] for lid in lead_ids}
    # Keyed by (lead_id, batch_id) so a batch that contributed more than one
    # row to the same lead (internal duplicates within that upload) only
    # shows up once — one entry per distinct upload, not per row.
    source_files_by_lead: dict = {lid: {} for lid in lead_ids}
    last_contacted_by_lead: dict = {}
    if lead_ids:
        rows = await session.execute(
            select(LeadSource.lead_id, Batch.id, Batch.source, Batch.filename, Batch.created_at)
            .join(Batch, LeadSource.batch_id == Batch.id)
            .where(LeadSource.lead_id.in_(lead_ids))
        )
        for lead_id, batch_id, source, filename, uploaded_at in rows.all():
            if source not in sources_by_lead[lead_id]:
                sources_by_lead[lead_id].append(source)
            source_files_by_lead[lead_id][batch_id] = SourceFileOut(
                source=source, filename=filename, uploaded_at=uploaded_at
            )

        contacted_rows = await session.execute(
            select(ExportLead.lead_id, func.max(Export.scheduled_month))
            .join(Export, ExportLead.export_id == Export.id)
            .where(ExportLead.lead_id.in_(lead_ids))
            .group_by(ExportLead.lead_id)
        )
        last_contacted_by_lead = dict(contacted_rows.all())

        tried_rows = await session.execute(
            select(EnrichmentAttempt.lead_id)
            .where(EnrichmentAttempt.lead_id.in_(lead_ids), EnrichmentAttempt.type == "email")
            .distinct()
        )
        email_finder_tried_ids = {row[0] for row in tried_rows.all()}

    items = [
        LeadOut(
            **lead.model_dump(),
            sources=sources_by_lead.get(lead.id, []),
            source_files=list(source_files_by_lead.get(lead.id, {}).values()),
            last_contacted=last_contacted_by_lead.get(lead.id),
            email_finder_tried=lead.id in email_finder_tried_ids,
        )
        for lead in leads
    ]
    return LeadPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{lead_id}/raw", response_model=list[LeadRawRowOut], operation_id="get_lead_raw_rows")
async def get_lead_raw_rows(session: DbSession, lead_id: uuid.UUID) -> list[LeadRawRowOut]:
    """Every original CSV row that ever contributed to this lead, via the
    lead_sources provenance trail — the untouched pre-mapping values."""
    lead = await session.get(MasterLead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Lead {lead_id} not found")

    rows = await session.execute(
        select(Batch.source, Batch.filename, Batch.created_at, RawRow.row_index, RawRow.raw_data)
        .select_from(LeadSource)
        .join(Batch, LeadSource.batch_id == Batch.id)
        .join(RawRow, LeadSource.row_id == RawRow.id)
        .where(LeadSource.lead_id == lead_id)
        .order_by(Batch.created_at)
    )
    return [
        LeadRawRowOut(
            source=source,
            filename=filename,
            uploaded_at=uploaded_at,
            row_index=row_index,
            raw_data=raw_data,
        )
        for source, filename, uploaded_at, row_index, raw_data in rows.all()
    ]


@router.get(
    "/{lead_id}/enrichment",
    response_model=list[EnrichmentAttemptOut],
    operation_id="get_lead_enrichment_attempts",
)
async def get_lead_enrichment_attempts(
    session: DbSession, lead_id: uuid.UUID
) -> list[EnrichmentAttemptOut]:
    lead = await session.get(MasterLead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Lead {lead_id} not found")

    attempts = (
        (
            await session.execute(
                select(EnrichmentAttempt)
                .where(EnrichmentAttempt.lead_id == lead_id)
                .order_by(EnrichmentAttempt.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [
        EnrichmentAttemptOut(
            type=a.type,
            cost_mode=a.cost_mode,
            status=a.status,
            value=a.value,
            provider=a.provider,
            cost_incurred=a.cost_incurred,
            attempted_at=a.created_at,
        )
        for a in attempts
    ]


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_lead")
async def delete_lead(session: DbSession, lead_id: uuid.UUID) -> None:
    lead = await session.get(MasterLead, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Lead {lead_id} not found")

    # lead_sources and export_leads rows reference this lead with no
    # ON DELETE CASCADE at the DB level — delete them first or the foreign
    # key blocks the delete. raw_rows are left untouched: they're the
    # historical record of what was actually uploaded, independent of
    # whether a canonical lead currently exists for them. Batch counts
    # (row_count_new_leads etc.) and exports.lead_count are also left
    # as-is — fixed facts about what happened during those events, not
    # something a later deletion should retroactively rewrite.
    await session.execute(delete(LeadSource).where(LeadSource.lead_id == lead_id))
    await session.execute(delete(ExportLead).where(ExportLead.lead_id == lead_id))
    await session.execute(delete(EnrichmentAttempt).where(EnrichmentAttempt.lead_id == lead_id))
    await session.delete(lead)
