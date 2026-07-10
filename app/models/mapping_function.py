"""A registered, approved mapping spec for one CSV column-shape."""

from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.db.base import Base


class MappingFunction(Base, table=True):
    """
    Keyed by fingerprint (column-name + dtype signature). A fingerprint hit
    means the shape is known and the executor can run fully automatically;
    a miss means the LLM must draft a new spec for human approval.
    """

    __tablename__ = "mapping_functions"

    fingerprint: str = Field(index=True, unique=True)
    source_label: str
    mapping_spec: dict = Field(sa_column=Column(JSONB, nullable=False))
    version: int = Field(default=1)
    approved_at: datetime | None = Field(default=None)
