"""One row per CSV upload — source, counts, and which mapping was used."""

import uuid

from sqlmodel import Field

from app.db.base import Base


class Batch(Base, table=True):
    """Upload-level metadata. Row data itself lives in RawRow."""

    __tablename__ = "batches"

    source: str = Field(index=True)  # e.g. "youtube-tool", "youtube-consulti"
    source_sheet_url: str | None = Field(default=None)
    filename: str
    mapping_function_id: uuid.UUID | None = Field(
        default=None, foreign_key="mapping_functions.id"
    )
    status: str = Field(default="pending")  # pending/awaiting_mapping_approval/processing/completed/failed

    row_count_raw: int = Field(default=0)
    row_count_valid: int = Field(default=0)
    row_count_quarantined: int = Field(default=0)
    row_count_new_leads: int = Field(default=0)
    row_count_merged: int = Field(default=0)
