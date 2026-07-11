"""The enrichment interface: a pull work-queue + a write-back endpoint.

The queue is derived from attempt history (see EnrichmentAttempt), never
pushed by upload events — that's what makes the whole flow idempotent:
re-uploads, worker crashes, and restarts can't double-pay for a lead
because "already attempted at this cost tier" is a database fact, not
in-flight state."""

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exists
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.models.enrichment_attempt import EnrichmentAttempt
from app.models.master_lead import MasterLead
from app.schemas.enrichment import EnrichmentQueueItem, EnrichmentResultIn

router = APIRouter()


@router.get("/queue", response_model=list[EnrichmentQueueItem], operation_id="get_enrichment_queue")
async def get_enrichment_queue(
    session: DbSession,
    cost_mode: str = Query(default="low", pattern="^(low|high)$"),
    limit: int = Query(default=25, ge=1, le=200),
) -> list[EnrichmentQueueItem]:
    """Leads needing an email attempt at this cost tier: no email yet, and
    never attempted at this cost_mode. A low-cost miss therefore stays in
    the high-cost queue — that's the deliberate escalation path."""
    attempted = exists().where(
        EnrichmentAttempt.lead_id == MasterLead.id,
        EnrichmentAttempt.type == "email",
        EnrichmentAttempt.cost_mode == cost_mode,
    )
    leads = (
        (
            await session.execute(
                select(MasterLead)
                .where(MasterLead.email.is_(None), ~attempted)
                .order_by(MasterLead.created_at)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [
        EnrichmentQueueItem(
            lead_id=lead.id,
            youtube_channel_name=lead.youtube_channel_name,
            youtube_handle=lead.youtube_handle,
            website=lead.website,
            social_youtube=lead.social_youtube,
            social_twitter=lead.social_twitter,
            social_instagram=lead.social_instagram,
            social_tiktok=lead.social_tiktok,
            social_facebook=lead.social_facebook,
            social_linkedin=lead.social_linkedin,
            niche=lead.niche,
            country=lead.country,
        )
        for lead in leads
    ]


@router.post("/results", status_code=status.HTTP_204_NO_CONTENT, operation_id="post_enrichment_result")
async def post_enrichment_result(session: DbSession, body: EnrichmentResultIn) -> None:
    """Record one attempt and, on a find, fill the lead's email — in the
    same transaction, so the ledger and the lead can't disagree."""
    lead = await session.get(MasterLead, body.lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Lead {body.lead_id} not found")

    session.add(
        EnrichmentAttempt(
            lead_id=body.lead_id,
            type=body.type,
            cost_mode=body.cost_mode,
            status=body.status,
            value=body.value,
            provider=body.provider,
            cost_incurred=body.cost_incurred,
        )
    )

    # Same upsert semantics as ingestion: fill only if still null, never
    # overwrite. email_source='email_finder' is what keeps "had email at
    # upload" distinguishable from "enriched later" (see sources.py).
    if body.status == "found" and body.value and lead.email is None:
        lead.email = body.value
        lead.email_source = "email_finder"
        lead.email_confidence = body.confidence
        session.add(lead)
