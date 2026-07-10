"""Read access to the master table — paginated, with optional search."""

from fastapi import APIRouter, Query
from sqlalchemy import func, or_
from sqlmodel import select

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.lead import LeadOut, LeadPage

router = APIRouter()


@router.get("", response_model=LeadPage, operation_id="list_leads")
async def list_leads(
    session: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str | None = Query(default=None),
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

    total = (await session.execute(count_query)).scalar_one()

    query = (
        query.order_by(MasterLead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    leads = (await session.execute(query)).scalars().all()

    lead_ids = [lead.id for lead in leads]
    sources_by_lead: dict = {lid: [] for lid in lead_ids}
    if lead_ids:
        rows = await session.execute(
            select(LeadSource.lead_id, Batch.source)
            .join(Batch, LeadSource.batch_id == Batch.id)
            .where(LeadSource.lead_id.in_(lead_ids))
        )
        for lead_id, source in rows.all():
            if source not in sources_by_lead[lead_id]:
                sources_by_lead[lead_id].append(source)

    items = [
        LeadOut(**lead.model_dump(), sources=sources_by_lead.get(lead.id, []))
        for lead in leads
    ]
    return LeadPage(items=items, total=total, page=page, page_size=page_size)
