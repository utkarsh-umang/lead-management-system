"""Global pause switch for the background workers — the "I'm closing the
laptop" button. Pauses BOTH the email finder and the ICP classifier at once so
no crawl fires against a sleeping machine and quietly fails.

The finder's long-poll and the classifier's /requested + /status endpoints all
consult the same flag (see app.services.worker_pause), so this one pair of
endpoints controls everything. Distinct from the finder's own hard-block pause
(enrichment /pause /resume), which the worker trips on credit exhaustion.
"""
from fastapi import APIRouter

from app.schemas.system import WorkerPauseIn, WorkerPauseState
from app.services import enrichment_signals as signals
from app.services import worker_pause

router = APIRouter()


@router.get(
    "/workers/pause-state",
    response_model=WorkerPauseState,
    operation_id="get_worker_pause_state",
)
async def get_worker_pause_state() -> WorkerPauseState:
    return WorkerPauseState(**worker_pause.pause_state())


@router.post(
    "/workers/pause",
    response_model=WorkerPauseState,
    operation_id="pause_workers",
)
async def pause_workers(body: WorkerPauseIn | None = None) -> WorkerPauseState:
    """Idle both workers. The finder's held long-poll re-checks and re-blocks;
    the classifier stops claiming lists and halts its current one mid-batch."""
    state = worker_pause.set_paused(body.reason if body else None)
    # Wake any finder request parked on /queue/wait so it re-evaluates the gate.
    signals.notify_control()
    return WorkerPauseState(**state)


@router.post(
    "/workers/resume",
    response_model=WorkerPauseState,
    operation_id="resume_workers",
)
async def resume_workers() -> WorkerPauseState:
    """Clear the gate — both workers pick work back up (finder instantly, the
    classifier within its ~15s poll)."""
    worker_pause.clear_paused()
    signals.notify_control()
    return WorkerPauseState(**worker_pause.pause_state())
