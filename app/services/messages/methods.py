"""Message-method registry — named ways to generate a lead's `email_to_send`.

Same governance as the mapping `OPS` and `QUALIFIERS` registries: methods are
code-defined and self-describing; the caller (and the UI) only *selects* one by
name, never supplies logic. Each method reads canonical `MasterLead` fields and
returns the opening line, or None when it can't produce one for that lead (the
column is left as-is / cleared, and the lead is reported as skipped).

The registry is intentionally self-describing (`label`, `description`, `kind`,
`required_fields`) so the frontend renders the method picker straight from
`GET /messages/methods` — adding a method here is all it takes to surface it.

First method: `podcast_name_opener`, a 1:1 port of the Google-Sheet formula the
user ran by hand for the Podscan Host list.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.models.master_lead import MasterLead


@dataclass(frozen=True)
class MessageMethod:
    name: str
    label: str
    description: str
    kind: str  # "deterministic" | "llm" | "scrape" — only deterministic exists today
    required_fields: list[str]  # canonical MasterLead fields the method reads
    generate: Callable[[MasterLead], str | None]


def _podcast_name_opener(lead: MasterLead) -> str | None:
    """Port of the sheet formula (A2 = podcast name = company_name):

        =IF(REGEXMATCH(LOWER(A2),"podcast"),
            "Checked out " & IF(LEFT(LOWER(A2),4)="the ", A2, "The " & A2) & ", really good stuff!",
            "Checked out your podcast \"" & A2 & "\", really good stuff!")
    """
    name = (lead.company_name or "").strip()
    if not name:
        return None
    low = name.lower()
    if "podcast" in low:
        body = name if low.startswith("the ") else f"The {name}"
        return f"Checked out {body}, really good stuff!"
    return f'Checked out your podcast "{name}", really good stuff!'


MESSAGE_METHODS: dict[str, MessageMethod] = {
    "podcast_name_opener": MessageMethod(
        name="podcast_name_opener",
        label="Podcast name opener",
        description=(
            'Simple opener from the podcast name. "…Podcast" → "Checked out '
            'The X Podcast, really good stuff!"; otherwise → "Checked out your '
            'podcast \"X\", really good stuff!". Best for the Podscan Host list.'
        ),
        kind="deterministic",
        required_fields=["company_name"],
        generate=_podcast_name_opener,
    ),
}


def get_method(name: str) -> MessageMethod | None:
    return MESSAGE_METHODS.get(name)
