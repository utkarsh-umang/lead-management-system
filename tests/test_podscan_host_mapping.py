"""Podscan Host spec through the real interpreter — one row = one podcast that
arrives with candidate emails. Exercises the brand-match qualifier
(row_qualifier): which listed email, if any, belongs to the show's brand, and
that hosting/junk addresses never win. Rows profiled from the real export."""

from app.services.mapping.interpreter import apply_mapping
from app.services.mapping.specs.podscan_host import MAPPING_SPEC


def _row(**over):
    base = {
        "Type": "Podcast",
        "Podcast Name": "",
        "Podcast ID": "pd_test",
        "Podcast Website": "",
        "Podcast Email": "",
        "Podcast Facebook": "",
        "Podcast Twitter": "",
        "Podcast Instagram": "",
        "Podcast YouTube": "",
        "Podcast LinkedIn": "",
    }
    base.update(over)
    return base


def test_brand_matched_email_wins_over_unrelated_first_address():
    # First listed address is unrelated; the brand-matching one must be chosen.
    row = _row(
        **{
            "Podcast Name": "Anderson Business Advisors Podcast",
            "Podcast Website": "https://andersonadvisors.com",
            "Podcast Email": "cstack@savingforcollege.com, taxtuesday@andersonadvisors.com",
        }
    )
    out = apply_mapping(MAPPING_SPEC, row)
    assert out["email"] == "taxtuesday@andersonadvisors.com"
    assert out["email_source"] == "provided"
    assert out["company_name"] == "Anderson Business Advisors Podcast"
    assert out["podcast_id"] == "pd_test"
    assert out["lead_tag"] == "podcast_host"


def test_hosting_platform_email_is_never_qualified():
    # soundcloud is a hosting platform; the real brand email must win instead.
    row = _row(
        **{
            "Podcast Name": "Practical Wisdom from ACP",
            "Podcast Website": "https://acplanners.org",
            "Podcast Email": "feeds@soundcloud.com, anne@acplanners.org",
        }
    )
    out = apply_mapping(MAPPING_SPEC, row)
    assert out["email"] == "anne@acplanners.org"


def test_only_hosting_email_falls_through_to_enrichment():
    # A single hosting-platform address is not send-ready -> no email set, so
    # the lead drops to the finder queue (the Needs_Enrichment bucket).
    row = _row(
        **{
            "Podcast Name": "The FarrCast Wealth Strategies",
            "Podcast Website": "https://podcasters.spotify.com/pod/farrcast",
            "Podcast Email": "podcasts45+ccd5d78@anchor.fm",
        }
    )
    out = apply_mapping(MAPPING_SPEC, row)
    assert out["email"] is None


def test_no_brand_match_falls_through_to_enrichment():
    # Real address, but no overlap with the show's name/site -> not qualified.
    row = _row(
        **{
            "Podcast Name": "What Should I Do With My Money?",
            "Podcast Website": "https://art19.com/shows/what-should-i-do",
            "Podcast Email": "ourideas@morganstanley.com",
        }
    )
    out = apply_mapping(MAPPING_SPEC, row)
    assert out["email"] is None


def test_no_email_at_all_is_empty():
    row = _row(**{"Podcast Name": "Some Finance Show", "Podcast Website": "https://somefinanceshow.com"})
    out = apply_mapping(MAPPING_SPEC, row)
    assert out["email"] is None
    # Non-email fields still map (so the lead is enrichable / exportable later).
    assert out["website"] == "https://somefinanceshow.com"
    assert out["lead_tag"] == "podcast_host"
