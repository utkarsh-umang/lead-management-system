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
