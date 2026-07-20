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

    # Human gate for the enrichment queue: held leads never appear in the
    # email finder's work queue until explicitly released (import-time
    # "don't run the finder" choice + a Release button on the source page).
    enrichment_hold: bool = Field(default=False)

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
    # Industry is deliberately separate from niche/category: those carry
    # YouTube-native taxonomy from the channel tools, and Apollo's industry
    # taxonomy would silently collide into them.
    industry: str | None = Field(default=None)

    # ── Universal — person identity (when the lead IS a person at a company,
    # e.g. Apollo exports; a YouTube-native lead leaves these NULL) ──
    first_name: str | None = Field(default=None)
    last_name: str | None = Field(default=None)
    job_title: str | None = Field(default=None)
    seniority: str | None = Field(default=None)
    phone: str | None = Field(default=None)

    # ── Universal — company (the org the person belongs to) ──
    company_name: str | None = Field(default=None)
    # A different entity's profile than social_linkedin (the person's) —
    # merging both into one column would lose the person/company distinction.
    company_linkedin: str | None = Field(default=None)

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
