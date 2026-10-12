import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("runedrive.cache")

_redis_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        _redis_pool = aioredis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
            max_connections=50,
        )
    return _redis_pool


def get_redis_client() -> aioredis.Redis:
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def get_cache_json(key: str) -> Any | None:
    """Отримує значення з кешу Redis та десеріалізує JSON.

    При відсутності ключа повертає None.
    При відмові Redis логує помилку та повертає None (Graceful Degradation / Fallback to DB).
    """
    try:
        client = get_redis_client()
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as exc:
        logger.warning("Redis fallback: помилка читання ключа '%s': %s", key, exc)
        return None


async def set_cache_json(key: str, value: Any, ttl: int = 120) -> bool:
    """Серіалізує об'єкт у JSON та записує у Redis з вказаним TTL (у секундах).

    При відмові Redis повертає False без генерації винятку (Non-blocking fallback).
    """
    try:
        client = get_redis_client()
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        return True
    except Exception as exc:
        logger.warning("Redis fallback: помилка запису ключа '%s': %s", key, exc)
        return False


async def delete_cache(key: str) -> bool:
    """Видаляє одиночний ключ із кешу."""
    try:
        client = get_redis_client()
        await client.delete(key)
        return True
    except Exception as exc:
        logger.warning("Redis fallback: помилка видалення ключа '%s': %s", key, exc)
        return False


async def delete_cache_pattern(pattern: str) -> int:
    """Інвалідує множинні ключі за маскою (наприклад, 'items:catalog:*') через scan_iter."""
    try:
        client = get_redis_client()
        deleted_count = 0
        async for k in client.scan_iter(match=pattern, count=100):
            await client.delete(k)
            deleted_count += 1
        return deleted_count
    except Exception as exc:
        logger.warning(
            "Redis fallback: помилка скидання за маскою '%s': %s", pattern, exc
        )
        return 0


async def close_redis() -> None:
    """Коректне закриття пулу під час зупинки застосунку."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
