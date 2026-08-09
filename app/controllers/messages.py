"""On-demand `email_to_send` generation — pick a source + list + method, preview
a few outputs, then write the opening line onto every lead in that list.

Generation is deterministic today (a template over canonical fields), so both
preview and generate run inline. The method registry is self-describing, so the
UI's method picker comes straight from GET /messages/methods.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.message import (
    GenerateMessagesIn,
    GenerateMessagesResult,
    MessagePreviewOut,
    MessageSample,
    MethodOut,
)
from app.services.messages.methods import MESSAGE_METHODS, get_method

router = APIRouter()

_PREVIEW_SAMPLE_SIZE = 5


def _display_name(lead: MasterLead) -> str:
    return (
        lead.company_name
        or lead.first_name
        or lead.youtube_channel_name
        or ""
    )


async def _leads_for_list(session, source: str, batch_id: uuid.UUID) -> list[MasterLead]:
    """Distinct leads linked to this batch. Validates the batch exists and
    belongs to the named source (guards against a stale source/list pairing)."""
    batch = (
        await session.execute(select(Batch).where(Batch.id == batch_id))
    ).scalars().first()
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No list (batch) {batch_id}")
    if batch.source != source:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"List {batch_id} belongs to source {batch.source!r}, not {source!r}",
        )
    # Subquery, not a materialized id list — asyncpg caps bind params at 32,767
    # and a single list can exceed that (see sources.py).
    lead_ids_subq = (
        select(LeadSource.lead_id).where(LeadSource.batch_id == batch_id).distinct()
    )
    return (
        (await session.execute(select(MasterLead).where(MasterLead.id.in_(lead_ids_subq))))
        .scalars()
        .all()
    )


@router.get("/methods", response_model=list[MethodOut], operation_id="list_message_methods")
async def list_message_methods() -> list[MethodOut]:
    """Every registered generation method, for the UI's method picker."""
    return [
        MethodOut(
            name=m.name,
            label=m.label,
            description=m.description,
            kind=m.kind,
            required_fields=m.required_fields,
        )
        for m in MESSAGE_METHODS.values()
    ]


@router.post("/preview", response_model=MessagePreviewOut, operation_id="preview_messages")
async def preview_messages(session: DbSession, body: GenerateMessagesIn) -> MessagePreviewOut:
    """Dry run: how many leads the method can write, and a few real outputs.
    Writes nothing."""
    method = get_method(body.method)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown method {body.method!r}")

    leads = await _leads_for_list(session, body.source, body.batch_id)

    would_generate = 0
    samples: list[MessageSample] = []
    for lead in leads:
        line = method.generate(lead)
        if line is None:
            continue
        would_generate += 1
        if len(samples) < _PREVIEW_SAMPLE_SIZE:
            samples.append(
                MessageSample(
                    lead_id=lead.id,
                    display_name=_display_name(lead),
                    email_to_send=line,
                )
            )

    return MessagePreviewOut(
        method=body.method,
        total_leads=len(leads),
        would_generate=would_generate,
        would_skip=len(leads) - would_generate,
        samples=samples,
    )


@router.post("/generate", response_model=GenerateMessagesResult, operation_id="generate_messages")
async def generate_messages(session: DbSession, body: GenerateMessagesIn) -> GenerateMessagesResult:
    """Write `email_to_send` for every lead in the list the method can produce a
    line for. Latest run wins (overwrite); leads the method skips are left as-is,
    so a re-run with a narrower method never clobbers a prior good line."""
    method = get_method(body.method)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown method {body.method!r}")

    leads = await _leads_for_list(session, body.source, body.batch_id)

    generated = 0
    for lead in leads:
        line = method.generate(lead)
        if line is None:
            continue
        lead.email_to_send = line
        session.add(lead)
        generated += 1

    await session.commit()

    return GenerateMessagesResult(
        method=body.method,
        total_leads=len(leads),
        generated=generated,
        skipped=len(leads) - generated,
    )
