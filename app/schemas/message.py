"""Schemas for on-demand `email_to_send` generation."""

import uuid

from pydantic import BaseModel


class MethodOut(BaseModel):
    """A message-generation method, as the UI's method picker sees it."""

    name: str
    label: str
    description: str
    kind: str  # deterministic | llm | scrape
    required_fields: list[str]


class GenerateMessagesIn(BaseModel):
    source: str
    batch_id: uuid.UUID
    method: str


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
