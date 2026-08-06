"""Runs a mapping spec (data) over a raw row. This is the only thing that
ever touches raw CSV data — it never executes anything from the spec beyond
looking up a named op in the fixed OPS table, so a mapping spec can never
smuggle in arbitrary code."""

from __future__ import annotations

from typing import Any

from app.services.mapping.ops import OPS
from app.services.mapping.qualifiers import QUALIFIERS


def apply_mapping(spec: dict, raw_row: dict[str, Any]) -> dict[str, Any]:
    """spec['fields'] = [{"canonical": ..., "source": ..., "op": ..., "op_args": {...}}]
    Returns a dict of canonical_field -> value, only for fields the spec maps.

    An optional spec['row_qualifier'] names a cross-field transform (from the
    fixed QUALIFIERS registry) that runs after the per-field ops and merges its
    canonical overrides on top — for decisions no single column can make, e.g.
    the Podscan Host brand-match email pick. Named, never executed from the
    spec, so the spec stays data."""
    canonical: dict[str, Any] = {}
    for field in spec["fields"]:
        op_fn = OPS[field["op"]]
        raw_value = raw_row.get(field["source"])
        canonical[field["canonical"]] = op_fn(raw_value, **field.get("op_args", {}))

    qualifier = spec.get("row_qualifier")
    if qualifier:
        canonical.update(QUALIFIERS[qualifier](raw_row, canonical))
    return canonical
