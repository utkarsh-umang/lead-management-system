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


class EnrichmentResultIn(BaseModel):
    lead_id: uuid.UUID
    type: Literal["email"] = "email"
    cost_mode: Literal["low", "high"]
    status: Literal["found", "not_found", "failed"]
    value: str | None = None  # the email when status == "found"
    confidence: float | None = None
    provider: str | None = None
    cost_incurred: float | None = None


class EnrichmentAttemptOut(BaseModel):
    type: str
    cost_mode: str
    status: str
    value: str | None
    provider: str | None
    cost_incurred: float | None
    attempted_at: datetime
