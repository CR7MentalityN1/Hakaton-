import hashlib
import json
import logging
import time
import redis
from redis.retry import Retry
from redis.backoff import NoBackoff
from fastapi.encoders import jsonable_encoder
from app.core.config import settings

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self):
        self.unavailable_until = 0.0
        self.client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
            retry=Retry(NoBackoff(), 0),
        )

    def revision(self):
        # A failed optional cache must not add connection timeouts to every request.
        if time.monotonic() < self.unavailable_until:
            return None
        try:
            return self.client.get("crm:revision") or "0"
        except redis.RedisError:
            self.unavailable_until = time.monotonic() + 5
            return None

    def key(self, namespace, parameters, revision=None):
        if revision is None:
            revision = self.revision()
        if revision is None:
            return None
        digest = hashlib.sha256(
            json.dumps(jsonable_encoder(parameters), sort_keys=True).encode()
        ).hexdigest()
        return f"crm:{revision}:{namespace}:{digest}"

    def get(self, key):
        if not key:
            return None
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except (redis.RedisError, ValueError):
            return None

    def set(self, key, value):
        if not key:
            return
        try:
            self.client.setex(
                key,
                settings.cache_ttl,
                json.dumps(jsonable_encoder(value), ensure_ascii=False),
            )
        except redis.RedisError:
            logger.warning("Redis unavailable; serving uncached result")

    def invalidate(self):
        # Generation keys avoid SCAN/KEYS and stale in-flight writes after a mutation.
        if time.monotonic() < self.unavailable_until:
            return
        try:
            self.client.incr("crm:revision")
        except redis.RedisError:
            self.unavailable_until = time.monotonic() + 5
            logger.warning(
                "Redis invalidation unavailable; existing keys expire by TTL"
            )


cache = Cache()
