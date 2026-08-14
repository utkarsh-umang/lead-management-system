"""`transcript_opener` — the LLM message method that writes a personalized
`email_to_send` from the actual podcast episode the guest appeared on.

Where the deterministic openers work off canonical fields, this one reads the
episode the lead came from (its `episode_id` + the guest's diarized
`speaker_label`, carried in the source's raw row), pulls the transcript from
Podscan, isolates the GUEST'S OWN spoken lines, and asks the LLM for one
specific opener about something they actually said — not a guess from the title.

Benchmarked against title-only and YouTube-transcript sourcing on 50 guests:
title-only never misses but invents the guest's words; YouTube is vivid but
grabs the wrong video ~1-in-8; this (exact `episode_id`, guest's own turns) was
the only source with specificity AND no wrong-source risk.

All network I/O is httpx REST (no SDK deps). Every failure path returns None —
the lead is left unchanged and reported as skipped, never a hard error — so an
unconfigured key or a missing transcript can't break a batch run.
"""
from __future__ import annotations

import re

import httpx

from app.core.config import config
from app.services.messages.podscan import STOP_SENTINELS, fetch_transcript

_TS_RX = re.compile(r"\[\d\d:\d\d:\d\d\.\d+\s*-->\s*\d\d:\d\d:\d\d\.\d+\]")

_SYS = (
    "You write ONE short, genuine cold-email opener for a podcast guest, in this exact shape:\n"
    '  "<FirstName> — watched your episode about <specific insight> on the <Podcast> podcast. '
    'Honestly so good."\n'
    '  "<one short, specific follow-up sentence about that insight — 3rd-grade reading level, '
    'plain words>."\n'
    "Rules: <specific insight> must be concrete and true to the material given — NOT generic "
    "praise. Two short lines only. No greeting, no signature, no extra text."
)


def _guest_turns(transcript: str, speaker_label: str | None) -> str:
    """The guest's own spoken lines, pulled out by their diarized speaker label
    (Podscan tags every turn `[SPEAKER_NN]`). Lets the opener quote what the
    guest actually said, not what the host framed. Empty string when the label
    is missing or never appears (caller falls back to the full transcript)."""
    if not speaker_label:
        return ""
    parts = re.split(r"\[(SPEAKER_\d+)\]", transcript)
    turns = [
        _TS_RX.sub("", parts[i + 1]).strip()
        for i in range(1, len(parts) - 1, 2)
        if parts[i] == speaker_label
    ]
    return " ".join(turns)


async def _llm_opener(client: httpx.AsyncClient, user: str) -> str | None:
    try:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": config.MESSAGE_LLM_MODEL, "temperature": 0.4,
                  "messages": [{"role": "system", "content": _SYS},
                               {"role": "user", "content": user[:12000]}]},
            timeout=60,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


async def generate(ctx) -> str | None:
    """ctx: MessageContext(lead, provenance). Provenance carries the raw source
    row — we need episode_id (+ ideally speaker_label). Returns the opener or
    None (skip) when unconfigured, no episode, or no transcript."""
    if not (config.PODSCAN_API_KEY and config.OPENAI_API_KEY):
        return None
    prov = ctx.provenance or {}
    episode_id = (prov.get("episode_id") or "").strip()
    first_name = (ctx.lead.first_name or "").strip()
    if not episode_id or not first_name:
        return None
    podcast = prov.get("podcast_name") or ctx.lead.company_name or "the"
    episode_title = prov.get("episode_title") or ""
    speaker = (prov.get("speaker_label") or "").strip()

    async with httpx.AsyncClient() as client:
        # Prefer the transcript already cached on the lead (bulk-fetched by
        # transcript_store); only hit the rate-limited API when it's missing.
        transcript = (ctx.lead.episode_transcript or "").strip() or None
        if not transcript:
            transcript = await fetch_transcript(client, episode_id)
        if not transcript or transcript in STOP_SENTINELS:
            return None
        guest = _guest_turns(transcript, speaker)
        if len(guest) >= 600:
            body = f"THE GUEST'S OWN LINES (speaker {speaker}):\n{guest[:11000]}"
        else:
            body = f"EPISODE TRANSCRIPT (excerpt):\n{transcript[:11000]}"
        user = (f"FirstName: {first_name}\nPodcast: {podcast}\nEpisode title: {episode_title}\n\n"
                f"{body}\n\nPick a specific, memorable thing THIS guest actually said or argued, "
                "and write the opener about that — quote or paraphrase their actual point.")
        return await _llm_opener(client, user)
