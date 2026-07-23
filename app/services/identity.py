"""Normalized name+company identity key — the lowest dedup tier.

A podcast guest almost never arrives with an email or LinkedIn (the strong,
universal identity anchors), so those tiers can't merge them. But the same
person recurs across episodes and across sheets, and sometimes across sources
(a guest who is also an Apollo contact). name+company is the strongest key we
can build for that case: exact, deterministic, never fuzzy.

Deliberately returns None unless BOTH a name and a company are present — a bare
name ("David French", "Kevin Smith") collides across unrelated people, so we
would rather leave those as separate leads than fuse strangers. They can still
merge later via email/LinkedIn once enrichment earns one.

The same normalization is used when the key is written (ingestion) and when it
is matched (dedup) and when existing leads are backfilled — one code path, so
the stored key and the lookup key can never drift.
"""

from __future__ import annotations

import re


def _norm(value: str | None) -> str:
    """lowercase, strip punctuation to spaces, collapse whitespace."""
    v = (value or "").strip().lower()
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def compute_identity_key(
    first_name: str | None,
    last_name: str | None,
    company_name: str | None,
) -> str | None:
    """Return "<norm name>|<norm company>", or None if either part is empty."""
    name = _norm(f"{first_name or ''} {last_name or ''}")
    company = _norm(company_name or "")
    if not name or not company:
        return None
    return f"{name}|{company}"
