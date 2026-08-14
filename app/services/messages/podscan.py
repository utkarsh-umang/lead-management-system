"""Shared Podscan API access — the single place that pulls an episode transcript.

Both callers use this: `transcript_store` bulk-fetches transcripts (deduped by
episode) into `master_leads.episode_transcript`, and `transcript_opener` falls
back to it when a lead has no cached transcript yet. Keeping the fetch here means
one implementation of the rate-limit backoff and the lenient JSON parse.
"""
from __future__ import annotations

import asyncio
import json
import re

import httpx

from app.core.config import config

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/121.0 Safari/537.36")

# Distinguishes "the API told us to slow down / upgrade" from "no transcript".
PAID_PLAN_REQUIRED = "paid-plan-required"


async def fetch_transcript(client: httpx.AsyncClient, episode_id: str) -> str | None:
    """Full episode transcript for `episode_id`, honoring the API's per-minute
    rate limit ('Retry after N second(s)'). Returns the transcript string, None
    when the episode has none, or the PAID_PLAN_REQUIRED sentinel when the key's
    plan can't serve transcripts (so a bulk run can stop early instead of
    grinding through every episode)."""
    url = f"{config.PODSCAN_API_BASE}/episodes/{episode_id}"
    headers = {"Authorization": f"Bearer {config.PODSCAN_API_KEY}", "User-Agent": _UA}
    for _ in range(8):
        try:
            r = await client.get(url, headers=headers, timeout=60)
            # strict=False: some transcripts carry raw control chars that would
            # break strict JSON parsing.
            data = json.loads(r.text, strict=False)
        except Exception:
            await asyncio.sleep(1.5)
            continue
        msg = data.get("message", "") if isinstance(data, dict) else ""
        if msg:
            low = msg.lower()
            if "paid plan" in low:
                return PAID_PLAN_REQUIRED
            if "limit" in low:
                m = re.search(r"retry after (\d+)", low)
                await asyncio.sleep((int(m.group(1)) if m else 6) + 1)
                continue
        ep = data.get("episode", data) if isinstance(data, dict) else {}
        t = ep.get("episode_transcript") if isinstance(ep, dict) else None
        return t if isinstance(t, str) and len(t) > 200 else None
    return None
