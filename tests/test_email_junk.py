"""Junk-email rejection at ingestion — the email_or_null op is the gate
every mapped email passes through."""

from app.services.mapping.email_junk import junk_email_reason
from app.services.mapping.ops import email_or_null


def test_placeholders_rejected():
    for junk in [
        "your@email.com",
        "name@example.com",
        "user@domain.com",
        "test@test.com",
        "firstname.lastname@acme.com",
        "someone@somewhere.io",
    ]:
        assert email_or_null(junk) is None, junk


def test_system_mailboxes_rejected():
    for junk in ["privacy@channel.com", "noreply@brand.io", "dmca@site.net", "gdpr@co.uk"]:
        assert email_or_null(junk) is None, junk


def test_vendor_and_thirdparty_domains_rejected():
    for junk in [
        "contact@ncs.io",  # the Chloe Ting lesson: linked label, not the creator
        "hi@patreon.com",
        "errors@sentry.io",
        "sub@mail.wixpress.com",  # subdomain of a vendor domain
        "partners@nordvpn.com",
    ]:
        assert email_or_null(junk) is None, junk


def test_asset_extensions_rejected():
    assert email_or_null("logo@2x.png") is None
    assert email_or_null("icon@3x.svg") is None


def test_legitimate_emails_kept():
    # Role emails and freemail are real outreach contacts — never junk.
    for real in [
        "tony@beastmodecamping.com",
        "info@acmecorp.io",
        "contact@somebrand.com",
        "creator123@gmail.com",
        "Hello@Brand.com",  # normalized to lowercase, kept
    ]:
        assert email_or_null(real) == real.lower(), real


def test_no_false_positives_on_placeholder_like_locals():
    # Placeholder words must match the local part EXACTLY, not as a
    # substring — otherwise these real-looking addresses would be killed.
    for real in [
        "greatest@gmail.com",  # contains "test@"
        "brandname@gmail.com",  # contains "name@"
        "poweruser@gmail.com",  # contains "user@"
        "bayou@acme.com",  # contains "you@"
    ]:
        assert email_or_null(real) == real, real


def test_sentinels_and_nonemail_still_null():
    for v in ["x", "X", "n/a", "", None, "Kevin Lu"]:
        assert email_or_null(v) is None


def test_reason_labels():
    assert junk_email_reason("your@email.com") == "placeholder"
    assert junk_email_reason("privacy@x.com") == "system_mailbox"
    assert junk_email_reason("a@ncs.io") == "vendor_domain"
    assert junk_email_reason("logo@2x.png") == "asset_extension"
    assert junk_email_reason("tony@beastmodecamping.com") is None
