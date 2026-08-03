"""Register the two hand-authored mapping functions (phase 2). Fingerprint
is computed from the real CSV headers on disk, not hand-transcribed, so it
can never drift from the actual file. Run: poetry run python scripts/seed_mapping_functions.py
"""

import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import select  # noqa: E402

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.mapping_function import MappingFunction  # noqa: E402
from app.services.mapping.fingerprint import compute_fingerprint  # noqa: E402
from app.services.mapping.specs.apollo import MAPPING_SPEC as APOLLO_SPEC  # noqa: E402
from app.services.mapping.specs.apollo import SOURCE_LABEL as APOLLO_LABEL  # noqa: E402
from app.services.mapping.specs.apollo import REAL_ESTATE_HEADERS as APOLLO_RE_HEADERS  # noqa: E402
from app.services.mapping.specs.apollo import MASTER_30K_HEADERS as APOLLO_30K_HEADERS  # noqa: E402
from app.services.mapping.specs.youtube_consulti import MAPPING_SPEC as CONSULTI_SPEC  # noqa: E402
from app.services.mapping.specs.youtube_consulti import SOURCE_LABEL as CONSULTI_LABEL  # noqa: E402
from app.services.mapping.specs.youtube_tool import MAPPING_SPEC as TOOL_SPEC  # noqa: E402
from app.services.mapping.specs.youtube_tool import SOURCE_LABEL as TOOL_LABEL  # noqa: E402
from app.services.mapping.specs.podscan_guest import CANONICAL_HEADERS as PODSCAN_HEADERS  # noqa: E402
from app.services.mapping.specs.podscan_guest import MAPPING_SPEC as PODSCAN_SPEC  # noqa: E402
from app.services.mapping.specs.podscan_guest import SOURCE_LABEL as PODSCAN_LABEL  # noqa: E402
from app.services.mapping.specs.apollo_lite import EXPECTED_HEADERS as APOLLO_LITE_HEADERS  # noqa: E402
from app.services.mapping.specs.apollo_lite import MAPPING_SPEC as APOLLO_LITE_SPEC  # noqa: E402
from app.services.mapping.specs.apollo_lite import SOURCE_LABEL as APOLLO_LITE_LABEL  # noqa: E402

SEEDS = [
    (Path.home() / "Desktop" / "youtube-tool.csv", TOOL_LABEL, TOOL_SPEC),
    (Path.home() / "Desktop" / "youtube-consulti.csv", CONSULTI_LABEL, CONSULTI_SPEC),
    (
        Path.home() / "Desktop" / "Ad Agencies -- Apollo - 1443 36k Apollo Leads.csv",
        APOLLO_LABEL,
        APOLLO_SPEC,
    ),
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for csv_path, source_label, spec in SEEDS:
            if not csv_path.exists():
                # Already-registered sources whose CSV has since left Desktop —
                # their fingerprint lives in the DB; nothing to (re)compute.
                print(f"csv gone, skipping: {source_label} ({csv_path.name})")
                continue
            with open(csv_path, encoding="utf-8-sig") as f:
                headers = next(csv.reader(f))
            fingerprint = compute_fingerprint(headers)

            existing = (
                await session.execute(
                    select(MappingFunction).where(MappingFunction.fingerprint == fingerprint)
                )
            ).scalars().first()

            if existing:
                print(f"already registered: {source_label} ({fingerprint[:12]}...)")
                continue

            session.add(
                MappingFunction(
                    fingerprint=fingerprint,
                    source_label=source_label,
                    mapping_spec=spec,
                    approved_at=datetime.utcnow(),
                )
            )
            print(f"registered: {source_label} ({fingerprint[:12]}...)")

        # Podscan Guest: the shape is code-defined (the flattener always emits
        # CANONICAL_HEADERS), so the fingerprint comes from that list, not a
        # file on disk — every flattened sheet dispatches to this one spec.
        podscan_fp = compute_fingerprint(PODSCAN_HEADERS)
        podscan_existing = (
            await session.execute(
                select(MappingFunction).where(MappingFunction.fingerprint == podscan_fp)
            )
        ).scalars().first()
        if podscan_existing:
            print(f"already registered: {PODSCAN_LABEL} ({podscan_fp[:12]}...)")
        else:
            session.add(
                MappingFunction(
                    fingerprint=podscan_fp,
                    source_label=PODSCAN_LABEL,
                    mapping_spec=PODSCAN_SPEC,
                    approved_at=datetime.utcnow(),
                )
            )
            print(f"registered: {PODSCAN_LABEL} ({podscan_fp[:12]}...)")

        # Apollo-lite: the 9-column reduced Apollo delivery shape. Header set is
        # fixed by the delivery format, so the fingerprint is code-defined (like
        # podscan). Each list in this shape sets its own label via the upload's
        # `source` form param; this spec only decides HOW to parse.
        apollo_lite_fp = compute_fingerprint(APOLLO_LITE_HEADERS)
        apollo_lite_existing = (
            await session.execute(
                select(MappingFunction).where(MappingFunction.fingerprint == apollo_lite_fp)
            )
        ).scalars().first()
        if apollo_lite_existing:
            print(f"already registered: {APOLLO_LITE_LABEL} ({apollo_lite_fp[:12]}...)")
        else:
            session.add(
                MappingFunction(
                    fingerprint=apollo_lite_fp,
                    source_label=APOLLO_LITE_LABEL,
                    mapping_spec=APOLLO_LITE_SPEC,
                    approved_at=datetime.utcnow(),
                )
            )
            print(f"registered: {APOLLO_LITE_LABEL} ({apollo_lite_fp[:12]}...)")

        # Apollo real-estate variant (20-col: +Facebook/Twitter, -Founded Year).
        # Its own fingerprint, but points back to the canonical APOLLO_SPEC.
        apollo_re_fp = compute_fingerprint(APOLLO_RE_HEADERS)
        apollo_re_existing = (
            await session.execute(
                select(MappingFunction).where(MappingFunction.fingerprint == apollo_re_fp)
            )
        ).scalars().first()
        if apollo_re_existing:
            print(f"already registered: {APOLLO_LABEL} (RE) ({apollo_re_fp[:12]}...)")
        else:
            session.add(
                MappingFunction(
                    fingerprint=apollo_re_fp,
                    source_label=APOLLO_LABEL,
                    mapping_spec=APOLLO_SPEC,
                    approved_at=datetime.utcnow(),
                )
            )
            print(f"registered: {APOLLO_LABEL} (RE) ({apollo_re_fp[:12]}...)")

        # Apollo rich 33-col master export ("30k" list) — its own fingerprint,
        # points back to the canonical APOLLO_SPEC (which maps # Employees +
        # Email Status when present).
        apollo_30k_fp = compute_fingerprint(APOLLO_30K_HEADERS)
        apollo_30k_existing = (
            await session.execute(
                select(MappingFunction).where(MappingFunction.fingerprint == apollo_30k_fp)
            )
        ).scalars().first()
        if apollo_30k_existing:
            print(f"already registered: {APOLLO_LABEL} (30k) ({apollo_30k_fp[:12]}...)")
        else:
            session.add(
                MappingFunction(
                    fingerprint=apollo_30k_fp,
                    source_label=APOLLO_LABEL,
                    mapping_spec=APOLLO_SPEC,
                    approved_at=datetime.utcnow(),
                )
            )
            print(f"registered: {APOLLO_LABEL} (30k) ({apollo_30k_fp[:12]}...)")

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
