"""Mapping spec for the Podscan Host source — one row = one podcast (the show
itself is the lead, reachable at its own `Podcast Email`). Sibling of
podscan-guest (one row = one guest), but Host rows arrive WITH candidate emails,
so this spec's job is to keep only the ones that actually belong to the show.

That pick is a cross-field decision (which of the listed emails brand-matches
the podcast name/website?), so it can't be a per-column op — it runs through
`row_qualifier: podscan_host_qualify` (a faithful port of the user's
`qualifyPodcastLeads` Apps Script). A brand match becomes the lead's email with
email_source='provided' (send-ready, excluded from the finder). No match / no
email leaves email NULL, so the lead falls through to the finder queue — the
"Needs_Enrichment" bucket.

Identity: `podcast_id` (Podscan's stable `pd_...`) anchors the podcast so a
brand-less re-pull dedups instead of duplicating (dedup.py tier 7); a qualified
lead also anchors on its email (tier 1).

Raw-only (recoverable from raw_rows, not promoted): every Episode/Mention/Alert/
Topic/Entity/Publisher column — per-appearance provenance, same anti-bloat rule
as the other specs. The header set is fixed by the Podscan export, so the
fingerprint is code-defined from EXPECTED_HEADERS (like clutch / podscan_guest).
"""

SOURCE_LABEL = "podscan-host"

# The exact Podscan Host export header row (the real header lives on line 2 of
# the file, under an Excel `sep=;` hint line the uploader strips). Fingerprint
# is order-independent (fingerprint.py sorts); file order kept for readability.
EXPECTED_HEADERS = [
    "Type", "Added to Collection", "Item ID", "Podcast Name", "Podcast ID",
    "Podcast Website", "Podcast Email", "Podcast Facebook", "Podcast Twitter",
    "Podcast Instagram", "Podcast YouTube", "Podcast LinkedIn", "Episode ID",
    "Episode Title", "Episode Published Date", "Episode Duration",
    "Episode Description", "Mention ID", "Mention Detected At",
    "Mention Excerpt", "Mention Type", "Mention Filter", "Alert ID",
    "Alert Name", "Alert Status", "Alert Created At", "Topic ID", "Topic Name",
    "Topic Description", "Entity ID", "Entity Name", "Entity Type",
    "Publisher ID", "Publisher Name", "Publisher Website",
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "company_name", "source": "Podcast Name", "op": "text"},
        {"canonical": "podcast_id", "source": "Podcast ID", "op": "text"},
        {"canonical": "website", "source": "Podcast Website", "op": "website_or_null"},
        {"canonical": "social_facebook", "source": "Podcast Facebook", "op": "url_or_null"},
        {"canonical": "social_twitter", "source": "Podcast Twitter", "op": "url_or_null"},
        {"canonical": "social_instagram", "source": "Podcast Instagram", "op": "url_or_null"},
        {"canonical": "social_youtube", "source": "Podcast YouTube", "op": "url_or_null"},
        {"canonical": "social_linkedin", "source": "Podcast LinkedIn", "op": "url_or_null"},
        {"canonical": "lead_tag", "source": "Type", "op": "const", "op_args": {"value": "podcast_host"}},
    ],
    # Cross-field brand-match email pick (sets email + email_source). Runs after
    # the field ops above; see services/mapping/qualifiers.py.
    "row_qualifier": "podscan_host_qualify",
}
