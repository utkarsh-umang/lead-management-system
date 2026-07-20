"""Mapping spec for Apollo people exports. Headers: First Name, Last Name,
Title, Headline, Company Name, Email, Seniority, Company Phone, Company
Founded Year, Industry, Keywords, Person Linkedin Url, Website, Company
Linkedin Url, City, State, Country, Company City, Company State.

First person-centric source (the lead is a person at a company, not a
YouTube channel) — populates the person/company canonical columns and none
of the youtube_* ones. Dedup identity here is email, then normalized
Person Linkedin Url (100% filled in the first real export).

Deliberately raw-only (recoverable from raw_rows, not canonical): Headline
(free-text LinkedIn headline), Keywords (huge Apollo-derived tag blob),
Company Founded Year, and the four City/State columns — promoting
source-specific extras is exactly the schema bloat Master Schema.md warns
about. Industry maps to canonical `industry`, NOT niche/category, which
carry YouTube-native taxonomy.
"""

SOURCE_LABEL = "apollo"

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
    ],
}
