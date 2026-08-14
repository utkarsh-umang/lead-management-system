"""Schemas for on-demand `email_to_send` generation."""

import uuid

from pydantic import BaseModel, Field


class MethodOut(BaseModel):
    """A message-generation method, as the UI's method picker sees it."""

    name: str
    label: str
    description: str
    kind: str  # deterministic | llm | scrape
    required_fields: list[str]
    is_async: bool = False  # runs external I/O (llm/scrape) — slower, bounded by `limit`
    configured: bool = True  # False when a required key (Podscan/OpenAI) is unset


class GenerateMessagesIn(BaseModel):
    source: str
    batch_id: uuid.UUID
    method: str
    # Cap the number of leads processed — the safety valve for slow, rate-limited
    # llm methods so a run stays bounded (deterministic methods ignore small caps
    # in practice since they're instant). None = whole list.
    limit: int | None = Field(default=None, ge=1)


class MessageSample(BaseModel):
    lead_id: uuid.UUID
    display_name: str
    email_to_send: str


class MessagePreviewOut(BaseModel):
    method: str
    total_leads: int  # distinct leads in this list
    would_generate: int  # how many the method can produce a line for
    would_skip: int  # missing the required field(s)
    samples: list[MessageSample]  # a handful of real outputs, for eyeballing


class GenerateMessagesResult(BaseModel):
    method: str
    total_leads: int
    generated: int  # leads whose email_to_send was written
    skipped: int  # leads the method returned None for (left unchanged)


class FetchTranscriptsIn(BaseModel):
    """Bulk-fetch Podscan episode transcripts for a list into
    master_leads.episode_transcript (deduped by episode)."""

    source: str
    batch_id: uuid.UUID
    # Optionally restrict to the leads in a specific export (e.g. the top-25
    # list). Provenance (episode_id) still comes from the batch's raw rows; this
    # just narrows WHICH leads get a transcript. None = the whole list.
    export_id: uuid.UUID | None = Field(default=None)
    # Cap the number of UNIQUE EPISODES fetched — i.e. the number of Podscan API
    # calls. The rate-limit safety valve: a small cap (e.g. 50) is a bounded
    # trial run; None fetches every uncached episode in the list.
    max_episodes: int | None = Field(default=None, ge=1)


class FetchTranscriptsResult(BaseModel):
    total_leads: int
    leads_with_episode: int  # leads carrying an episode_id (fetch candidates)
    unique_episodes: int  # distinct episodes among the uncached candidates
    episodes_fetched: int  # episodes we got a transcript for
    leads_written: int  # leads whose episode_transcript was set
    stopped_paid_plan: bool  # key's plan can't serve transcripts — run halted early
