"""On-demand `email_to_send` generation — pick a source + list + method, preview
a few outputs, then write the opening line onto every lead in that list.

Two method kinds run through the same endpoints:
- deterministic (a template over canonical fields) — instant, inline, whole list;
- llm/scrape (e.g. `transcript_opener`) — async external I/O, run with bounded
  concurrency and a `limit`, and fed each lead's raw source row (`provenance`)
  since they read per-appearance fields the canonical MasterLead doesn't carry.

The method registry is self-describing, so the UI's picker comes straight from
GET /messages/methods.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select
from starlette import status

from app.core.config import config
from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.models.raw_row import RawRow
from app.schemas.message import (
    GenerateMessagesIn,
    GenerateMessagesResult,
    MessagePreviewOut,
    MessageSample,
    MethodOut,
)
from app.services.messages.methods import (
    MESSAGE_METHODS,
    MessageContext,
    MessageMethod,
    get_method,
)

router = APIRouter()

_PREVIEW_SAMPLE_SIZE = 5
# llm methods do external I/O per lead; a small pool keeps things moving without
# stampeding a rate-limited upstream (the method itself also backs off on 429s).
_ASYNC_CONCURRENCY = 4


def _display_name(lead: MasterLead) -> str:
    return lead.company_name or lead.first_name or lead.youtube_channel_name or ""


def _is_configured(method: MessageMethod) -> bool:
    """Whether the backend has the keys this method needs. Only the transcript
    opener needs external keys today."""
    if method.name == "transcript_opener":
        return bool(config.PODSCAN_API_KEY and config.OPENAI_API_KEY)
    return True


def _require_configured(method: MessageMethod) -> None:
    if not _is_configured(method):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Method {method.name!r} is not configured — set PODSCAN_API_KEY and "
            "OPENAI_API_KEY in the backend environment.",
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
    lead_ids_subq = (
        select(LeadSource.lead_id).where(LeadSource.batch_id == batch_id).distinct()
    )
    return (
        (await session.execute(select(MasterLead).where(MasterLead.id.in_(lead_ids_subq))))
        .scalars()
        .all()
    )


async def _provenance_for_batch(session, batch_id: uuid.UUID) -> dict[uuid.UUID, dict]:
    """lead_id -> its raw source row (raw_rows.raw_data) for this batch. This is
    where per-appearance fields like episode_id / speaker_label live — the
    canonical MasterLead never promoted them (see the podscan_guest spec)."""
    rows = await session.execute(
        select(LeadSource.lead_id, RawRow.raw_data)
        .join(RawRow, RawRow.id == LeadSource.row_id)
        .where(LeadSource.batch_id == batch_id)
    )
    return {lead_id: (raw or {}) for lead_id, raw in rows.all()}


async def _run_async_method(
    method: MessageMethod, leads: list[MasterLead], provenance: dict[uuid.UUID, dict]
) -> dict[uuid.UUID, str]:
    """Run an llm/scrape method over `leads` with bounded concurrency. Returns
    lead_id -> line for the leads that produced one (others are skipped)."""
    sem = asyncio.Semaphore(_ASYNC_CONCURRENCY)

    async def one(lead: MasterLead) -> tuple[uuid.UUID, str | None]:
        ctx = MessageContext(lead=lead, provenance=provenance.get(lead.id, {}))
        async with sem:
            try:
                return lead.id, await method.agenerate(ctx)
            except Exception:  # noqa: BLE001 — a bad lead must not sink the batch
                return lead.id, None

    results = await asyncio.gather(*(one(lead) for lead in leads))
    return {lid: line for lid, line in results if line}


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
            is_async=m.is_async,
            configured=_is_configured(m),
        )
        for m in MESSAGE_METHODS.values()
    ]


@router.post("/preview", response_model=MessagePreviewOut, operation_id="preview_messages")
async def preview_messages(session: DbSession, body: GenerateMessagesIn) -> MessagePreviewOut:
    """Dry run: a few real outputs (and, for deterministic methods, the exact
    count the method can write). Writes nothing. For llm methods the preview is
    sample-based — running the whole list just to count would spend real calls."""
    method = get_method(body.method)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown method {body.method!r}")
    _require_configured(method)

    leads = await _leads_for_list(session, body.source, body.batch_id)

    if method.is_async:
        sample_leads = leads[:_PREVIEW_SAMPLE_SIZE]
        provenance = (
            await _provenance_for_batch(session, body.batch_id)
            if method.needs_provenance
            else {}
        )
        lines = await _run_async_method(method, sample_leads, provenance)
        samples = [
            MessageSample(lead_id=lead.id, display_name=_display_name(lead),
                          email_to_send=lines[lead.id])
            for lead in sample_leads
            if lead.id in lines
        ]
        # For async methods the counts are over the SAMPLE, not the whole list.
        return MessagePreviewOut(
            method=body.method,
            total_leads=len(leads),
            would_generate=len(samples),
            would_skip=len(sample_leads) - len(samples),
            samples=samples,
        )

    would_generate = 0
    samples: list[MessageSample] = []
    for lead in leads:
        line = method.generate(lead)
        if line is None:
            continue
        would_generate += 1
        if len(samples) < _PREVIEW_SAMPLE_SIZE:
            samples.append(
                MessageSample(lead_id=lead.id, display_name=_display_name(lead),
                              email_to_send=line)
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
    line for. Latest run wins (overwrite); leads the method skips are left as-is.
    `limit` bounds the run — important for the slow, rate-limited llm methods."""
    method = get_method(body.method)
    if method is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown method {body.method!r}")
    _require_configured(method)

    leads = await _leads_for_list(session, body.source, body.batch_id)
    if body.limit is not None:
        leads = leads[: body.limit]

    if method.is_async:
        provenance = (
            await _provenance_for_batch(session, body.batch_id)
            if method.needs_provenance
            else {}
        )
        lines = await _run_async_method(method, leads, provenance)
        for lead in leads:
            line = lines.get(lead.id)
            if line:
                lead.email_to_send = line
                session.add(lead)
        generated = len(lines)
    else:
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
