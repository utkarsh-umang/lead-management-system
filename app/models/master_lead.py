"""The canonical lead — master table. Wide and sparse by design: any given
source populates only a subset of these columns, and that's expected, not
an error. Missing values are always NULL, never a sentinel string (see
Lead Management System.md for why) — "was this field even attempted for
this lead's source" is answered via MappingFunction / LeadSource, not a
per-cell marker.

Naming convention: fields that mean the same thing across every source stay
generic (email, website, country, social_*). Fields that only exist because
the lead's core identity IS a specific platform are prefixed with that
platform (youtube_*) — never a bare `name` that different sources would
collide into.
"""

from datetime import date, datetime

from sqlmodel import Field

from app.db.base import Base


class MasterLead(Base, table=True):
    __tablename__ = "master_leads"

    # ── Universal — contact & web presence ──
    email: str | None = Field(default=None, index=True)
    email_source: str | None = Field(default=None)
    email_confidence: float | None = Field(default=None)
    website: str | None = Field(default=None)

    social_youtube: str | None = Field(default=None)
    social_twitter: str | None = Field(default=None)
    social_instagram: str | None = Field(default=None)
    social_tiktok: str | None = Field(default=None)
    social_facebook: str | None = Field(default=None)
    social_linkedin: str | None = Field(default=None)

    # ── Universal — categorization ──
    country: str | None = Field(default=None, index=True)
    niche: str | None = Field(default=None)
    category: str | None = Field(default=None)

    # ── Universal — provenance from the upstream source tool itself ──
    source_discovered_at: datetime | None = Field(default=None)

    # ── YouTube-native identity (only when the lead IS a YouTube channel) ──
    youtube_channel_name: str | None = Field(default=None, index=True)
    youtube_channel_id: str | None = Field(default=None, index=True)
    youtube_handle: str | None = Field(default=None)
    youtube_subscriber_count: int | None = Field(default=None)
    youtube_video_count: int | None = Field(default=None)
    youtube_uploads_last_30d: int | None = Field(default=None)
    youtube_avg_views: int | None = Field(default=None)
    youtube_last_upload_date: date | None = Field(default=None)
