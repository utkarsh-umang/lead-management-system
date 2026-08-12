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

from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.models.master_lead import MasterLead


@dataclass(frozen=True)
class MessageContext:
    """What an async method sees. `provenance` is the lead's raw source row
    (raw_rows.raw_data) — the per-appearance fields the canonical MasterLead
    doesn't carry, e.g. episode_id / speaker_label for the Podscan guest list.
    Loaded by the controller only for methods that set `needs_provenance`."""

    lead: MasterLead
    provenance: dict


@dataclass(frozen=True)
class MessageMethod:
    name: str
    label: str
    description: str
    kind: str  # "deterministic" | "llm" | "scrape"
    required_fields: list[str]  # canonical MasterLead fields the method reads
    # A method is EITHER deterministic (sync `generate`, run inline) OR llm/scrape
    # (async `agenerate`, run with bounded concurrency + external I/O). Exactly
    # one is set.
    generate: Callable[[MasterLead], str | None] | None = None
    agenerate: Callable[["MessageContext"], Awaitable[str | None]] | None = None
    # llm/scrape methods that read the raw source row set this so the controller
    # loads raw_data alongside each lead.
    needs_provenance: bool = False
    provenance_fields: list[str] = field(default_factory=list)

    @property
    def is_async(self) -> bool:
        return self.agenerate is not None


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


from app.services.messages.transcript_opener import generate as _transcript_opener


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
    "transcript_opener": MessageMethod(
        name="transcript_opener",
        label="Episode transcript opener",
        description=(
            "Personalized opener from the actual episode the guest was on: pulls "
            "the Podscan transcript by episode_id, isolates the guest's own spoken "
            "lines (by speaker label), and writes a specific line about something "
            "they really said. Best for the Podscan Guest list. Needs Podscan + "
            "OpenAI keys; leads with no episode/transcript are skipped. Slower and "
            "rate-limited — run on a bounded list."
        ),
        kind="llm",
        required_fields=["first_name"],
        agenerate=_transcript_opener,
        needs_provenance=True,
        provenance_fields=["episode_id", "speaker_label", "podcast_name", "episode_title"],
    ),
}


def get_method(name: str) -> MessageMethod | None:
    return MESSAGE_METHODS.get(name)
