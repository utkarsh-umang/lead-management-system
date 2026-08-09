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
    # Company headcount (Apollo "# Employees"). Promoted from raw because it's a
    # primary targeting axis (the 30k list was scoped to 100-200 employees).
    company_headcount: int | None = Field(default=None)

    # ── Universal — email quality ──
    # Provider's deliverability verdict for `email` (Apollo "Email Status":
    # verified / extrapolated / unavailable). Distinct from email_confidence,
    # which is OUR finder's score — this is the source's own assessment.
    email_status: str | None = Field(default=None)

    # ── Universal — provenance from the upstream source tool itself ──
    source_discovered_at: datetime | None = Field(default=None)

    # Lead-quality tag, cross-source. Currently set by podscan-guest ingestion
    # (prospect / public_figure / host_or_regular) so the UI can filter to real
    # prospects without dropping the public figures and show hosts. NULL for
    # sources that don't classify their leads.
    lead_tag: str | None = Field(default=None, index=True)

    # Normalized name+company, the lowest dedup tier (see dedup.py and
    # services/identity.py). Computed at ingestion from first_name+last_name+
    # company_name; NULL when either is missing — a bare name is too
    # collision-prone to merge on. Lets a recurring guest accumulate across
    # sheets/sources instead of duplicating.
    identity_key: str | None = Field(default=None, index=True)

    # ── Directory-native identity (only when the lead IS a directory listing,
    # e.g. a Clutch agency profile). For company-as-lead sources there's no
    # email or person to anchor on, so the directory's stable per-listing URL
    # is the identity — the dedup key within the source and across re-pulls
    # (see dedup.py tier 6). Prefixed like youtube_* because it exists only
    # because the lead's identity IS that directory listing. ──
    clutch_profile_url: str | None = Field(default=None, index=True)

    # ── Platform-native identity (only when the lead IS a podcast, e.g. the
    # Podscan Host source). One row = one podcast; a podcast that arrives with
    # no brand-matched email has no person or name+company key to anchor on, so
    # Podscan's stable per-podcast id (`pd_...`) is the identity — the dedup key
    # within the source and across re-pulls (see dedup.py tier 7). Prefixed like
    # clutch_profile_url because it exists only because the lead's identity IS
    # that podcast listing. ──
    podcast_id: str | None = Field(default=None, index=True)

    # ── YouTube-native identity (only when the lead IS a YouTube channel) ──
    youtube_channel_name: str | None = Field(default=None, index=True)
    youtube_channel_id: str | None = Field(default=None, index=True)
    youtube_handle: str | None = Field(default=None)
    youtube_subscriber_count: int | None = Field(default=None)
    youtube_video_count: int | None = Field(default=None)
    youtube_uploads_last_30d: int | None = Field(default=None)
    youtube_avg_views: int | None = Field(default=None)
    youtube_last_upload_date: date | None = Field(default=None)

    # ── Outreach — the opening line to send this lead. Generated on demand by a
    # named method (services/messages/), scoped to a source + list; latest run
    # overwrites (regenerate-only, no per-lead editing). Read by the Instantly
    # export. NULL until a generation is run for this lead. ──
    email_to_send: str | None = Field(default=None)

    # ── Website-content classification (ai-agents ICP classifier). Inferred from
    # the actual site, so more accurate than the source-provided `industry`.
    # classified_industry = controlled-taxonomy bucket (LLM may propose a new
    # label when none fit); icp_confidence = 0-100 paid-ads-agency score (accept
    # segment >= 60). Both indexed — they ARE the segment keys. NULL until run. ──
    classified_industry: str | None = Field(default=None, index=True)
    icp_confidence: int | None = Field(default=None, index=True)
    icp_reasoning: str | None = Field(default=None)
    icp_source: str | None = Field(default=None)  # crawl | serper
    icp_classified_at: datetime | None = Field(default=None)
