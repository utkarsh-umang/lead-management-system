"""Instascraper's combined Google Maps CSV through the real interpreter."""

from app.services.mapping.fingerprint import compute_fingerprint
from app.services.mapping.interpreter import apply_mapping
from app.services.mapping.specs.instascraper import EXPECTED_HEADERS, MAPPING_SPEC


def _row(**overrides):
    row = {
        "Google Place ID": "ChIJKTOOesVbwokRMc8dEnLR4G0",
        "Scrape City": "1. New York City",
        "Maps Link": "https://www.google.com/maps/place/Roman+Commercial+Roofing/data=!19sChIJKTOOesVbwokRMc8dEnLR4G0",
        "Business Name": "Roman Commercial Roofing",
        "Phone": "+1 917-440-1800",
        "Business Type": "Roofing contractor",
        "Website": "https://www.romancommercialroofing.com/",
        "Rating": "5",
        "Address": "7 Harrison St # 2n",
        "Address 2": "",
        "Timings": "Open 24 hours",
        "Reviews": "On-site services",
    }
    row.update(overrides)
    return row


def test_maps_company_maps_to_canonical_fields():
    out = apply_mapping(MAPPING_SPEC, _row())

    assert out == {
        "google_place_id": "ChIJKTOOesVbwokRMc8dEnLR4G0",
        "google_maps_url": "https://www.google.com/maps/place/Roman+Commercial+Roofing/data=!19sChIJKTOOesVbwokRMc8dEnLR4G0",
        "company_name": "Roman Commercial Roofing",
        "phone": "+1 917-440-1800",
        "category": "Roofing contractor",
        "website": "https://www.romancommercialroofing.com/",
        "country": "United States",
    }


def test_optional_company_fields_become_null_without_losing_identity():
    out = apply_mapping(
        MAPPING_SPEC,
        _row(Phone="", Website="", **{"Business Type": ""}),
    )

    assert out["google_place_id"] == "ChIJKTOOesVbwokRMc8dEnLR4G0"
    assert out["phone"] is None
    assert out["website"] is None
    assert out["category"] is None


def test_export_header_fingerprint_ignores_incidental_whitespace_and_order():
    shuffled = [f" {header} " for header in reversed(EXPECTED_HEADERS)]

    assert compute_fingerprint(shuffled) == compute_fingerprint(EXPECTED_HEADERS)
