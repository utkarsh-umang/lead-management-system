"""Export request/response schemas."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class ExportSelection(BaseModel):
    """Mirrors how selection works in the frontend: either an explicit list
    of lead ids, or "everything matching the current filter" (the
    select-all-matching flag) expressed as the filter params themselves."""

    lead_ids: list[uuid.UUID] | None = None
    # Filter-based selection — only consulted when lead_ids is None.
    # These mirror GET /leads exactly; anything the table can filter on,
    # select-all-matching must be able to express, or "export what I see"
    # quietly exports more than the user is looking at.
    search: str | None = None
    source: str | None = None
    has_email: bool | None = None
    email_from_finder: bool | None = None


class ExportPreviewOut(BaseModel):
    """What the export modal shows before the user commits."""

    total_selected: int
    exportable: int  # has an email — what actually lands in the CSV
    excluded_no_email: int  # Instantly can't use a lead without an email
    already_exported: int  # of the exportable, how many were contacted before
    already_exported_last_month: date | None  # most recent scheduled_month among those


class ExportCreateIn(ExportSelection):
    year: int = Field(ge=2020, le=2100)
    month: int = Field(ge=1, le=12)
    include_already_exported: bool = False


class ExportOut(BaseModel):
    id: uuid.UUID
    destination: str
    scheduled_month: date
    lead_count: int
    created_at: datetime


class ExportLeadItem(BaseModel):
    lead_id: uuid.UUID
    # Channel name for YouTube-native leads; person (or company) name for
    # person-centric ones — computed server-side, see exports controller.
    display_name: str | None
    email: str | None


class ExportLeadsPage(BaseModel):
    items: list[ExportLeadItem]
    total: int
    page: int
    page_size: int
