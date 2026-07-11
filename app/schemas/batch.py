"""Batch upload request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BatchSummary(BaseModel):
    id: uuid.UUID
    source: str
    filename: str
    status: str
    row_count_raw: int
    row_count_valid: int
    row_count_quarantined: int
    row_count_new_leads: int
    row_count_merged: int


class QuarantinedRowOut(BaseModel):
    row_index: int
    quarantine_reason: str | None
    raw_data: dict


class BatchDetail(BaseModel):
    """Drill-down for one upload: full metadata plus every row that got
    quarantined and why — data that was stored but invisible until now."""

    id: uuid.UUID
    source: str
    filename: str
    status: str
    created_at: datetime
    row_count_raw: int
    row_count_valid: int
    row_count_quarantined: int
    row_count_new_leads: int
    row_count_merged: int
    row_count_with_email: int
    quarantined_rows: list[QuarantinedRowOut]
