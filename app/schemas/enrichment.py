"""Enrichment work-queue and write-back schemas — the contract between LMS
and the enricher ring (email finder today). Enrichers read a queue item,
work it, and post one result back keyed by lead_id; they never touch LMS
internals beyond this interface."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EnrichmentQueueItem(BaseModel):
    """What the email finder needs to work a lead — identity + every
    location signal we have."""

    lead_id: uuid.UUID
    youtube_channel_name: str | None
    youtube_handle: str | None
    website: str | None
    social_youtube: str | None
    social_twitter: str | None
    social_instagram: str | None
    social_tiktok: str | None
    social_facebook: str | None
    social_linkedin: str | None
    niche: str | None
    country: str | None
    # Person/company identity — what the search-first guest finder needs. Empty
    # for YouTube-native leads. lead_tag doubles as the worker's routing signal:
    # a tagged lead (podscan) goes to the guest finder, else to the crawl graph.
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    job_title: str | None = None
    industry: str | None = None
    lead_tag: str | None = None
    # Directory-native handle for company-as-lead sources (Clutch): the lead has
    # no website/person yet, so this profile URL is the resolver's starting
    # point (profile -> domain -> senior person -> email). Its presence also
    # routes the worker to the company-contact resolver instead of the person
    # finders. None for every person-centric lead.
    clutch_profile_url: str | None = None


class EnrichmentResultIn(BaseModel):
    lead_id: uuid.UUID
    type: Literal["email"] = "email"
    cost_mode: Literal["low", "high"]
    status: Literal["found", "not_found", "failed"]
    value: str | None = None  # the email when status == "found"
    confidence: float | None = None
    provider: str | None = None
    cost_incurred: float | None = None
    # Candidate context the enricher gathered (for offline re-scoring later).
    evidence: dict | None = None
    # Company-as-lead (Clutch) resolution: WHOSE email this is. A Clutch lead
    # starts as a bare company; the resolver picks one senior person and finds
    # their address, so the result carries that person back to stamp onto the
    # (otherwise personless) lead. All optional — person-centric finders omit them.
    person_first_name: str | None = None
    person_last_name: str | None = None
    person_job_title: str | None = None
    person_seniority: str | None = None
    # Provider deliverability verdict for `value` (e.g. Mailin: "ok" | "catch_all"
    # | "invalid"). Distinct from `confidence` (our name-match score) — this is a
    # verifier's own assessment. Stored on lead.email_status.
    email_status: str | None = None


class EnrichmentAttemptOut(BaseModel):
    type: str
    cost_mode: str
    status: str
    value: str | None
    provider: str | None
    cost_incurred: float | None
    attempted_at: datetime


class HeartbeatIn(BaseModel):
    state: Literal["waiting", "processing", "blocked"]
    detail: str | None = None
    in_flight: int = 0


class PauseIn(BaseModel):
    reason: str


class RequeueIn(BaseModel):
    """Re-queue leads for another enrichment attempt WITHOUT deleting the ledger:
    their current attempts at this cost_mode are marked superseded (rows stay),
    and their finder-earned email is cleared so the queue serves them again.
    Use this instead of deleting attempt rows."""

    lead_ids: list[uuid.UUID]
    cost_mode: Literal["low", "high"] = "low"


class EnrichmentStatusOut(BaseModel):
    """Everything the dashboard panel needs to answer 'what's the finder
    doing, and can I close my laptop?'"""

    # Worker liveness (from heartbeats; worker_alive = seen recently)
    worker_state: str | None  # waiting | processing | blocked | None = never seen
    worker_detail: str | None
    worker_in_flight: int
    worker_last_seen_at: datetime | None
    worker_alive: bool

    # Human-in-the-loop gate
    paused: bool
    pause_reason: str | None

    # Queue + progress
    pending_low: int
    pending_high: int
    attempts_last_hour: int
    attempts_today: int
    found_today: int

    # All-time finder performance (backfill rows excluded, like throughput).
    # Found rate = found_total / attempts_total, computed client-side.
    attempts_total: int
    found_total: int

    # Real money: sum of per-attempt cost_incurred reported by the worker
    # (exact LLM costs + estimated ScrapingBee/Perplexity per-call costs).
    cost_today_usd: float
    cost_total_usd: float
