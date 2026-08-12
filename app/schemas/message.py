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
