import logging
from functools import lru_cache

from redis import Redis

from app.core.settings import get_redis_settings


logger = logging.getLogger("uvicorn.error")


@lru_cache
def get_redis_cache_client() -> Redis | None:
    settings = get_redis_settings()
    if not settings.url:
        logger.info("Cache Redis desactivada: REDIS_URL no configurada")
        return None

    return Redis.from_url(
        settings.url,
        decode_responses=True,
        socket_connect_timeout=settings.socket_connect_timeout_ms / 1000,
        socket_timeout=settings.socket_timeout_ms / 1000,
        health_check_interval=30,
    )
