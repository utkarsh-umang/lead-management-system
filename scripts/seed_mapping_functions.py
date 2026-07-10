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
from app.services.mapping.specs.youtube_consulti import MAPPING_SPEC as CONSULTI_SPEC  # noqa: E402
from app.services.mapping.specs.youtube_consulti import SOURCE_LABEL as CONSULTI_LABEL  # noqa: E402
from app.services.mapping.specs.youtube_tool import MAPPING_SPEC as TOOL_SPEC  # noqa: E402
from app.services.mapping.specs.youtube_tool import SOURCE_LABEL as TOOL_LABEL  # noqa: E402

SEEDS = [
    (Path.home() / "Desktop" / "youtube-tool.csv", TOOL_LABEL, TOOL_SPEC),
    (Path.home() / "Desktop" / "youtube-consulti.csv", CONSULTI_LABEL, CONSULTI_SPEC),
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for csv_path, source_label, spec in SEEDS:
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

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
