"""Rate limiting using slowapi with Redis or in-memory fallback."""

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

log = logging.getLogger("hetu.limiter")
settings = get_settings()

storage_uri = "memory://"
if settings.redis_url:
    storage_uri = settings.redis_url

try:
    limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)
except Exception as e:
    log.warning(f"Could not connect rate limiter to Redis ({storage_uri}), falling back to memory: {e}")
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
