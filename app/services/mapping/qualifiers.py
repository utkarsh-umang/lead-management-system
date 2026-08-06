"""Row-level qualifiers: cross-field transforms a mapping spec can opt into
via a `row_qualifier` key, the same way `fields` opt into named `ops`.

A plain op sees one cell; a qualifier sees the whole raw row plus the already-
mapped canonical dict, and returns a small dict of canonical overrides that get
merged on top. This is for decisions no single column can make — the flagship
case being "which of this podcast's listed emails, if any, actually belongs to
its brand?".

Kept in a fixed QUALIFIERS registry (like OPS) so a spec still only ever *names*
a transform — the interpreter never executes anything the spec supplies, so a
mapping spec stays data, not code.

`podscan_host_qualify` is a faithful port of the user's Google Apps Script
`qualifyPodcastLeads`: brand candidates from the podcast name + website are
longest-common-substring matched (>= 4 chars) against each listed email's
local-part and domain brand; the best-matching non-junk email wins. A match =>
a "qualified" lead that already carries a send-ready email (email_source
'provided'); no match / no email => email stays NULL and the lead falls through
to the finder queue (the "Needs_Enrichment" bucket).
"""

from __future__ import annotations

import re

from app.services.mapping.email_junk import PODCAST_HOST_DOMAINS, is_junk_email

MIN_LCS_LENGTH = 4

# Accents -> ASCII, matching the Apps Script's transliterate() table.
_ACCENTS = str.maketrans(
    {
        "á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "å": "a", "ā": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e", "ē": "e", "ė": "e", "ę": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i", "ī": "i",
        "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o", "ø": "o", "ō": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u", "ū": "u",
        "ñ": "n", "ń": "n", "ç": "c", "ć": "c", "ß": "ss", "ÿ": "y", "ý": "y",
    }
)

_STOPWORDS = {
    "with", "and", "the", "of", "for", "on", "a", "an", "in", "to",
    "podcast", "show", "radio", "live",
}

_PATH_STOP = {"show", "pod", "podcast", "episode"}


def _normalize(text: str) -> str:
    """Lowercase, transliterate accents, strip to [a-z0-9]. Twin of the Apps
    Script normalize()."""
    return re.sub(r"[^a-z0-9]", "", text.lower().translate(_ACCENTS))


def _base_domain(url: str) -> str:
    host = re.sub(r"^https?://", "", url.lower()).split("/")[0]
    host = re.sub(r"^www\.", "", host)
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 else host


def _subdomain(url: str) -> str:
    host = re.sub(r"^https?://", "", url.lower()).split("/")[0]
    host = re.sub(r"^www\.", "", host)
    parts = host.split(".")
    return ".".join(parts[:-2]) if len(parts) > 2 else ""


def _path_identifier(url: str) -> str:
    parts = re.sub(r"^https?://", "", url.lower()).split("/")
    for segment in reversed(parts):
        seg = re.sub(r"[^a-z0-9-]", "", segment)
        if len(seg) > 3 and seg not in _PATH_STOP:
            return seg.replace("-", "")
    return ""


def _is_hosting_domain(domain: str) -> bool:
    return any(host in domain for host in PODCAST_HOST_DOMAINS)


def _website_brand(url: str) -> str:
    if not url:
        return ""
    domain = _base_domain(url)
    if _is_hosting_domain(domain):
        # A hosting URL's brand lives in its subdomain or path, not the
        # platform domain (thebrand.libsyn.com, libsyn.com/thebrand).
        sub = _subdomain(url)
        if sub:
            return _normalize(sub)
        path = _path_identifier(url)
        if path:
            return _normalize(path)
        return ""
    return _normalize(domain.split(".")[0])


def _meaningful_tokens(text: str) -> list[str]:
    out = []
    for raw in text.lower().split():
        tok = _normalize(raw)
        if len(tok) > 2 and raw not in _STOPWORDS and tok not in _STOPWORDS:
            out.append(tok)
    return out


def _brand_candidates(podcast_name: str, website: str) -> list[str]:
    candidates: list[str] = []
    full = _normalize(podcast_name)
    if len(full) >= 4:
        candidates.append(full)
    for tok in _meaningful_tokens(podcast_name):
        if len(tok) >= 4:
            candidates.append(tok)
    brand = _website_brand(website)
    if brand and len(brand) >= 4:
        candidates.append(brand)
    return candidates


def _longest_common_substring(a: str, b: str) -> int:
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def _parse_emails(cell: str | None) -> list[str]:
    if not cell:
        return []
    return [e.strip().lower() for e in cell.split(",") if "@" in e]


def podscan_host_qualify(raw_row: dict, canonical: dict) -> dict:
    """Pick the brand-matched, non-junk email for one podcast row.

    Always returns an explicit `email` key (the chosen send-ready address, or
    None so the lead falls through to the finder — the Needs_Enrichment bucket),
    plus `email_source='provided'` on a match."""
    no_match = {"email": None, "email_source": None}

    podcast_name = (raw_row.get("Podcast Name") or "").strip()
    website = (raw_row.get("Podcast Website") or "").strip()

    emails = _parse_emails(raw_row.get("Podcast Email"))
    if not emails:
        return no_match

    candidates = _brand_candidates(podcast_name, website)
    if not candidates:
        return no_match

    best_email: str | None = None
    best_lcs = 0
    for email in emails:
        if "@" not in email or is_junk_email(email):
            # is_junk_email covers hosting platforms, vendor/system mailboxes,
            # and asset/placeholder junk in one check.
            continue
        local, _, domain = email.partition("@")
        targets = (_normalize(local), _normalize(domain.split(".")[0]))
        for cand in candidates:
            for target in targets:
                lcs = _longest_common_substring(cand, target)
                if lcs >= MIN_LCS_LENGTH and lcs > best_lcs:
                    best_lcs = lcs
                    best_email = email

    if best_email is None:
        return no_match
    return {"email": best_email, "email_source": "provided"}


QUALIFIERS = {
    "podscan_host_qualify": podscan_host_qualify,
}
