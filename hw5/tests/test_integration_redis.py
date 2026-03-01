import pytest
import asyncio
import os
import redis.asyncio as aioredis
from app.storages.cache_storage import (
    get_cached_prediction_by_item,
    set_cached_prediction_by_item,
    delete_cached_prediction_for_item,
    get_cached_moderation_result,
    set_cached_moderation_result,
    PREDICTION_CACHE_TTL_SEC,
)
from models.schemas import PredictResponse, ModerationResultResponse


@pytest.fixture(scope="module", autouse=True)
def skip_if_redis_unavailable():
    try:
        async def check():
            r = aioredis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
            )
            await r.ping()
            await r.aclose()
        asyncio.run(check())
    except Exception as e:
        pytest.skip(f"Redis не запущен: {e}")


@pytest.fixture(autouse=True)
async def reset_redis_before_each_test():
    """Сброс глобального клиента Redis перед каждым тестом, чтобы не было Event loop is closed."""
    from app.clients.redis_client import close_redis
    await close_redis()
    yield


@pytest.mark.integration
@pytest.mark.asyncio
class TestCacheStorageIntegration:
    async def test_set_and_get_prediction_by_item(self):
        await set_cached_prediction_by_item(99991, PredictResponse(is_violation=True, probability=0.75))
        cached = await get_cached_prediction_by_item(99991)
        assert cached is not None
        assert cached.is_violation is True
        assert cached.probability == 0.75
        await delete_cached_prediction_for_item(99991)

    async def test_get_prediction_miss_returns_none(self):
        cached = await get_cached_prediction_by_item(99992)
        assert cached is None

    async def test_delete_prediction_then_get_returns_none(self):
        await set_cached_prediction_by_item(99993, PredictResponse(is_violation=False, probability=0.1))
        await delete_cached_prediction_for_item(99993)
        assert await get_cached_prediction_by_item(99993) is None

    async def test_set_and_get_moderation_result(self):
        res = ModerationResultResponse(task_id=88881, status="completed", is_violation=False, probability=0.2, error_message=None)
        await set_cached_moderation_result(88881, res)
        cached = await get_cached_moderation_result(88881)
        assert cached is not None
        assert cached.status == "completed"
        assert cached.probability == 0.2

    async def test_prediction_ttl_set(self):
        from app.clients.redis_client import get_redis
        await set_cached_prediction_by_item(99994, PredictResponse(is_violation=False, probability=0.5))
        r = await get_redis()
        ttl = await r.ttl("prediction:item:99994")
        await r.delete("prediction:item:99994")
        assert 0 < ttl <= PREDICTION_CACHE_TTL_SEC
