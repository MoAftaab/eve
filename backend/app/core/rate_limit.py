import logging
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, status

from app.core.cache import get_redis

_lock = Lock()
_requests: dict[str, deque[float]] = defaultdict(deque)
logger = logging.getLogger(__name__)


def enforce_rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    redis_client = get_redis()
    if redis_client:
        try:
            redis_key = f"eve:rate-limit:{key}"
            count = int(redis_client.incr(redis_key))
            if count == 1:
                redis_client.expire(redis_key, window_seconds)
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
                )
            return
        except HTTPException:
            raise
        except Exception as exc:
            # Redis is an optimization and distributed limiter in production;
            # local development remains usable when Redis is not running.
            logger.debug("redis_rate_limit_unavailable", extra={"error": str(exc)})

    now = monotonic()
    with _lock:
        bucket = _requests[key]
        while bucket and now - bucket[0] >= window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )
        bucket.append(now)
