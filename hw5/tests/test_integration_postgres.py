import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from model import get_or_train_model
from database import get_db_pool, close_db_pool
from repositories.user_repository import create_user
from repositories.item_repository import create_item, get_item_by_item_id, delete_item_by_item_id
from app.repositories.moderation_repository import (
    create_moderation_task,
    get_moderation_task,
    delete_moderation_results_by_item_id,
)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.integration
class TestPostgresRepositories:
    def test_create_user_and_item(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            await create_user(seller_id=50, is_verified_seller=True)
            await create_item(500, 50, "Integration item", "Desc", 1, 0)
            item = await get_item_by_item_id(500)
            assert item and item["item_id"] == 500
        run(t())

    def test_create_moderation_task_and_get(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            await create_user(seller_id=51, is_verified_seller=False)
            await create_item(501, 51, "Item 501", "D", 1, 0)
            task_id = await create_moderation_task(501)
            task = await get_moderation_task(task_id)
            assert task and task["status"] == "pending"
        run(t())

    def test_delete_moderation_results_and_item(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            await create_user(seller_id=52, is_verified_seller=True)
            await create_item(502, 52, "To delete", "D", 1, 0)
            task_id = await create_moderation_task(502)
            await delete_moderation_results_by_item_id(502)
            assert await get_moderation_task(task_id) is None
            assert await delete_item_by_item_id(502)
            assert await get_item_by_item_id(502) is None
        run(t())


@pytest.mark.integration
class TestSimplePredictIntegration:
    def test_simple_predict_positive(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            try:
                app.state.model = get_or_train_model()
            except Exception:
                app.state.model = None
            await create_user(seller_id=60, is_verified_seller=False)
            await create_item(600, 60, "Товар", "Короткое описание", 1, 0)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/simple_predict?item_id=600")
                assert r.status_code == 200
                assert "is_violation" in r.json() and "probability" in r.json()
        run(t())

    def test_simple_predict_item_not_found(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            try:
                app.state.model = get_or_train_model()
            except Exception:
                app.state.model = None
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post("/simple_predict?item_id=99999")
                assert r.status_code == 404
        run(t())


@pytest.mark.integration
class TestCloseIntegration:
    def test_close_then_simple_predict_404(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            try:
                app.state.model = get_or_train_model()
            except Exception:
                app.state.model = None
            await create_user(seller_id=70, is_verified_seller=True)
            await create_item(700, 70, "To close", "D", 1, 0)
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                assert (await c.post("/close?item_id=700")).status_code == 200
                assert (await c.post("/simple_predict?item_id=700")).status_code == 404
        run(t())

    def test_close_not_found(self):
        async def t():
            await close_db_pool()
            await get_db_pool()
            try:
                app.state.model = get_or_train_model()
            except Exception:
                app.state.model = None
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                assert (await c.post("/close?item_id=99998")).status_code == 404
        run(t())
