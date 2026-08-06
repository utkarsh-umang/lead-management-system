"""Tiered exact-match dedup — deterministic string comparison, never fuzzy
scoring (see Lead Management System.md for why).

Tiers, in order:
1. email — highest confidence, universal across every future source.
2. social_linkedin — the person's LinkedIn profile URL, normalized
   (scheme/www/trailing-slash stripped, lowercased) then exact-matched.
   Same-namespace identity for person-centric sources (Apollo), the way
   channel_id is for YouTube-native ones. company_linkedin is deliberately
   NOT an identity tier — many distinct people share one company profile.
3. youtube_channel_id / youtube_handle — same-namespace identity match
   within YouTube-native sources. Stronger than name matching, but only
   comparable within the same identifier space (channel_id from our own
   tool, @handle from consulti — they don't cross-resolve without hitting
   YouTube's API, which is out of scope for now).
4. youtube_channel_name — weakest tier, but the only one that can match
   *across* youtube-tool and youtube-consulti, since they don't share an
   identifier space. Case/whitespace-normalized exact match.
5. identity_key (name+company) — the only tier that can merge a person who
   arrives with neither email, LinkedIn, nor a YouTube identity (the podcast
   guests). Exact match on the normalized name+company key computed at
   ingestion; only fires when both a name and a company are present, so bare
   names never fuse strangers (see services/identity.py). Global, not
   source-siloed: a guest who is also an Apollo contact merges here.
6. clutch_profile_url — directory-native identity for company-as-lead sources
   (the Clutch agency scrape). Those leads have no email, no person, and no
   name+company key (no person name), so tiers 1-5 never fire; the Clutch
   profile URL is the only stable anchor — it dedups the list against itself
   and against future re-pulls. Exact match: the scraper emits one consistent
   URL format, so no normalization twin is needed (unlike LinkedIn). Only fires
   when a clutch_profile_url is present.
7. podcast_id — platform-native identity for the Podscan Host source (one row =
   one podcast). A podcast that arrives without a brand-matched email has no
   email/person/name-key either, so tiers 1-5 miss it; Podscan's stable per-
   podcast id (`pd_...`) is the anchor that keeps re-pulls from duplicating it.
   Exact match (one consistent id format). Only fires when a podcast_id is
   present.

On a match: upsert, existing values win — the new source only fills fields
that are currently NULL. On no match: insert a new MasterLead.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.master_lead import MasterLead


def normalize_linkedin_url(url: str) -> str:
    """https://www.linkedin.com/in/foo/ and http://linkedin.com/in/foo are
    the same profile — strip scheme, www., and trailing slash, lowercase."""
    v = url.strip().lower()
    # replace() not lstrip-of-prefix, so this stays the exact twin of the
    # SQL expression below (SQL replace() is all-occurrences).
    v = v.replace("https://", "").replace("http://", "").replace("www.", "")
    return v.rstrip("/")


def _sql_normalized_linkedin(column):  # noqa: ANN001, ANN202 — SQLA expression in/out
    """The SQL twin of normalize_linkedin_url, applied to the stored column
    (which keeps the original URL as uploaded)."""
    v = func.lower(func.trim(column))
    v = func.replace(func.replace(v, "https://", ""), "http://", "")
    v = func.replace(v, "www.", "")
    return func.rtrim(v, "/")


async def find_matching_lead(session: AsyncSession, canonical: dict) -> MasterLead | None:
    email = canonical.get("email")
    if email:
        result = await session.execute(select(MasterLead).where(MasterLead.email == email))
        existing = result.scalars().first()
        if existing:
            return existing

    linkedin = canonical.get("social_linkedin")
    if linkedin:
        result = await session.execute(
            select(MasterLead).where(
                _sql_normalized_linkedin(MasterLead.social_linkedin)
                == normalize_linkedin_url(linkedin)
            )
        )
        existing = result.scalars().first()
        if existing:
            return existing

    channel_id = canonical.get("youtube_channel_id")
    if channel_id:
        result = await session.execute(
            select(MasterLead).where(MasterLead.youtube_channel_id == channel_id)
        )
        existing = result.scalars().first()
        if existing:
            return existing

    handle = canonical.get("youtube_handle")
    if handle:
        result = await session.execute(
            select(MasterLead).where(MasterLead.youtube_handle == handle)
        )
        existing = result.scalars().first()
        if existing:
            return existing

    name = canonical.get("youtube_channel_name")
    if name:
        normalized = name.strip().lower()
        result = await session.execute(
            select(MasterLead).where(
                func.lower(func.trim(MasterLead.youtube_channel_name)) == normalized
            )
        )
        existing = result.scalars().first()
        if existing:
            return existing

    # Tier 5: name+company. Plain equality on the stored, pre-normalized key
    # (see services/identity.py) — no SQL normalization twin needed, and the
    # btree index on identity_key makes it an index lookup, not a scan.
    identity_key = canonical.get("identity_key")
    if identity_key:
        result = await session.execute(
            select(MasterLead).where(MasterLead.identity_key == identity_key)
        )
        existing = result.scalars().first()
        if existing:
            return existing

    # Tier 6: Clutch profile URL — directory-native identity for company-as-lead
    # sources with no email/person/name-key. Plain equality (single consistent
    # scraper format); indexed, so an index lookup.
    clutch_profile_url = canonical.get("clutch_profile_url")
    if clutch_profile_url:
        result = await session.execute(
            select(MasterLead).where(MasterLead.clutch_profile_url == clutch_profile_url)
        )
        existing = result.scalars().first()
        if existing:
            return existing

    # Tier 7: Podscan podcast id — platform-native identity for the Podscan Host
    # source. Plain equality (one consistent id format); indexed lookup. Only
    # fires when a podcast_id is present.
    podcast_id = canonical.get("podcast_id")
    if podcast_id:
        result = await session.execute(
            select(MasterLead).where(MasterLead.podcast_id == podcast_id)
        )
        existing = result.scalars().first()
        if existing:
            return existing

    return None


async def upsert_lead(
    session: AsyncSession, canonical: dict, enrichment_hold: bool = False
) -> tuple[MasterLead, bool]:
    """Returns (lead, is_new). enrichment_hold applies to NEW leads only —
    a merge never retroactively holds a lead that was already eligible."""
    existing = await find_matching_lead(session, canonical)
    if existing is None:
        lead = MasterLead(**canonical, enrichment_hold=enrichment_hold)
        session.add(lead)
        await session.flush()  # get lead.id without committing
        return lead, True

    for field, value in canonical.items():
        if value is not None and getattr(existing, field) is None:
            setattr(existing, field, value)
    session.add(existing)
    await session.flush()
    return existing, False
