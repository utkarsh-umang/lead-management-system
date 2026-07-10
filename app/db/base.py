"""SQLModel base class and common mixins."""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class Base(SQLModel):
    """Base model with common columns: id, created_at, updated_at."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
