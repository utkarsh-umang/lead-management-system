"""Google Place ID dedup keeps re-uploads and overlapping city tabs merged."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.master_lead import MasterLead
from app.services.dedup import upsert_lead


@pytest.mark.asyncio
async def test_same_place_id_merges_url_variants_and_fills_missing_fields():
    existing = MasterLead(
        company_name="Roman Commercial Roofing",
        google_place_id="ChIJKTOOesVbwokRMc8dEnLR4G0",
        google_maps_url="https://www.google.com/maps/place/roman?first-search",
        website=None,
    )
    result = MagicMock()
    result.scalars.return_value.first.return_value = existing
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    lead, is_new = await upsert_lead(
        session,
        {
            "company_name": "Roman Roofing should not overwrite",
            "google_place_id": "ChIJKTOOesVbwokRMc8dEnLR4G0",
            "google_maps_url": "https://www.google.com/maps/place/roman?second-search",
            "website": "https://romancommercialroofing.com",
        },
    )

    assert lead is existing
    assert is_new is False
    assert lead.company_name == "Roman Commercial Roofing"
    assert lead.google_maps_url == "https://www.google.com/maps/place/roman?first-search"
    assert lead.website == "https://romancommercialroofing.com"
    session.flush.assert_awaited_once()
