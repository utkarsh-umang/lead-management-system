"""Bulk-fetch Podscan episode transcripts into `master_leads.episode_transcript`.

Transcripts are per-EPISODE, but a guest list is per-appearance: the same
episode can carry several guests (co-hosts, panels, a host who's also a guest
elsewhere). So the unit of API work is the UNIQUE episode, not the lead — we
fetch each episode's transcript ONCE and fan it out to every lead that came from
it. On the 1,941-lead top-25 set that's 1,450 calls instead of 1,941, and it
compounds on the full list.

The fetch honors the same rate-limit backoff as the opener (shared podscan.py)
and stops early if the key's plan can't serve transcripts, so a trial key that
runs out mid-run reports what it managed rather than grinding to the end.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx

from app.models.master_lead import MasterLead
from app.services.messages.podscan import PAID_PLAN_REQUIRED, fetch_transcript


@dataclass
class TranscriptFetchResult:
    total_leads: int          # leads in the list
    leads_with_episode: int   # leads carrying an episode_id (fetch candidates)
    unique_episodes: int      # distinct episodes among them (== API calls attempted)
    episodes_fetched: int     # episodes we actually got a transcript for
    leads_written: int        # leads whose episode_transcript we set
    stopped_paid_plan: bool   # the key's plan can't serve transcripts — run halted


async def fetch_and_store(
    session,
    leads: list[MasterLead],
    provenance: dict[uuid.UUID, dict],
    *,
    max_episodes: int | None = None,
) -> TranscriptFetchResult:
    """Fetch the transcript for each unique episode among `leads` (deduped on
    episode_id) and write it onto every lead sharing that episode. `max_episodes`
    bounds the number of API calls — the safety valve for the rate-limited trial
    key. Leads already carrying a transcript are skipped (idempotent re-runs)."""
    # episode_id -> the leads that need it (skip leads already cached).
    by_episode: dict[str, list[MasterLead]] = {}
    leads_with_episode = 0
    for lead in leads:
        episode_id = (provenance.get(lead.id, {}).get("episode_id") or "").strip()
        if not episode_id:
            continue
        leads_with_episode += 1
        if (lead.episode_transcript or "").strip():
            continue
        by_episode.setdefault(episode_id, []).append(lead)

    episode_ids = list(by_episode.keys())
    if max_episodes is not None:
        episode_ids = episode_ids[:max_episodes]

    episodes_fetched = 0
    leads_written = 0
    stopped_paid_plan = False

    async with httpx.AsyncClient() as client:
        for episode_id in episode_ids:
            transcript = await fetch_transcript(client, episode_id)
            if transcript == PAID_PLAN_REQUIRED:
                stopped_paid_plan = True
                break
            if not transcript:
                continue
            episodes_fetched += 1
            for lead in by_episode[episode_id]:
                lead.episode_transcript = transcript
                session.add(lead)
                leads_written += 1

    await session.commit()

    return TranscriptFetchResult(
        total_leads=len(leads),
        leads_with_episode=leads_with_episode,
        unique_episodes=len(by_episode),
        episodes_fetched=episodes_fetched,
        leads_written=leads_written,
        stopped_paid_plan=stopped_paid_plan,
    )
