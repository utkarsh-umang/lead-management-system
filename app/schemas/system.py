"""Schemas for the global worker pause switch."""

from pydantic import BaseModel


class WorkerPauseState(BaseModel):
    """Whether the background workers are globally paused."""

    paused: bool
    since: str | None = None  # ISO timestamp the pause began
    reason: str | None = None


class WorkerPauseIn(BaseModel):
    reason: str | None = None
