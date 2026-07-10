"""Lead list/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class LeadOut(BaseModel):
    id: uuid.UUID
    email: str | None
    email_source: str | None
    email_confidence: float | None
    website: str | None
    social_youtube: str | None
    social_twitter: str | None
    social_instagram: str | None
    social_tiktok: str | None
    social_facebook: str | None
    social_linkedin: str | None
    country: str | None
    niche: str | None
    category: str | None
    youtube_channel_name: str | None
    youtube_channel_id: str | None
    youtube_handle: str | None
    youtube_subscriber_count: int | None
    youtube_video_count: int | None
    youtube_uploads_last_30d: int | None
    youtube_avg_views: int | None
    youtube_last_upload_date: date | None
    created_at: datetime
    sources: list[str]


class LeadPage(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    page_size: int


class SourceCount(BaseModel):
    source: str
    lead_count: int


class LeadStats(BaseModel):
    total: int
    with_email: int
    without_email: int
    by_source: list[SourceCount]
