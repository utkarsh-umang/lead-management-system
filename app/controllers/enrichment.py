"""The enrichment interface: a pull work-queue + a write-back endpoint.

The queue is derived from attempt history (see EnrichmentAttempt), never
pushed by upload events — that's what makes the whole flow idempotent:
re-uploads, worker crashes, and restarts can't double-pay for a lead
because "already attempted at this cost tier" is a database fact, not
in-flight state."""

import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import exists, func
from sqlmodel import select
from starlette import status

from app.core.db_dep import DbSession
from app.db.session import AsyncSessionLocal
from app.models.enrichment_attempt import EnrichmentAttempt
from app.models.enrichment_worker import EnrichmentWorkerState
from app.models.master_lead import MasterLead
from app.schemas.enrichment import (
    EnrichmentQueueItem,
    EnrichmentResultIn,
    EnrichmentStatusOut,
    HeartbeatIn,
    PauseIn,
)
from app.services import enrichment_signals as signals
from app.services.mapping.email_junk import is_junk_email

router = APIRouter()

# A worker that hasn't heartbeated in this long is presumed dead/asleep.
WORKER_ALIVE_WINDOW = timedelta(minutes=2)


def _queue_query(cost_mode: str, limit: int):
    attempted = exists().where(
        EnrichmentAttempt.lead_id == MasterLead.id,
        EnrichmentAttempt.type == "email",
        EnrichmentAttempt.cost_mode == cost_mode,
    )
    return (
        select(MasterLead)
        .where(
            MasterLead.email.is_(None),
            MasterLead.enrichment_hold.is_(False),  # held leads wait for Release
            ~attempted,
        )
        .order_by(MasterLead.created_at)
        .limit(limit)
    )


def _to_queue_item(lead: MasterLead) -> EnrichmentQueueItem:
    return EnrichmentQueueItem(
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


async def _get_worker_state(session) -> EnrichmentWorkerState | None:
    return (
        (await session.execute(select(EnrichmentWorkerState).limit(1))).scalars().first()
    )


@router.get("/queue", response_model=list[EnrichmentQueueItem], operation_id="get_enrichment_queue")
async def get_enrichment_queue(
    session: DbSession,
    cost_mode: str = Query(default="low", pattern="^(low|high)$"),
    limit: int = Query(default=25, ge=1, le=200),
) -> list[EnrichmentQueueItem]:
    """Leads needing an email attempt at this cost tier: no email yet, and
    never attempted at this cost_mode. A low-cost miss therefore stays in
    the high-cost queue — that's the deliberate escalation path."""
    leads = (await session.execute(_queue_query(cost_mode, limit))).scalars().all()
    return [_to_queue_item(lead) for lead in leads]


@router.get(
    "/queue/wait",
    response_model=list[EnrichmentQueueItem],
    operation_id="wait_enrichment_queue",
)
async def wait_enrichment_queue(
    cost_mode: str = Query(default="low", pattern="^(low|high)$"),
    limit: int = Query(default=50, ge=1, le=200),
    timeout: float = Query(default=55.0, ge=1.0, le=110.0),
) -> list[EnrichmentQueueItem]:
    """Long-poll variant of /queue: holds the request open until work
    exists (returns immediately with it) or `timeout` elapses (returns []).
    While paused (human-in-the-loop gate), it blocks even if work exists —
    a Resume wakes it instantly.

    Deliberately no DbSession dependency: that would pin a pooled
    connection for the whole held request. Short-lived sessions are opened
    only for each actual check."""
    deadline = asyncio.get_event_loop().time() + timeout

    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            return []

        async with AsyncSessionLocal() as session:
            worker_state = await _get_worker_state(session)
            paused = bool(worker_state and worker_state.paused)
            leads = []
            if not paused:
                leads = (await session.execute(_queue_query(cost_mode, limit))).scalars().all()

        if paused:
            # Only a control change (Resume) can make progress — new work
            # arriving is irrelevant while the gate is closed.
            await signals.wait_for(signals.control_changed, remaining)
            continue
        if leads:
            return [_to_queue_item(lead) for lead in leads]
        # Empty queue: sleep until ingestion signals new work (or timeout).
        await signals.wait_for(signals.work_available, remaining)


@router.post("/heartbeat", status_code=status.HTTP_204_NO_CONTENT, operation_id="post_worker_heartbeat")
async def post_worker_heartbeat(session: DbSession, body: HeartbeatIn) -> None:
    worker = await _get_worker_state(session)
    if worker is None:
        worker = EnrichmentWorkerState()
    worker.state = body.state
    worker.detail = body.detail
    worker.in_flight = body.in_flight
    worker.last_seen_at = datetime.utcnow()
    session.add(worker)


@router.post("/pause", status_code=status.HTTP_204_NO_CONTENT, operation_id="pause_enrichment")
async def pause_enrichment(session: DbSession, body: PauseIn) -> None:
    """Called by the worker on a hard block (credits exhausted, bad key).
    Only POST /resume — a human action — reopens the gate."""
    worker = await _get_worker_state(session)
    if worker is None:
        worker = EnrichmentWorkerState()
    worker.paused = True
    worker.pause_reason = body.reason
    worker.state = "blocked"
    worker.detail = body.reason
    worker.last_seen_at = datetime.utcnow()
    session.add(worker)
    signals.notify_control()


@router.post("/resume", status_code=status.HTTP_204_NO_CONTENT, operation_id="resume_enrichment")
async def resume_enrichment(session: DbSession) -> None:
    """The 'Continue — I've recharged' button. Clears the gate and wakes
    any worker blocked on /queue/wait immediately."""
    worker = await _get_worker_state(session)
    if worker is None:
        worker = EnrichmentWorkerState()
    worker.paused = False
    worker.pause_reason = None
    session.add(worker)
    # Commit before signaling: the woken request reads state in a NEW
    # session, so the flag must be durable before the event fires.
    await session.commit()
    signals.notify_control()


@router.get("/status", response_model=EnrichmentStatusOut, operation_id="get_enrichment_status")
async def get_enrichment_status(session: DbSession) -> EnrichmentStatusOut:
    worker = await _get_worker_state(session)

    async def _pending(cost_mode: str) -> int:
        attempted = exists().where(
            EnrichmentAttempt.lead_id == MasterLead.id,
            EnrichmentAttempt.type == "email",
            EnrichmentAttempt.cost_mode == cost_mode,
        )
        return (
            await session.execute(
                select(func.count())
                .select_from(MasterLead)
                .where(
                    MasterLead.email.is_(None),
                    MasterLead.enrichment_hold.is_(False),
                    ~attempted,
                )
            )
        ).scalar_one()

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def _attempts_since(since: datetime, only_found: bool = False) -> int:
        query = (
            select(func.count())
            .select_from(EnrichmentAttempt)
            .where(
                EnrichmentAttempt.created_at >= since,
                # Backfilled ledger rows (imported pre-LMS run history) are
                # not throughput — counting them makes "tried today" and the
                # ETA lie on any day a backfill happens.
                ~EnrichmentAttempt.provider.like("backfill:%"),
            )
        )
        if only_found:
            query = query.where(EnrichmentAttempt.status == "found")
        return (await session.execute(query)).scalar_one()

    return EnrichmentStatusOut(
        worker_state=worker.state if worker else None,
        worker_detail=worker.detail if worker else None,
        worker_in_flight=worker.in_flight if worker else 0,
        worker_last_seen_at=worker.last_seen_at if worker else None,
        worker_alive=bool(worker and now - worker.last_seen_at < WORKER_ALIVE_WINDOW),
        paused=bool(worker and worker.paused),
        pause_reason=worker.pause_reason if worker else None,
        pending_low=await _pending("low"),
        pending_high=await _pending("high"),
        attempts_last_hour=await _attempts_since(now - timedelta(hours=1)),
        attempts_today=await _attempts_since(today_start),
        found_today=await _attempts_since(today_start, only_found=True),
    )


@router.post("/results", status_code=status.HTTP_204_NO_CONTENT, operation_id="post_enrichment_result")
async def post_enrichment_result(session: DbSession, body: EnrichmentResultIn) -> None:
    """Record one attempt and, on a find, fill the lead's email — in the
    same transaction, so the ledger and the lead can't disagree."""
    lead = await session.get(MasterLead, body.lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Lead {body.lead_id} not found")

    # Last line of defense: the store never accepts junk, no matter which
    # enricher sends it. A junk "found" (placeholder/vendor/system mailbox
    # — see email_junk.py) is recorded as not_found, so the lead correctly
    # stays escalatable rather than looking done with a garbage email.
    if body.status == "found" and body.value and is_junk_email(body.value.lower()):
        body = body.model_copy(update={"status": "not_found", "value": None, "confidence": None})

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
