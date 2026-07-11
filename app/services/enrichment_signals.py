"""In-process wake signals for the enrichment long-poll.

These events carry no information — they only wake held /queue/wait
requests early. The queue itself (derived from enrichment_attempts) is
always the source of truth: every woken request re-queries it, so a
missed signal costs at most one poll-timeout of latency, never work.

Single-process assumption: uvicorn runs one worker process in this stack,
so plain asyncio.Events suffice. If that ever changes, swap these for
Postgres LISTEN/NOTIFY — the call sites stay identical.
"""

import asyncio

work_available = asyncio.Event()
control_changed = asyncio.Event()


def notify_work() -> None:
    """Call after new leads are committed (end of ingestion)."""
    work_available.set()


def notify_control() -> None:
    """Call when pause/resume state changes."""
    control_changed.set()


async def wait_for(event: asyncio.Event, timeout: float) -> bool:
    """Wait for an event with a timeout; consume it if it fired."""
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        event.clear()
        return True
    except asyncio.TimeoutError:
        return False
