"""Live state of the enrichment worker — a single row, overwritten by
heartbeats, never a log (the attempt history in enrichment_attempts is the
log). `paused` is the human-in-the-loop gate: the worker sets it when it
hits a hard block (e.g. LLM credits exhausted) and only a human pressing
Resume clears it — no timed auto-retry against an error that can't
self-heal."""

from datetime import datetime

from sqlmodel import Field

from app.db.base import Base


class EnrichmentWorkerState(Base, table=True):
    __tablename__ = "enrichment_worker_state"

    # waiting | processing | blocked — as reported by the worker itself
    state: str = Field(default="waiting")
    detail: str | None = Field(default=None)
    in_flight: int = Field(default=0)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

    paused: bool = Field(default=False)
    pause_reason: str | None = Field(default=None)
