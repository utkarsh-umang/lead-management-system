"""Fetch one daily tranche of Podscan episode transcripts into master_leads.

The Podscan free/trial key has a ~100 requests/DAY cap. This script fetches as
many uncached episodes as the key will serve in one run, then stops the instant
the API reports a hard cap (fetch_transcript returns a STOP_SENTINELS value) —
so it grabs one day's allotment and exits, whether run right after a quota reset
or (harmlessly, doing nothing) before one. Scheduled a few times a day (cron),
it drains the backlog ~100/day and finishes on its own; on a paid key one run
completes the whole remainder.

Deduped by episode (one API call per unique episode, fanned out to every guest
of it), commits per episode, idempotent — already-cached leads are excluded by
the query, so it always resumes cleanly.

Scope defaults to the podscan-guest batch + top-25 export; override via env
TRANSCRIPT_BATCH_ID / TRANSCRIPT_EXPORT_ID (export id optional — unset = whole
batch). MAX_PER_RUN is a runaway guard on top of the API's own daily cap.

Run: poetry run python scripts/fetch_transcript_tranche.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from sqlalchemy import text, update  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.master_lead import MasterLead  # noqa: E402
from app.services.messages.podscan import STOP_SENTINELS, fetch_transcript  # noqa: E402

BATCH_ID = os.environ.get("TRANSCRIPT_BATCH_ID", "29231ba4-cabb-4d22-9b84-7aec336cf332")
EXPORT_ID = os.environ.get("TRANSCRIPT_EXPORT_ID", "48a0a31d-b391-470a-8ada-2df89abcd173")
MAX_PER_RUN = int(os.environ.get("TRANSCRIPT_MAX_PER_RUN", "300"))

# Uncached leads in scope, grouped by episode. export_id filter is applied only
# when EXPORT_ID is set.
_SCOPE_SQL = """
    SELECT rr.raw_data->>'episode_id' AS episode_id, ls.lead_id
    FROM lead_sources ls
    JOIN raw_rows rr ON rr.id = ls.row_id
    JOIN master_leads ml ON ml.id = ls.lead_id
    WHERE ls.batch_id = :batch_id
      {export_filter}
      AND rr.raw_data ? 'episode_id'
      AND (rr.raw_data->>'episode_id') <> ''
      AND ml.episode_transcript IS NULL
"""


def _log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}", flush=True)


async def main() -> None:
    params = {"batch_id": BATCH_ID}
    export_filter = ""
    if EXPORT_ID:
        export_filter = "AND ls.lead_id IN (SELECT lead_id FROM export_leads WHERE export_id = :export_id)"
        params["export_id"] = EXPORT_ID
    sql = text(_SCOPE_SQL.format(export_filter=export_filter))

    async with AsyncSessionLocal() as session:
        rows = (await session.execute(sql, params)).all()

    by_episode: dict[str, list] = {}
    for episode_id, lead_id in rows:
        by_episode.setdefault(episode_id, []).append(lead_id)

    episodes = list(by_episode.keys())[:MAX_PER_RUN]
    _log(f"START uncached_episodes={len(by_episode)} leads={len(rows)} this_run={len(episodes)}")

    fetched = written = empty = 0
    stop_reason = None
    async with httpx.AsyncClient() as client:
        for episode_id in episodes:
            transcript = await fetch_transcript(client, episode_id)
            if transcript in STOP_SENTINELS:
                stop_reason = transcript
                break
            if not transcript:
                empty += 1
                continue
            ids = by_episode[episode_id]
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(MasterLead).where(MasterLead.id.in_(ids)).values(episode_transcript=transcript)
                )
                await session.commit()
            fetched += 1
            written += len(ids)

    remaining = len(by_episode) - fetched
    _log(f"END fetched={fetched} leads_written={written} no_transcript={empty} "
         f"stop_reason={stop_reason or 'none'} uncached_remaining={remaining}")


if __name__ == "__main__":
    asyncio.run(main())
