"""Mapping registry response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class MappingFunctionOut(BaseModel):
    id: uuid.UUID
    fingerprint: str
    source_label: str
    mapping_spec: dict
    version: int
    approved_at: datetime | None
    created_at: datetime
