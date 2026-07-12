"""Tiered exact-match dedup — deterministic string comparison, never fuzzy
scoring (see Lead Management System.md for why).

Tiers, in order:
1. email — highest confidence, universal across every future source.
2. youtube_channel_id / youtube_handle — same-namespace identity match
   within YouTube-native sources. Stronger than name matching, but only
   comparable within the same identifier space (channel_id from our own
   tool, @handle from consulti — they don't cross-resolve without hitting
   YouTube's API, which is out of scope for now).
3. youtube_channel_name — weakest tier, but the only one that can match
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


async def find_matching_lead(session: AsyncSession, canonical: dict) -> MasterLead | None:
    email = canonical.get("email")
    if email:
        result = await session.execute(select(MasterLead).where(MasterLead.email == email))
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
