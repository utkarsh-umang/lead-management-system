"""Schemas for the ICP / industry classification write-back."""

import uuid

from pydantic import BaseModel


class PendingLead(BaseModel):
    """A lead awaiting classification (handed to the ai-agents runner)."""

    lead_id: uuid.UUID
    company_name: str | None
    website: str | None


class ClassificationResult(BaseModel):
    lead_id: uuid.UUID
    classified_industry: str  # taxonomy bucket or an LLM-proposed label
    icp_confidence: int  # 0-100 paid-ads-agency score
    icp_reasoning: str | None = None
    icp_source: str | None = None  # crawl | serper


class ClassificationResultsIn(BaseModel):
    results: list[ClassificationResult]


class ClassificationResultsOut(BaseModel):
    updated: int


class ClassificationStatus(BaseModel):
    batch_id: uuid.UUID
    classify_requested: bool
    total_leads: int
    with_website: int
    classified: int
    pending: int  # has website, not yet classified
    icp_accepted: int  # icp_confidence >= 60
    by_industry: dict[str, int]  # classified_industry -> count
    paused: bool = False  # global worker pause (halts the classifier mid-list)


class RequestClassificationIn(BaseModel):
    batch_id: uuid.UUID


class RequestClassificationOut(BaseModel):
    batch_id: uuid.UUID
    classify_requested: bool
    pending: int


class RequestedBatch(BaseModel):
    """A list the worker should classify (requested + has pending leads)."""

    batch_id: uuid.UUID
    source: str
    filename: str
    pending: int
