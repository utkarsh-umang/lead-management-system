"""Health check controller."""

from fastapi import APIRouter

from app.cache.redis_client import cache
from app.core.config import config
from app.db.session import engine
from app.schemas.common import HealthResponse

router = APIRouter()


async def _check_postgres() -> str:
    """Ping Postgres (async)."""
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSession(engine) as session:
            await session.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unreachable"


def _check_redis() -> str:
    """Ping Redis."""
    try:
        if cache._available and cache._client:
            cache._client.ping()
            return "connected"
    except Exception:
        pass
    return "unreachable"


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check with per-store connectivity status.
    Returns 200 with status for Postgres and Redis.
    """
    postgres_status = await _check_postgres()
    redis_status = _check_redis()

    return HealthResponse(
        status="ok",
        environment=config.ENVIRONMENT,
        postgres=postgres_status,
        redis=redis_status,
    )
