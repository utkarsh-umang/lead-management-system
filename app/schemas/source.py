"""Per-source aggregate stats and upload history."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BatchSummaryOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    created_at: datetime
    row_count_raw: int
    row_count_valid: int
    row_count_quarantined: int
    row_count_new_leads: int
    row_count_merged: int
    row_count_with_email: int


class SourceDetail(BaseModel):
    source: str
    lead_count: int
    total_rows_uploaded: int
    total_quarantined: int
    total_deduped: int
    total_with_email_at_upload: int
    currently_with_email: int
    currently_without_email: int  # eligible for the email finder
    batches: list[BatchSummaryOut]
