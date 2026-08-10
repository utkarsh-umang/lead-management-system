"""Global pause gate for the background workers (email finder + ICP
classifier).

One Redis flag both workers' queue endpoints consult, so the user can idle
everything with a single switch before closing the laptop lid. The problem it
solves: while the machine sleeps a crawl that was handed out just fails (and
burns a retry / API credits), so the fix is to stop handing out work rather
than fight sleep.

Redis, not a DB table: this is a transient control signal, not domain data, so
it needs no migration (and stays independent of any in-flight schema work). A
deliberately long TTL — not the cache's 1h default, which would silently
auto-resume overnight — means a normal overnight pause never expires, while a
pause the user forgets self-heals after a week instead of stranding the workers
forever.
"""
from datetime import datetime, timezone

from app.cache.redis_client import cache

_KEY = "system:workers_paused"
_TTL_S = 7 * 24 * 3600  # 7 days: survives any overnight, auto-heals if forgotten


def pause_state() -> dict:
    """{paused, since, reason}. since/reason are null while running."""
    v = cache.get(_KEY)
    if not v:
        return {"paused": False, "since": None, "reason": None}
    since = v.get("since")
    # The cache's JSON loader revives ISO strings as datetimes; hand back a
    # plain string so it matches the response schema.
    if isinstance(since, datetime):
        since = since.isoformat()
    return {"paused": True, "since": since, "reason": v.get("reason")}


def is_paused() -> bool:
    return bool(cache.get(_KEY))


def set_paused(reason: str | None) -> dict:
    since = datetime.now(timezone.utc).isoformat()
    cache.set(_KEY, {"since": since, "reason": reason}, ttl=_TTL_S)
    return {"paused": True, "since": since, "reason": reason}


def clear_paused() -> None:
    cache.delete(_KEY)
