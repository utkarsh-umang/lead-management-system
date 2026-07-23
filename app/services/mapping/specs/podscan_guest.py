"""Mapping spec for the Podscan Guest source.

Unlike the other sources, this CSV is NOT a raw vendor export — it is the
canonical, fixed-shape output of the enricher's Podscan sheet flattener
(lead-enricher-ai-be: podscan/sheet_flattener.py). Podscan ships a different
Google Sheet every time (26 podcast tabs, guests packed inside a JSON column);
the flattener absorbs all that variety and always emits these same columns, so
the LMS only ever needs this one spec and the fingerprint never drifts.

One row = one guest (already deduped within the sheet on name+company by the
flattener). The lead is a person, so this populates the person/company columns
like Apollo does — plus lead_tag, which the flattener sets to prospect /
public_figure / host_or_regular so the UI can filter to real prospects without
dropping anyone.

Deliberately raw-only (recoverable from raw_rows, not promoted to canonical —
same anti-bloat rule as Master Schema.md): guest_name (first/last cover
identity), other_social, and all the per-appearance provenance
(podcast_name, episode_*, speaker_label, appearance_count, all_appearances_json,
dedup_key). There is no email column — Podscan guests never arrive with one;
they enter as "No Email Yet" and wait for the finder.
"""

SOURCE_LABEL = "podscan-guest"

# The canonical column set emitted by podscan/sheet_flattener.py. Must stay in
# sync with that flattener's CANONICAL_COLUMNS — the fingerprint (seed script)
# is computed from this list, and a mismatch would make an uploaded flattened
# CSV fail to dispatch to this spec.
CANONICAL_HEADERS = [
    "source",
    "dedup_key",
    "lead_tag",
    "guest_name",
    "first_name",
    "last_name",
    "company",
    "job_title",
    "industry",
    "linkedin",
    "twitter",
    "instagram",
    "website",
    "other_social",
    "appearance_count",
    "podcast_name",
    "podcast_id",
    "episode_title",
    "episode_url",
    "episode_published_at",
    "episode_id",
    "speaker_label",
    "all_appearances_json",
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "first_name", "source": "first_name", "op": "text"},
        {"canonical": "last_name", "source": "last_name", "op": "text"},
        {"canonical": "company_name", "source": "company", "op": "text"},
        {"canonical": "job_title", "source": "job_title", "op": "text"},
        {"canonical": "industry", "source": "industry", "op": "text"},
        {"canonical": "social_linkedin", "source": "linkedin", "op": "url_or_null"},
        {"canonical": "social_twitter", "source": "twitter", "op": "url_or_null"},
        {"canonical": "social_instagram", "source": "instagram", "op": "url_or_null"},
        {"canonical": "website", "source": "website", "op": "website_or_null"},
        {"canonical": "lead_tag", "source": "lead_tag", "op": "text"},
    ],
}
