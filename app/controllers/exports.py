"""Export selected leads for an Instantly campaign, recording the contact
event (which leads, scheduled for which month) as a system of record."""

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.export import Export, ExportLead
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.export import (
    ExportCreateIn,
    ExportLeadItem,
    ExportLeadsPage,
    ExportOut,
    ExportPreviewOut,
    ExportSelection,
)
from app.services.contact_record import record_contact_event
from app.services.lead_filters import email_from_finder_condition, search_condition

router = APIRouter()

# Instantly maps CSV columns on import; these headers match its standard
# field names so the mapping step is zero-effort. For YouTube-native leads
# first_name/company_name both carry the channel name — it's the only
# name-like field such a lead has, and {{firstName}} is the variable
# templates actually use. Person-centric leads (Apollo) have the real
# first_name/company_name, which win when present.
CSV_HEADERS = ["email", "first_name", "company_name", "website", "youtube_url", "niche", "country"]


def _selection_query(selection: ExportSelection):
    """Resolve a selection to a MasterLead query — same filter semantics as
    GET /leads, so what you see filtered is exactly what exports."""
    query = select(MasterLead)

    if selection.lead_ids is not None:
        return query.where(MasterLead.id.in_(selection.lead_ids))

    if selection.search:
        query = query.where(search_condition(f"%{selection.search}%"))
    if selection.source:
        source_subquery = (
            select(LeadSource.lead_id)
            .join(Batch, LeadSource.batch_id == Batch.id)
            .where(Batch.source == selection.source)
        )
        query = query.where(MasterLead.id.in_(source_subquery))
    if selection.has_email is not None:
        query = query.where(
            MasterLead.email.is_not(None) if selection.has_email else MasterLead.email.is_(None)
        )
    if selection.email_from_finder is not None:
        query = query.where(email_from_finder_condition(selection.email_from_finder))
    return query


# asyncpg refuses a statement with more than 32,767 bind parameters, and a
# select-all-matching export on a big source blows straight past that (the
# Apollo list alone has ~35k exportable leads). The IDs here are an explicit
# selection, not something a subquery can re-derive, so they get chunked.
_MAX_BIND_PARAMS = 30_000


async def _already_exported_ids(session, lead_ids: list[uuid.UUID]) -> dict[uuid.UUID, date]:
    """lead_id -> most recent scheduled_month, for leads exported before."""
    if not lead_ids:
        return {}
    exported: dict[uuid.UUID, date] = {}
    for start in range(0, len(lead_ids), _MAX_BIND_PARAMS):
        chunk = lead_ids[start : start + _MAX_BIND_PARAMS]
        rows = await session.execute(
            select(ExportLead.lead_id, func.max(Export.scheduled_month))
            .join(Export, ExportLead.export_id == Export.id)
            .where(ExportLead.lead_id.in_(chunk))
            .group_by(ExportLead.lead_id)
        )
        exported.update(rows.all())
    return exported


@router.get("", response_model=list[ExportOut], operation_id="list_exports")
async def list_exports(session: DbSession) -> list[ExportOut]:
    """Every export event, newest first — the contact system of record."""
    rows = (
        (await session.execute(select(Export).order_by(Export.created_at.desc()))).scalars().all()
    )
    return [ExportOut(**e.model_dump()) for e in rows]


@router.get("/{export_id}/leads", response_model=ExportLeadsPage, operation_id="get_export_leads")
async def get_export_leads(
    session: DbSession,
    export_id: uuid.UUID,
    page: int = 1,
    page_size: int = 25,
) -> ExportLeadsPage:
    """The member leads of one export event. Paginated — a
    select-all-matching export can hold thousands. Leads deleted since the
    export simply drop out of this view (the event's lead_count keeps the
    historical number)."""
    export = await session.get(Export, export_id)
    if export is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Export {export_id} not found")

    total = (
        await session.execute(
            select(func.count())
            .select_from(ExportLead)
            .join(MasterLead, MasterLead.id == ExportLead.lead_id)
            .where(ExportLead.export_id == export_id)
        )
    ).scalar_one()

    # One name-like field per lead, whatever kind of lead it is: channel
    # name for YouTube-native, person name (falling back to company) for
    # person-centric sources like Apollo.
    display_name = func.coalesce(
        MasterLead.youtube_channel_name,
        func.nullif(
            func.trim(
                func.concat(
                    func.coalesce(MasterLead.first_name, ""),
                    " ",
                    func.coalesce(MasterLead.last_name, ""),
                )
            ),
            "",
        ),
        MasterLead.company_name,
    )
    rows = await session.execute(
        select(MasterLead.id, display_name, MasterLead.email)
        .join(ExportLead, ExportLead.lead_id == MasterLead.id)
        .where(ExportLead.export_id == export_id)
        .order_by(display_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return ExportLeadsPage(
        items=[
            ExportLeadItem(lead_id=lid, display_name=name, email=email)
            for lid, name, email in rows.all()
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/preview", response_model=ExportPreviewOut, operation_id="preview_export")
async def preview_export(session: DbSession, selection: ExportSelection) -> ExportPreviewOut:
    leads = (await session.execute(_selection_query(selection))).scalars().all()
    exportable = [lead for lead in leads if lead.email]
    exported_before = await _already_exported_ids(session, [lead.id for lead in exportable])

    return ExportPreviewOut(
        total_selected=len(leads),
        exportable=len(exportable),
        excluded_no_email=len(leads) - len(exportable),
        already_exported=len(exported_before),
        already_exported_last_month=max(exported_before.values()) if exported_before else None,
    )


@router.post("", operation_id="create_export")
async def create_export(session: DbSession, body: ExportCreateIn) -> StreamingResponse:
    leads = (await session.execute(_selection_query(body))).scalars().all()
    exportable = [lead for lead in leads if lead.email]

    if not body.include_already_exported:
        exported_before = await _already_exported_ids(session, [lead.id for lead in exportable])
        exportable = [lead for lead in exportable if lead.id not in exported_before]

    if not exportable:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Nothing to export — no selected lead has an email"
            + ("" if body.include_already_exported else " (or all were already exported)"),
        )

    scheduled_month = date(body.year, body.month, 1)
    await record_contact_event(session, [lead.id for lead in exportable], scheduled_month)
    # Commit before streaming: the dependency's commit runs in teardown,
    # after the response body is already on the wire — too late to fail.
    # The contact record must be durable before the user has the CSV.
    await session.commit()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADERS)
    for lead in exportable:
        writer.writerow(
            [
                lead.email,
                lead.first_name or lead.youtube_channel_name or "",
                lead.company_name or lead.youtube_channel_name or "",
                lead.website or "",
                lead.social_youtube or "",
                lead.niche or lead.industry or "",
                lead.country or "",
            ]
        )
    buffer.seek(0)

    filename = f"instantly-{scheduled_month:%Y-%m}-{len(exportable)}-leads.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
