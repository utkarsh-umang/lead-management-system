"""Read access to the master table — paginated, with optional search."""

from fastapi import APIRouter, Query
from sqlalchemy import func, or_
from sqlmodel import select

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.lead import LeadOut, LeadPage, LeadStats, SourceCount, SourceFileOut

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

    items = [
        LeadOut(
            **lead.model_dump(),
            sources=sources_by_lead.get(lead.id, []),
            source_files=list(source_files_by_lead.get(lead.id, {}).values()),
        )
        for lead in leads
    ]
    return LeadPage(items=items, total=total, page=page, page_size=page_size)
