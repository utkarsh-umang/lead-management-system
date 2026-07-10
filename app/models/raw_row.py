"""The untouched original row data for every uploaded CSV row."""

import uuid

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.db.base import Base


class RawRow(Base, table=True):
    __tablename__ = "raw_rows"

    batch_id: uuid.UUID = Field(foreign_key="batches.id", index=True)
    row_index: int
    raw_data: dict = Field(sa_column=Column(JSONB, nullable=False))
    validation_status: str = Field(default="pending")  # pending/valid/quarantined
    quarantine_reason: str | None = Field(default=None)
