"""ICP / industry classification write-back.

The heavy work (crawl the site + gpt-4o-mini) runs in the ai-agents ICP
classifier; the LMS owns the results. Resumability is free: `pending` returns
only leads in a list not yet classified, and posting results marks them done —
so a re-run just continues where it stopped.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.batch import Batch
from app.models.lead_source import LeadSource
from app.models.master_lead import MasterLead
from app.schemas.classification import (
    ClassificationResultsIn,
    ClassificationResultsOut,
    ClassificationStatus,
    PendingLead,
    RequestClassificationIn,
    RequestClassificationOut,
    RequestedBatch,
)

router = APIRouter()

ICP_ACCEPT_THRESHOLD = 60


async def _pending_count(session, batch_id: uuid.UUID) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(MasterLead)
            .where(
                MasterLead.id.in_(_lead_ids_in_batch(batch_id)),
                _has_website(),
                MasterLead.classified_industry.is_(None),
            )
        )
    ).scalar_one()


def _has_website():
    return MasterLead.website.is_not(None) & (MasterLead.website != "")


def _lead_ids_in_batch(batch_id: uuid.UUID):
    # Subquery, not a materialized id list — asyncpg caps bind params at 32,767
    # and an Apollo list can exceed that (see sources.py / messages.py).
    return select(LeadSource.lead_id).where(LeadSource.batch_id == batch_id).distinct()


async def _require_batch(session, batch_id: uuid.UUID) -> Batch:
    batch = (await session.execute(select(Batch).where(Batch.id == batch_id))).scalars().first()
    if batch is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No list (batch) {batch_id}")
    return batch


@router.get("/pending", response_model=list[PendingLead], operation_id="classification_pending")
async def classification_pending(
    session: DbSession,
    batch_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[PendingLead]:
    """Leads in this list with a website but no classification yet (oldest first)."""
    await _require_batch(session, batch_id)
    rows = (
        await session.execute(
            select(MasterLead.id, MasterLead.company_name, MasterLead.website)
            .where(
                MasterLead.id.in_(_lead_ids_in_batch(batch_id)),
                _has_website(),
                MasterLead.classified_industry.is_(None),
            )
            .order_by(MasterLead.created_at)
            .limit(limit)
        )
    ).all()
    return [PendingLead(lead_id=r[0], company_name=r[1], website=r[2]) for r in rows]


@router.post("/results", response_model=ClassificationResultsOut, operation_id="classification_results")
async def classification_results(
    session: DbSession, body: ClassificationResultsIn
) -> ClassificationResultsOut:
    """Upsert classification verdicts onto the leads. Latest write wins."""
    # Naive UTC — icp_classified_at is TIMESTAMP WITHOUT TIME ZONE.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = 0
    for res in body.results:
        lead = (
            await session.execute(select(MasterLead).where(MasterLead.id == res.lead_id))
        ).scalars().first()
        if lead is None:
            continue
        lead.classified_industry = res.classified_industry
        lead.icp_confidence = res.icp_confidence
        lead.icp_reasoning = res.icp_reasoning
        lead.icp_source = res.icp_source
        lead.icp_classified_at = now
        session.add(lead)
        updated += 1
    await session.commit()
    return ClassificationResultsOut(updated=updated)


@router.get("/status", response_model=ClassificationStatus, operation_id="classification_status")
async def classification_status(session: DbSession, batch_id: uuid.UUID) -> ClassificationStatus:
    """Progress + the industry breakdown for a list."""
    batch = await _require_batch(session, batch_id)
    ids = _lead_ids_in_batch(batch_id)

    async def _count(*conds) -> int:
        q = select(func.count()).select_from(MasterLead).where(MasterLead.id.in_(ids), *conds)
        return (await session.execute(q)).scalar_one()

    total = await _count()
    with_website = await _count(_has_website())
    classified = await _count(MasterLead.classified_industry.is_not(None))
    pending = await _count(_has_website(), MasterLead.classified_industry.is_(None))
    icp_accepted = await _count(MasterLead.icp_confidence >= ICP_ACCEPT_THRESHOLD)

    industry_rows = (
        await session.execute(
            select(MasterLead.classified_industry, func.count())
            .where(MasterLead.id.in_(ids), MasterLead.classified_industry.is_not(None))
            .group_by(MasterLead.classified_industry)
            .order_by(func.count().desc())
        )
    ).all()

    return ClassificationStatus(
        batch_id=batch_id,
        classify_requested=batch.classify_requested,
        total_leads=total,
        with_website=with_website,
        classified=classified,
        pending=pending,
        icp_accepted=icp_accepted,
        by_industry={row[0]: row[1] for row in industry_rows},
    )


@router.post("/request", response_model=RequestClassificationOut, operation_id="request_classification")
async def request_classification(
    session: DbSession, body: RequestClassificationIn
) -> RequestClassificationOut:
    """Mark a list for classification — the worker will pick it up."""
    batch = await _require_batch(session, body.batch_id)
    batch.classify_requested = True
    session.add(batch)
    await session.commit()
    return RequestClassificationOut(
        batch_id=body.batch_id,
        classify_requested=True,
        pending=await _pending_count(session, body.batch_id),
    )


@router.post("/stop", response_model=RequestClassificationOut, operation_id="stop_classification")
async def stop_classification(
    session: DbSession, body: RequestClassificationIn
) -> RequestClassificationOut:
    """Clear the classify request — the worker stops picking up this list."""
    batch = await _require_batch(session, body.batch_id)
    batch.classify_requested = False
    session.add(batch)
    await session.commit()
    return RequestClassificationOut(
        batch_id=body.batch_id,
        classify_requested=False,
        pending=await _pending_count(session, body.batch_id),
    )


@router.get("/requested", response_model=list[RequestedBatch], operation_id="requested_classifications")
async def requested_classifications(session: DbSession) -> list[RequestedBatch]:
    """Lists the worker should classify: requested AND still have pending leads."""
    batches = (
        await session.execute(select(Batch).where(Batch.classify_requested.is_(True)))
    ).scalars().all()
    out: list[RequestedBatch] = []
    for b in batches:
        pending = await _pending_count(session, b.id)
        if pending > 0:
            out.append(RequestedBatch(batch_id=b.id, source=b.source, filename=b.filename, pending=pending))
    return out
