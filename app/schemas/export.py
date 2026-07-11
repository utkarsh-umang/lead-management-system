"""Export request/response schemas."""

import uuid
from datetime import date

from pydantic import BaseModel, Field


class ExportSelection(BaseModel):
    """Mirrors how selection works in the frontend: either an explicit list
    of lead ids, or "everything matching the current filter" (the
    select-all-matching flag) expressed as the filter params themselves."""

    lead_ids: list[uuid.UUID] | None = None
    # Filter-based selection — only consulted when lead_ids is None.
    search: str | None = None
    source: str | None = None
    has_email: bool | None = None


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
