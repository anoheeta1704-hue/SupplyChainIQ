# ============================================
# SupplyChainIQ — Redis Client
# ============================================
import json
import time
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class _InMemoryRedis:
    def __init__(self):
        self._store = {}
        self._exp = {}

    async def get(self, key: str) -> Optional[str]:
        if key in self._exp and time.time() > self._exp[key]:
            self._store.pop(key, None)
            self._exp.pop(key, None)
            return None
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        if ex:
            self._exp[key] = time.time() + ex
        else:
            self._exp.pop(key, None)
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                self._exp.pop(k, None)
                count += 1
        return count

    async def scan_iter(self, match: str = "*"):
        import fnmatch
        now = time.time()
        for k in list(self._store.keys()):
            if k in self._exp and now > self._exp[k]:
                self._store.pop(k, None)
                self._exp.pop(k, None)
                continue
            if fnmatch.fnmatch(k, match):
                yield k

    async def incr(self, key: str) -> int:
        val = int(await self.get(key) or 0) + 1
        # Store new value while preserving existing TTL in _exp
        self._store[key] = str(val)
        return val

    async def ping(self) -> bool:
        return True

    async def close(self):
        pass


_redis_pool: Optional[Any] = None
_use_memory = False


async def get_redis() -> Any:
    """Get or create the Redis connection pool with memory fallback."""
    global _redis_pool, _use_memory
    if _redis_pool is not None:
        return _redis_pool

    if not _use_memory:
        try:
            pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10,
                socket_timeout=0.5,
            )
            # Test ping
            await pool.ping()
            _redis_pool = pool
            logger.info("redis_connected", url=settings.REDIS_URL)
            return _redis_pool
        except Exception:
            _use_memory = True
            logger.info("redis_offline_using_in_memory_cache")

    _redis_pool = _InMemoryRedis()
    return _redis_pool


async def close_redis():
    """Close the Redis connection pool."""
    global _redis_pool
    if _redis_pool and hasattr(_redis_pool, "close"):
        await _redis_pool.close()
        _redis_pool = None



class RedisCache:
    """High-level caching operations for the application."""

    # TTL defaults (seconds)
    STATUS_TTL = 300         # 5 min for shipment status
    KPI_TTL = 120            # 2 min for dashboard KPIs
    LIST_TTL = 60            # 1 min for list queries

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        r = await get_redis()
        try:
            val = await r.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.warning("redis_get_error", key=key, error=str(e))
            return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 300) -> bool:
        r = await get_redis()
        try:
            await r.set(key, json.dumps(value, default=str), ex=ttl)
            return True
        except Exception as e:
            logger.warning("redis_set_error", key=key, error=str(e))
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        r = await get_redis()
        try:
            await r.delete(key)
            return True
        except Exception as e:
            logger.warning("redis_delete_error", key=key, error=str(e))
            return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        r = await get_redis()
        try:
            keys = []
            async for key in r.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await r.delete(*keys)
            return 0
        except Exception as e:
            logger.warning("redis_delete_pattern_error", pattern=pattern, error=str(e))
            return 0

    # ---- Shipment Status ----
    @staticmethod
    async def set_shipment_status(shipment_id: str, status_data: dict):
        key = f"shipment:{shipment_id}:status"
        await RedisCache.set(key, status_data, ttl=RedisCache.STATUS_TTL)

    @staticmethod
    async def get_shipment_status(shipment_id: str) -> Optional[dict]:
        key = f"shipment:{shipment_id}:status"
        return await RedisCache.get(key)

    # ---- Dashboard KPIs ----
    @staticmethod
    async def set_dashboard_kpis(kpis: dict):
        await RedisCache.set("dashboard:kpis", kpis, ttl=RedisCache.KPI_TTL)

    @staticmethod
    async def get_dashboard_kpis() -> Optional[dict]:
        return await RedisCache.get("dashboard:kpis")

    # ---- Rate Limiting ----
    @staticmethod
    async def check_rate_limit(client_ip: str, limit: int = 60, window: int = 60) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        r = await get_redis()
        key = f"ratelimit:{client_ip}"
        try:
            current = await r.get(key)
            if current is None:
                await r.set(key, 1, ex=window)
                return True
            if int(current) >= limit:
                return False
            await r.incr(key)
            return True
        except Exception as e:
            logger.warning("rate_limit_error", error=str(e))
            return True  # Fail open
