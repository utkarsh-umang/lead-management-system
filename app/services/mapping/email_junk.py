"""Junk-email rejection for ingestion — the store's last line of defense.

A junk value in a source CSV's email column (form placeholder, vendor
address scraped out of a JS bundle, a legal mailbox) is worse than no
email: it makes the lead look "done" to the enrichment queue and pollutes
exports. Anything rejected here lands as NULL in canonical — the original
value always survives in raw_rows.raw_data, so rejection is recoverable.

Pattern lists ported from the battle-tested `email-finder-youtube-lite`
notebook (lead-enricher-ai-be), which hardened them over real 19k-lead
runs. ADD NEW PATTERNS HERE — each constant says what it matches.

Deliberately NOT rejected:
- Role emails (info@, contact@, hello@…) — a real outreach contact for a
  business lead, just less personal. The notebook only scored them lower.
- Free-mail providers (gmail etc.) — how most creators are reachable.
"""

# Substring match against the WHOLE email — placeholder DOMAINS and
# template markers. Only patterns that can't collide with a real address
# belong here; local-part words go in PLACEHOLDER_LOCALPARTS below
# (exact match), otherwise "test@" would also kill greatest@gmail.com.
PLACEHOLDER_SUBSTRINGS = (
    "example.com", "example.org", "example.net",
    "yourdomain", "yourcompany", "yoursite",
    "domain.com", "placeholder",
)

# Exact local-part match — demo/template text used in form placeholders.
PLACEHOLDER_LOCALPARTS = frozenset(
    {
        "email", "user", "username", "test", "name", "sample", "someone",
        "somebody", "your", "you", "youremail", "yourname", "firstname",
        "lastname", "firstname.lastname", "johnappleseed", "john.doe",
        "jane.doe", "example",
    }
)

# Exact local-part match — legal/system mailboxes that are never a useful
# outreach contact.
DROP_LOCALPARTS = frozenset(
    {
        "privacy", "privacypolicy", "legal", "dmca", "abuse", "webmaster",
        "postmaster", "hostmaster", "copyright", "compliance", "gdpr",
        "unsubscribe", "newsletter", "notifications", "noreply", "no-reply",
        "donotreply", "mailerdaemon", "root", "spam", "security", "dpo",
        "dataprotection",
    }
)

# Domain suffix match (catches subdomains too) — platform/vendor/third-party
# addresses that leak out of widgets, scripts, and linked pages; never the
# lead's own inbox.
VENDOR_DOMAINS = frozenset(
    {
        # web infra / site builders / CDNs
        "amazonaws.com", "gstatic.com", "googleapis.com", "googlevideo.com",
        "wordpress.org", "wixpress.com", "wix.com", "sentry.io",
        "cloudflare.com", "godaddy.com", "squarespace.com", "shopify.com",
        "fbcdn.net", "w3.org", "schema.org", "mozilla.org", "jquery.com",
        # music labels / distributors (the Chloe Ting / ncs.io lesson)
        "ncs.io", "distrokid.com", "spinnup.com", "unitedmasters.com",
        "tunecore.com", "cdbaby.com", "monstercat.com", "soundcloud.com",
        "bandcamp.com", "audius.co", "awal.com", "symphonic.com",
        "incompetech.com",
        # game studios / platforms
        "nintendo.com", "playstation.com", "xbox.com", "riotgames.com",
        "ea.com", "ubisoft.com", "rockstargames.com", "epicgames.com",
        "roblox.com",
        # merch / payment / creator platforms
        "patreon.com", "cash.app", "venmo.com", "ko-fi.com",
        "buymeacoffee.com", "cameo.com", "represent.com", "fanjoy.co",
        "teespring.com", "spring.com", "bonfire.com", "merchbar.com",
        "streamelements.com", "streamlabs.com", "payhip.com",
        "redbubble.com", "teepublic.com", "spreadshirt.com",
        "threadless.com", "kit.co", "awin.com", "deviantart.com",
        "gamersupps.gg", "linktr.ee", "beacons.ai", "gumroad.com",
        # talent agencies (represent the creator, not the creator's inbox)
        "caa.com", "unitedtalent.com", "wmeagency.com", "gersh.com",
        "abramsartists.com", "icmpartners.com",
        # sponsors whose contact email leaks onto creator sites
        "surfshark.com", "nordvpn.com", "expressvpn.com", "betterhelp.com",
    }
)

# "TLD" is actually a file extension: the email regex matched asset paths in
# JS bundles (e.g. logo@2x.png parses as local="logo", domain="2x.png").
ASSET_EXTENSIONS = frozenset(
    {"css", "js", "json", "png", "jpg", "jpeg", "svg", "webp", "gif", "bmp",
     "map", "scss", "ts", "woff", "woff2", "ttf", "ico", "mp4", "webm"}
)


def junk_email_reason(email: str) -> str | None:
    """Return why this email is junk, or None if it looks legitimate.
    Expects an already-lowercased, trimmed, email-shaped string."""
    local, _, domain = email.partition("@")

    if domain.rsplit(".", 1)[-1] in ASSET_EXTENSIONS:
        return "asset_extension"
    if any(marker in email for marker in PLACEHOLDER_SUBSTRINGS):
        return "placeholder"
    if local in PLACEHOLDER_LOCALPARTS:
        return "placeholder"
    if local in DROP_LOCALPARTS:
        return "system_mailbox"
    if domain in VENDOR_DOMAINS or any(domain.endswith("." + v) for v in VENDOR_DOMAINS):
        return "vendor_domain"
    return None


def is_junk_email(email: str) -> bool:
    return junk_email_reason(email) is not None
