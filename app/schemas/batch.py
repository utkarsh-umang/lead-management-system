"""Batch upload request/response schemas."""

import uuid

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
