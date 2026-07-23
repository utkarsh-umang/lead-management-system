"""Backfill identity_key for existing leads that predate the tier-5 dedup key.

Computes the key in Python — the exact same compute_identity_key() ingestion
uses — so a backfilled Apollo lead and a future incoming row produce byte-for-
byte the same key (a hand-written SQL twin could drift and silently miss
matches). Only touches leads that have both a name and a company and no key yet.

Run: poetry run python scripts/backfill_identity_key.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.master_lead import MasterLead  # noqa: E402
from app.services.identity import compute_identity_key  # noqa: E402

BATCH = 2000


async def main() -> None:
    # Keyset pagination by id (NOT offset + a mutating WHERE filter — setting
    # identity_key removes rows from an `IS NULL` filter and an OFFSET window
    # would then skip rows). Scans every lead exactly once; idempotent, so it is
    # safe to re-run.
    updated = 0
    scanned = 0
    last_id = None
    async with AsyncSessionLocal() as session:
        while True:
            stmt = select(MasterLead).order_by(MasterLead.id).limit(BATCH)
            if last_id is not None:
                stmt = stmt.where(MasterLead.id > last_id)
            rows = (await session.execute(stmt)).scalars().all()
            if not rows:
                break
            for lead in rows:
                scanned += 1
                last_id = lead.id
                key = compute_identity_key(lead.first_name, lead.last_name, lead.company_name)
                if key and lead.identity_key != key:
                    lead.identity_key = key
                    session.add(lead)
                    updated += 1
            await session.commit()
            print(f"  scanned {scanned}, backfilled {updated} …")

    print(f"Done. Backfilled identity_key for {updated} leads (scanned {scanned}).")


if __name__ == "__main__":
    asyncio.run(main())
