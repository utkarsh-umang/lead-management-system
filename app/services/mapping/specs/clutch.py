"""Mapping spec for the Clutch.co directory scrape — a *company*-as-lead source
(the lead is an advertising agency, not a person). Distinct from every other
spec so far, which are person-centric.

The CSV is a raw scraper dump: its 79 headers are DOM/CSS class names, and only
a couple carry the identity we canonicalize — the rest (rating, review count,
min project size, services breakdown, description, per-review snippets) are
recoverable from raw_rows but not promoted, per the Master Schema "don't bloat
canonical with source-specific extras" rule. Promoting rating / min-project /
services later (for targeting) is a one-line add if outreach segmentation needs
it.

Identity: these leads have no email, no person, and no external website, so
NONE of the person/YouTube dedup tiers fire. The Clutch profile URL
('sg-provider-logotype-v2 href', e.g. https://clutch.co/profile/power-digital)
is the stable per-agency key — it maps to the canonical `clutch_profile_url`
column and is dedup tier 6 (see dedup.py). `website` is deliberately left NULL:
it's the agency's *real* site, which this scrape doesn't carry — the later
resolution step (profile -> website -> email) fills it.

Because the header set is fixed by the scraper's output, the fingerprint is
computed from EXPECTED_HEADERS (code-defined, like podscan_guest / apollo_lite),
so every pull in this shape dispatches here.

Provenance: `source` is the directory (Clutch); a specific pull ("Ad Agencies")
is a batch under it, identified by the batch filename in the UI.
"""

SOURCE_LABEL = "clutch"

# The exact 79-column header row this scraper emits, in file order. The
# fingerprint is order-independent (fingerprint.py sorts), but file order here
# keeps the shape self-documenting.
EXPECTED_HEADERS = [
    'sg-provider-logotype-v2 href', 'sg-provider-logotype-v2 src', 'provider__title-link',
    'sg-rating__number', 'sg-rating__stars href', 'sg-rating__reviews',
    'provider__highlights-item', 'provider__highlights-item 2', 'provider__highlights-item 3',
    'provider__highlights-item 4', 'provider__services-list-item', 'provider__services-list-item 2',
    'provider__services-list-item 3', 'provider__services-list-item-more', 'provider__services-list-item 4',
    'provider__services-list-item 5', 'provider__services-list-item 6', 'provider__description-text-more',
    'show-more-button-summary', 'provider__project-highlight-projects-link', 'provider__services-list-item 7',
    'provider__services-list-item 8', 'provider__services-list-item 9', 'sg-tabs-expanded__tab',
    'provider-insight__summary', 'provider-insight__title', 'provider-insight__review-title',
    'provider-insight__review-details', 'provider-insight__review-date', 'provider-insight__review-snippet',
    'provider-insight__review-snippet 2', 'provider-insight__review-show-full-review', 'provider-insight__review-show-full-review href',
    'provider-insight__review-snippet 4', 'provider__cta-link 3', 'provider__cta-link href 3',
    'feedback__message', 'sg-tabs-expanded__tab 3', 'features__item 3',
    'features__item 4', 'provider-insight__subtitle', 'provider-insight__title 3',
    'provider-insight-highlight-rating', 'provider-insight__highlight-more-link', 'provider-insight__highlight-more-link href',
    'provider__cta-link 5', 'provider__cta-link href 5', 'feedback__message 3',
    'sg-tabs-expanded__tab 4', 'provider-insight__title 4', 'provider-insight__text',
    'provider-insight__cta-link', 'provider-insight__cta-link href', 'provider-insight__back-button',
    'provider-insight__title 5', 'provider-insight__industry-token', 'provider-insight__industry-token 2',
    'provider-insight__industry-token 3', 'provider-insight__industry-token 4', 'feedback__message 4',
    'provider__less-more-button', 'sg-tabs-expanded__tab 5', 'statistic__title',
    'statistic__item', 'statistic__item href', 'statistic__item 2',
    'statistic__item href 2', 'provider-insight__summary 3', 'provider-insight__title 6',
    'provider__cta-link 6', 'provider__cta-link href 6', 'feedback__message 5',
    'sg-tabs-expanded__tab 8', 'insight-countries__title', 'insight-countries__country',
    'insight-countries__country href', 'insight-countries__country 2', 'insight-countries__country href 2',
    'feedback__message 8',
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "company_name", "source": "provider__title-link", "op": "text"},
        {"canonical": "clutch_profile_url", "source": "sg-provider-logotype-v2 href", "op": "url_or_null"},
    ],
}
