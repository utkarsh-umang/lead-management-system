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

# Sentinels that mean "stop the whole run" (the key is capped/insufficient) —
# distinct from None, which means "this one episode has no transcript". A bulk
# caller should halt on any of these rather than grind through every episode.
PAID_PLAN_REQUIRED = "paid-plan-required"      # plan can't serve transcripts at all
DAILY_LIMIT_EXCEEDED = "daily-limit-exceeded"  # per-day quota hit (trial keys) — a HARD cap
STOP_SENTINELS = frozenset({PAID_PLAN_REQUIRED, DAILY_LIMIT_EXCEEDED})

# Only wait out a rate limit if it clears soon; anything longer is a hard cap
# (a daily/quota reset hours away), and a bulk run must stop, not sleep on it.
_MAX_BACKOFF_SECONDS = 90


async def fetch_transcript(client: httpx.AsyncClient, episode_id: str) -> str | None:
    """Full episode transcript for `episode_id`. Returns the transcript string;
    None when the episode simply has none; or a STOP_SENTINELS value when the key
    is out of capacity (daily quota / plan too low), so a bulk run halts cleanly
    instead of backing off for hours on a limit that won't clear this run.

    Handles two limit shapes: a short per-minute rate limit (wait it out, up to
    _MAX_BACKOFF_SECONDS) vs a hard cap like `daily_limit_exceeded` with a
    multi-hour `retry_after` (stop immediately)."""
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
        if not isinstance(data, dict):
            return None
        err = str(data.get("error") or "").lower()
        msg = str(data.get("message") or "")
        low = msg.lower()
        if err or msg:
            if "paid plan" in low:
                return PAID_PLAN_REQUIRED
            # Hard daily/quota cap — resets hours away, not this run.
            if "daily" in err or "daily" in low or "quota" in err:
                return DAILY_LIMIT_EXCEEDED
            if "limit" in err or "limit" in low or r.status_code == 429:
                # Prefer the structured retry_after; fall back to "retry after N".
                retry_after = data.get("retry_after")
                if not isinstance(retry_after, (int, float)):
                    m = re.search(r"retry after (\d+)", low)
                    retry_after = int(m.group(1)) if m else 6
                if retry_after > _MAX_BACKOFF_SECONDS:
                    # Won't clear soon — treat as a hard cap, don't grind.
                    return DAILY_LIMIT_EXCEEDED
                await asyncio.sleep(retry_after + 1)
                continue
        ep = data.get("episode", data)
        t = ep.get("episode_transcript") if isinstance(ep, dict) else None
        return t if isinstance(t, str) and len(t) > 200 else None
    return None
