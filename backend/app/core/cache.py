import json
import logging
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis():
    try:
        from redis import Redis

        return Redis.from_url(get_settings().redis_url, decode_responses=True, socket_timeout=0.2)
    except Exception:
        return None


def cache_get(key: str):
    client = get_redis()
    if not client:
        return None
    try:
        value = client.get(key)
        return json.loads(value) if value else None
    except Exception as exc:
        logger.debug("cache_get_failed", extra={"error": str(exc)})
        return None


def cache_set(key: str, value, ttl: int = 60) -> None:
    client = get_redis()
    if not client:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("cache_set_failed", extra={"error": str(exc)})


def cache_delete(*keys: str) -> None:
    client = get_redis()
    if not client:
        return
    try:
        for key in keys:
            matching = list(client.scan_iter(match=f"{key}*") if key.endswith(":") else [key])
            if matching:
                client.delete(*matching)
    except Exception as exc:
        logger.debug("cache_delete_failed", extra={"error": str(exc)})
