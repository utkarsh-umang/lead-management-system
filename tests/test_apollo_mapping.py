"""Apollo spec through the real interpreter — the first person-centric
source. Checks the mapped fields land in the person/company canonical
columns and that the ops null out what they should, on row shapes profiled
from the real export."""

from app.services.dedup import normalize_linkedin_url
from app.services.mapping.interpreter import apply_mapping
from app.services.mapping.specs.apollo import MAPPING_SPEC

FULL_ROW = {
    "First Name": "Eric",
    "Last Name": "Fluet",
    "Title": "Owner and President",
    "Headline": "Freelance Marketing Executive",
    "Company Name": "Get It Done Marketing",
    "Email": "efluet@getitdonemarketing.com",
    "Seniority": "Owner",
    "Company Phone": "+1 201-962-6414",
    "Company Founded Year": "2017.0",
    "Industry": "marketing & advertising",
    "Keywords": "branding, paid media",
    "Person Linkedin Url": "http://www.linkedin.com/in/ericfluet",
    "Website": "http://www.getitdonemarketing.com",
    "Company Linkedin Url": "http://www.linkedin.com/company/getitdonemkt",
    "City": "New York",
    "State": "New York",
    "Country": "United States",
    "Company City": "Ridgewood",
    "Company State": "New Jersey",
}


def test_full_row_maps_to_person_company_columns():
    canonical = apply_mapping(MAPPING_SPEC, FULL_ROW)
    assert canonical["first_name"] == "Eric"
    assert canonical["last_name"] == "Fluet"
    assert canonical["job_title"] == "Owner and President"
    assert canonical["seniority"] == "Owner"
    assert canonical["company_name"] == "Get It Done Marketing"
    assert canonical["email"] == "efluet@getitdonemarketing.com"
    assert canonical["phone"] == "+1 201-962-6414"
    assert canonical["industry"] == "marketing & advertising"
    assert canonical["social_linkedin"] == "http://www.linkedin.com/in/ericfluet"
    assert canonical["company_linkedin"] == "http://www.linkedin.com/company/getitdonemkt"
    assert canonical["website"] == "http://www.getitdonemarketing.com"
    assert canonical["country"] == "United States"


def test_raw_only_columns_never_reach_canonical():
    canonical = apply_mapping(MAPPING_SPEC, FULL_ROW)
    for value in canonical.values():
        assert value not in ("Freelance Marketing Executive", "branding, paid media", "2017.0")
    # And nothing youtube-native gets touched by a person-centric source.
    assert not any(key.startswith("youtube_") for key in canonical)


def test_blank_and_junk_values_null_out():
    row = dict(
        FULL_ROW,
        **{
            "Last Name": "  ",
            "Email": "john.doe@company.com",  # placeholder → junk-rejected
            "Website": "n/a",
        },
    )
    canonical = apply_mapping(MAPPING_SPEC, row)
    assert canonical["last_name"] is None
    assert canonical["email"] is None
    assert canonical["website"] is None


def test_linkedin_normalization_matches_url_variants():
    variants = [
        "http://www.linkedin.com/in/ericfluet",
        "https://linkedin.com/in/ericfluet/",
        "www.linkedin.com/in/EricFluet",
    ]
    assert len({normalize_linkedin_url(v) for v in variants}) == 1
