"""Lead list/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SourceFileOut(BaseModel):
    """One batch/CSV that contributed to a lead — the CSV filename is what
    actually distinguishes uploads within the same source, since a source
    label like "youtube-tool" can have many uploads over time."""

    source: str
    filename: str
    uploaded_at: datetime


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
    industry: str | None
    first_name: str | None
    last_name: str | None
    job_title: str | None
    seniority: str | None
    phone: str | None
    company_name: str | None
    company_linkedin: str | None
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
    source_files: list[SourceFileOut]
    # Most recent Instantly export month for this lead (see exports tables) —
    # null means never contacted.
    last_contacted: date | None
    # Whether the email finder has attempted this lead (any cost tier) —
    # splits "no email yet" into "not yet attempted" vs "tried, not found".
    email_finder_tried: bool


class LeadRawRowOut(BaseModel):
    """One original CSV row that contributed to a lead — the untouched
    source values, before any mapping/normalization."""

    source: str
    filename: str
    uploaded_at: datetime
    row_index: int
    raw_data: dict


class LeadPage(BaseModel):
    items: list[LeadOut]
    total: int
    page: int
    page_size: int


class SourceCount(BaseModel):
    source: str
    lead_count: int
    # Upload-level context so the Dashboard list answers "how much raw
    # volume, across how many files" without a click-through.
    total_rows_uploaded: int
    upload_count: int


class LeadStats(BaseModel):
    total: int
    with_email: int
    without_email: int
    # The working pipeline: has an email (so it CAN be contacted) and has
    # never appeared in an export. Deliberately not "every lead without an
    # export" — a lead with no email isn't waiting on you, it's waiting on
    # the finder, and lumping the two hides the number you'd act on.
    contactable_never_contacted: int
    by_source: list[SourceCount]
