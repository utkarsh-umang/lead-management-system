"""Mapping spec for the *reduced* Apollo delivery export — the 9-column shape
Apollo lead-delivery services hand back (e.g. the Commercial Roofers list):
First Name, Last Name, Title, Headline, Company Name, Email, Person Linkedin
Url, Website, Company Linkedin Url.

Same person-centric canonical mapping as the full `apollo` spec, minus the
columns this shape doesn't carry (Seniority, Company Phone, Company Founded
Year, Industry, Keywords, City/State/Country, Company City/State). Because the
header set is fixed by the delivery format, the fingerprint is computed from
`EXPECTED_HEADERS` (code-defined, like podscan_guest) — so every list arriving
in this shape dispatches here and gets its own list identity from the upload's
`source` form param, not from this spec's default label.

Dedup identity: email, then normalized Person Linkedin Url. Headline is
deliberately raw-only (free-text LinkedIn headline — recoverable from raw_rows,
not worth a canonical column), matching the full apollo spec.
"""

SOURCE_LABEL = "apollo-lite"

# The exact header row this delivery format emits, in file order. The fingerprint
# is order-independent (fingerprint.py sorts), but keeping file order here makes
# the shape self-documenting.
EXPECTED_HEADERS = [
    "First Name",
    "Last Name",
    "Title",
    "Headline",
    "Company Name",
    "Email",
    "Person Linkedin Url",
    "Website",
    "Company Linkedin Url",
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "first_name", "source": "First Name", "op": "text"},
        {"canonical": "last_name", "source": "Last Name", "op": "text"},
        {"canonical": "job_title", "source": "Title", "op": "text"},
        {"canonical": "company_name", "source": "Company Name", "op": "text"},
        {"canonical": "email", "source": "Email", "op": "email_or_null"},
        {"canonical": "social_linkedin", "source": "Person Linkedin Url", "op": "url_or_null"},
        {"canonical": "company_linkedin", "source": "Company Linkedin Url", "op": "url_or_null"},
        {"canonical": "website", "source": "Website", "op": "website_or_null"},
    ],
}
