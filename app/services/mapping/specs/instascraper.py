"""Mapping for the stable CSV produced by the Instascraper Apps Script.

One row is one Google Maps company listing. The exporter combines every city
tab, adds the tab name as scrape provenance, and extracts Google Maps' stable
place ID. Search-city, rating, address, timings, and review text remain in the
raw row until they become real targeting axes; only cross-source canonical
fields and the platform-native identity are promoted here.
"""

SOURCE_LABEL = "instascraper"

EXPECTED_HEADERS = [
    "Google Place ID",
    "Scrape City",
    "Maps Link",
    "Business Name",
    "Phone",
    "Business Type",
    "Website",
    "Rating",
    "Address",
    "Address 2",
    "Timings",
    "Reviews",
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "google_place_id", "source": "Google Place ID", "op": "text"},
        {"canonical": "google_maps_url", "source": "Maps Link", "op": "url_or_null"},
        {"canonical": "company_name", "source": "Business Name", "op": "text"},
        {"canonical": "phone", "source": "Phone", "op": "text"},
        {"canonical": "category", "source": "Business Type", "op": "text"},
        {"canonical": "website", "source": "Website", "op": "website_or_null"},
        {
            "canonical": "country",
            "source": "Business Name",
            "op": "const",
            "op_args": {"value": "United States"},
        },
    ],
}
