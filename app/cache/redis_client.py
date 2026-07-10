"""Redis cache client with JSON serialization and graceful fallback."""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any
import redis

from app.core.config import config

logger = logging.getLogger(__name__)


class _JSONEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, cls=_JSONEncoder)


def _json_loads(s: str) -> Any:
    def _object_hook(d: dict) -> dict:
        for k, v in d.items():
            if isinstance(v, str) and len(v) >= 19 and v[10] == "T":
                try:
                    d[k] = datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    pass
        return d

    return json.loads(s, object_hook=_object_hook)


def generate_cache_key(prefix: str, **params: Any) -> str:
    """Create a deterministic hash-based cache key. Same inputs -> same key."""
    parts = [f"{k}={v}" for k, v in sorted(params.items())]
    payload = f"{prefix}:{':'.join(parts)}"
    h = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{prefix}:{h}"


class RedisCache:
    """Redis cache with JSON serialization and graceful fallback when Redis is down."""

    def __init__(self) -> None:
        self._client: Any = None
        self._available = False
        try:
            self._client = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASSWORD or None,
                decode_responses=True,
            )
            self._client.ping()
            self._available = True
        except Exception as e:
            logger.warning("Redis unavailable: %s. Cache get returns None, set is no-op.", e)

    def get(self, key: str) -> dict | None:
        """Get value by key. Returns None on cache miss or Redis unavailable."""
        if not self._available or not self._client:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return _json_loads(raw)
        except Exception as e:
            logger.warning("Redis get failed for %s: %s", key, e)
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """Set value with optional TTL (seconds). No-op if Redis unavailable."""
        if not self._available or not self._client:
            return
        try:
            self._client.set(key, _json_dumps(value), ex=ttl)
        except Exception as e:
            logger.warning("Redis set failed for %s: %s", key, e)

    def delete(self, key: str) -> None:
        """Delete key. No-op if Redis unavailable."""
        if not self._available or not self._client:
            return
        try:
            self._client.delete(key)
        except Exception as e:
            logger.warning("Redis delete failed for %s: %s", key, e)


cache = RedisCache()
