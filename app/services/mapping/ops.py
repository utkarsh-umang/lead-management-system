"""The fixed op vocabulary. Every mapping spec can only reference these —
this is what keeps mapping specs data, not code: nothing here executes
anything the spec provides, it only selects among a small set of
pre-written, unit-testable transforms.

Every op takes the raw string value (already `.get()` from the row, may be
None) plus optional args from the spec, and returns a canonical Python value
or None. None is the only representation of "missing" — never a sentinel
string (see Master Schema.md for why).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

from app.services.mapping.email_junk import is_junk_email

# Known not-found sentinels tools use instead of leaving a cell blank.
_NULL_SENTINELS = {"", "x", "n/a", "na", "none", "null", "-"}

# Domains that are never a lead's actual website, even though they're
# syntactically valid URLs — CDN/streaming infrastructure a scraper picked
# up by mistake. Match by suffix.
_REJECT_DOMAIN_SUFFIXES = (
    "googlevideo.com",
    "ytimg.com",
    "googleusercontent.com",
    "ggpht.com",
)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def text(value: str | None, **_args) -> str | None:
    """Trim whitespace; empty or known not-found sentinel -> None."""
    v = _clean(value)
    if v is None:
        return None
    return None if v.lower() in _NULL_SENTINELS else v


def to_int(value: str | None, **_args) -> int | None:
    v = _clean(value)
    if v is None:
        return None
    try:
        return int(float(v))  # handles "123.0"-style exports too
    except ValueError:
        return None


def to_float(value: str | None, **_args) -> float | None:
    v = _clean(value)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def date_parse(value: str | None, fmt: str = "%Y-%m-%d", **_args) -> date | None:
    v = _clean(value)
    if v is None:
        return None
    try:
        return datetime.strptime(v, fmt).date()
    except ValueError:
        return None


def datetime_parse(value: str | None, fmt: str = "%Y-%m-%d %H:%M UTC", **_args) -> datetime | None:
    v = _clean(value)
    if v is None:
        return None
    try:
        return datetime.strptime(v, fmt)
    except ValueError:
        return None


def email_or_null(value: str | None, **_args) -> str | None:
    """Normalize known not-found sentinels to None; anything left that
    isn't email-shaped (e.g. a name that ended up in the email column) is
    also None rather than kept as a wrong value. Email-shaped junk
    (placeholders, vendor addresses, system mailboxes — see email_junk.py)
    is rejected the same way: NULL in canonical, original preserved in
    raw_rows."""
    v = text(value)
    if v is None:
        return None
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
        return None
    v = v.lower()
    return None if is_junk_email(v) else v


def url_or_null(value: str | None, **_args) -> str | None:
    v = _clean(value)
    if v is None:
        return None
    parsed = urlparse(v if "://" in v else f"https://{v}")
    return v if parsed.netloc else None


def website_or_null(value: str | None, **_args) -> str | None:
    """Like url_or_null, but rejects known CDN/streaming domains that are
    never actually a lead's website (see Master Schema.md)."""
    v = url_or_null(value)
    if v is None:
        return None
    netloc = urlparse(v if "://" in v else f"https://{v}").netloc.lower()
    if any(netloc == d or netloc.endswith("." + d) for d in _REJECT_DOMAIN_SUFFIXES):
        return None
    return v


def youtube_url_from_handle(value: str | None, **_args) -> str | None:
    """@handle -> https://youtube.com/@handle ; UC... channel id ->
    https://youtube.com/channel/UC..."""
    v = _clean(value)
    if v is None:
        return None
    if v.startswith("@"):
        return f"https://youtube.com/{v}"
    if v.startswith("UC"):
        return f"https://youtube.com/channel/{v}"
    return f"https://youtube.com/{v}"


OPS = {
    "text": text,
    "to_int": to_int,
    "to_float": to_float,
    "date_parse": date_parse,
    "datetime_parse": datetime_parse,
    "email_or_null": email_or_null,
    "url_or_null": url_or_null,
    "website_or_null": website_or_null,
    "youtube_url_from_handle": youtube_url_from_handle,
}
