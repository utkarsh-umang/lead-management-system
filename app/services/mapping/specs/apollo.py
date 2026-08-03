"""Canonical mapping spec for Apollo people exports (the lead is a person at a
company, not a YouTube channel) — populates the person/company canonical columns
and none of the youtube_* ones.

Apollo ships several header variants: the original 19-column export, and a
20-column real-estate variant that drops Company Founded Year but adds Facebook
Url + Twitter Url. This ONE spec serves all of them — the interpreter reads each
field via ``raw_row.get(source)``, so a column a given variant doesn't have just
maps to None. Each variant's header signature is registered as its own
fingerprint pointing back to this spec (see ``*_HEADERS`` below + the seed
script); adding a future variant = one more header list + one more registration,
never a new spec. The 9-column reduced delivery shape has its own thin spec
(``apollo_lite``) only because it predates this consolidation.

Dedup identity: email, then normalized Person Linkedin Url (100% filled in the
real exports).

Deliberately raw-only (recoverable from raw_rows, not canonical): Headline
(free-text LinkedIn headline), Keywords (huge Apollo-derived tag blob), Company
Founded Year, and the City/State columns — promoting source-specific extras is
the schema bloat Master Schema.md warns about. Industry maps to canonical
`industry`, NOT niche/category, which carry YouTube-native taxonomy.
"""

SOURCE_LABEL = "apollo"

# The header signatures this spec serves, in file order (fingerprint.py sorts, so
# order here is just documentation). Each is registered → this spec in the seed.
FULL_HEADERS = [
    "First Name", "Last Name", "Title", "Headline", "Company Name", "Email",
    "Seniority", "Company Phone", "Company Founded Year", "Industry", "Keywords",
    "Person Linkedin Url", "Website", "Company Linkedin Url",
    "City", "State", "Country", "Company City", "Company State",
]
# Real-estate variant: no Company Founded Year; adds Facebook Url + Twitter Url.
REAL_ESTATE_HEADERS = [
    "First Name", "Last Name", "Title", "Headline", "Company Name", "Email",
    "Seniority", "Company Phone", "Industry", "Keywords",
    "Person Linkedin Url", "Website", "Company Linkedin Url",
    "Facebook Url", "Twitter Url",
    "City", "State", "Country", "Company City", "Company State",
]
# The rich 33-column master export (the "30k" list): everything the RE variant
# has, plus ID, Full Name, Email Status, Primary Email Source, Languages, Stage,
# # Employees, Company Founded Year, Company Country, Annual Revenue, and the
# headcount-growth columns. Only # Employees + Email Status are promoted to
# canonical columns (below); the rest live in raw_rows.
MASTER_30K_HEADERS = [
    "ID", "Full Name", "First Name", "Last Name", "Title", "Headline",
    "Company Name", "Email", "Email Status", "Primary Email Source", "Seniority",
    "Company Phone", "Company Founded Year", "Languages", "Stage", "# Employees",
    "Industry", "Keywords", "Person Linkedin Url", "Website", "Company Linkedin Url",
    "Facebook Url", "Twitter Url", "City", "State", "Country", "Company City",
    "Company State", "Company Country", "Annual Revenue",
    "Company Headcount Six Month Growth", "Company Headcount Twelve Month Growth",
    "Company Headcount Twenty Four Month Growth",
]

MAPPING_SPEC = {
    "source_label": SOURCE_LABEL,
    "fields": [
        {"canonical": "first_name", "source": "First Name", "op": "text"},
        {"canonical": "last_name", "source": "Last Name", "op": "text"},
        {"canonical": "job_title", "source": "Title", "op": "text"},
        {"canonical": "seniority", "source": "Seniority", "op": "text"},
        {"canonical": "company_name", "source": "Company Name", "op": "text"},
        {"canonical": "email", "source": "Email", "op": "email_or_null"},
        {"canonical": "phone", "source": "Company Phone", "op": "text"},
        {"canonical": "industry", "source": "Industry", "op": "text"},
        {"canonical": "social_linkedin", "source": "Person Linkedin Url", "op": "url_or_null"},
        {"canonical": "company_linkedin", "source": "Company Linkedin Url", "op": "url_or_null"},
        {"canonical": "website", "source": "Website", "op": "website_or_null"},
        {"canonical": "country", "source": "Country", "op": "text"},
        # Present only in the real-estate variant; None elsewhere (harmless).
        {"canonical": "social_facebook", "source": "Facebook Url", "op": "url_or_null"},
        {"canonical": "social_twitter", "source": "Twitter Url", "op": "url_or_null"},
        # Present only in the rich 30k master export; None in leaner shapes.
        {"canonical": "company_headcount", "source": "# Employees", "op": "to_int"},
        {"canonical": "email_status", "source": "Email Status", "op": "text"},
    ],
}
