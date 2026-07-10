"""Fingerprint a CSV by its column-name signature so a known shape can be
dispatched automatically, without re-deciding what it is every upload."""

from __future__ import annotations

import hashlib


def compute_fingerprint(headers: list[str]) -> str:
    signature = "|".join(sorted(h.strip() for h in headers))
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()
