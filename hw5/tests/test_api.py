


import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from main import app
from app.workers.moderation_worker import process_moderation_message
from models.schemas import PredictResponse, ModerationResultResponse


class TestSuccessfulPredictions:
    def test_prediction_with_violation(self, client: TestClient):
        data = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 100,
            "name": "Товар",
            "description": "Короткое описание",
            "category": 1,
            "images_qty": 0,
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "is_violation" in result
        assert "probability" in result
        assert isinstance(result["is_violation"], bool)
        assert isinstance(result["probability"], float)
        assert 0.0 <= result["probability"] <= 1.0

    def test_prediction_without_violation(self, client: TestClient):
        data = {
            "seller_id": 2,
            "is_verified_seller": True,
            "item_id": 101,
            "name": "Товар 2",
            "description": "Длинное описание товара с подробностями",
            "category": 50,
            "images_qty": 5,
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "is_violation" in result
        assert "probability" in result


class TestSimplePredictUnit:

    def test_simple_predict_cache_miss_then_set(self, client: TestClient):
        mock_get_cached = AsyncMock(return_value=None)
        mock_predict_from_db = AsyncMock(
            return_value=PredictResponse(is_violation=False, probability=0.2)
        )
        mock_set = AsyncMock()
        with patch(
            "routes.predict_router.get_cached_prediction_by_item", mock_get_cached
        ), patch(
            "routes.predict_router.predict_from_db", mock_predict_from_db
        ), patch(
            "routes.predict_router.set_cached_prediction_by_item", mock_set
        ):
            response = client.post("/simple_predict?item_id=200")
            assert response.status_code == 200
            mock_get_cached.assert_called_once_with(200)
            mock_predict_from_db.assert_called_once()
            mock_set.assert_called_once()
            assert mock_set.call_args[0][0] == 200
            assert mock_set.call_args[0][1].is_violation is False

    def test_simple_predict_cache_hit_no_db(self, client: TestClient):
        cached = PredictResponse(is_violation=True, probability=0.9)
        mock_get_cached = AsyncMock(return_value=cached)
        mock_predict_from_db = AsyncMock()
        with patch(
            "routes.predict_router.get_cached_prediction_by_item", mock_get_cached
        ), patch(
            "routes.predict_router.predict_from_db", mock_predict_from_db
        ):
            response = client.post("/simple_predict?item_id=200")
            assert response.status_code == 200
            assert response.json()["is_violation"] is True
            assert response.json()["probability"] == 0.9
            mock_get_cached.assert_called_once_with(200)
            mock_predict_from_db.assert_not_called()

    def test_simple_predict_item_not_found(self, client: TestClient):
        # get_item_by_item_id вызывается внутри predict_from_db (services.predict_service)
        mock_get_cached = AsyncMock(return_value=None)
        mock_get_item = AsyncMock(return_value=None)
        with patch(
            "routes.predict_router.get_cached_prediction_by_item", mock_get_cached
        ), patch(
            "services.predict_service.get_item_by_item_id", mock_get_item
        ):
            response = client.post("/simple_predict?item_id=99999")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestValidation:
    def test_missing_required_field(self, client: TestClient):
        data = {
            "seller_id": 1,
            "is_verified_seller": True,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 2,
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "field,invalid_value,expected_status",
        [
            ("seller_id", 0, 422),
            ("item_id", -1, 422),
            ("name", "", 422),
            ("images_qty", -1, 422),
        ],
    )
    def test_validation_wrong_values(
        self, client: TestClient, field, invalid_value, expected_status
    ):
        data = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 2,
        }
        data[field] = invalid_value
        response = client.post("/predict", json=data)
        assert response.status_code == expected_status

    def test_empty_request_body(self, client: TestClient):
        response = client.post("/predict", json={})
        assert response.status_code == 422


class TestModelUnavailable:
    def test_model_unavailable(self, client: TestClient):
        original_model = app.state.model
        app.state.model = None
        try:
            data = {
                "seller_id": 1,
                "is_verified_seller": True,
                "item_id": 100,
                "name": "Товар",
                "description": "Описание",
                "category": 1,
                "images_qty": 2,
            }
            response = client.post("/predict", json=data)
            assert response.status_code == 503
            assert "Service Unavailable" in response.json()["detail"]
        finally:
            app.state.model = original_model


class TestPredictCacheUnit:

    def test_predict_cache_miss_then_set(self, client: TestClient):
        mock_get_cached = AsyncMock(return_value=None)
        mock_set_cached = AsyncMock()
        data = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "X",
            "description": "Y",
            "category": 1,
            "images_qty": 0,
        }
        with patch(
            "routes.predict_router.get_cached_prediction_by_request", mock_get_cached
        ), patch(
            "routes.predict_router.set_cached_prediction_by_request", mock_set_cached
        ):
            response = client.post("/predict", json=data)
            assert response.status_code == 200
            mock_get_cached.assert_called_once()
            mock_set_cached.assert_called_once()
            assert mock_set_cached.call_args[0][1].probability >= 0

    def test_predict_cache_hit(self, client: TestClient):
        mock_get_cached = AsyncMock(
            return_value=PredictResponse(is_violation=True, probability=0.88)
        )
        data = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 100,
            "name": "X",
            "description": "Y",
            "category": 1,
            "images_qty": 0,
        }
        with patch(
            "routes.predict_router.get_cached_prediction_by_request", mock_get_cached
        ):
            response = client.post("/predict", json=data)
            assert response.status_code == 200
            assert response.json()["probability"] == 0.88
            mock_get_cached.assert_called_once()


class TestAsyncPredict:
    def test_async_predict_success(self, client: TestClient):
        mock_get_item = AsyncMock(return_value={
            "item_id": 100,
            "seller_id": 1,
            "name": "Item",
            "description": "Desc",
            "category": 1,
            "images_qty": 0,
            "is_verified_seller": False,
        })
        mock_create_task = AsyncMock(return_value=42)
        mock_send_kafka = AsyncMock(return_value=None)
        with patch(
            "routes.predict_router.get_item_by_item_id", mock_get_item
        ), patch(
            "routes.predict_router.create_moderation_task", mock_create_task
        ), patch(
            "routes.predict_router.send_moderation_request", mock_send_kafka
        ):
            response = client.post("/async_predict", json={"item_id": 100})
            assert response.status_code == 200
            body = response.json()
            assert body["task_id"] == 42
            assert body["status"] == "pending"
            mock_get_item.assert_called_once_with(100)
            mock_create_task.assert_called_once_with(100)
            mock_send_kafka.assert_called_once_with(100)

    def test_async_predict_item_not_found(self, client: TestClient):
        mock_get_item = AsyncMock(return_value=None)
        with patch(
            "routes.predict_router.get_item_by_item_id", mock_get_item
        ):
            response = client.post("/async_predict", json={"item_id": 999})
            assert response.status_code == 404

    def test_async_predict_kafka_failure_marks_task_failed(self, client: TestClient):
        mock_get_item = AsyncMock(return_value={
            "item_id": 100,
            "seller_id": 1,
            "name": "x",
            "description": "y",
            "category": 1,
            "images_qty": 0,
            "is_verified_seller": False,
        })
        mock_create_task = AsyncMock(return_value=7)
        mock_update = AsyncMock()
        mock_send_kafka = AsyncMock(side_effect=Exception("Kafka unavailable"))
        with patch(
            "routes.predict_router.get_item_by_item_id", mock_get_item
        ), patch(
            "routes.predict_router.create_moderation_task", mock_create_task
        ), patch(
            "routes.predict_router.update_moderation_result", mock_update
        ), patch(
            "routes.predict_router.send_moderation_request", mock_send_kafka
        ):
            response = client.post("/async_predict", json={"item_id": 100})
            assert response.status_code == 500
            mock_update.assert_called_once()
            call_kw = mock_update.call_args[1]
            assert call_kw["task_id"] == 7
            assert call_kw["status"] == "failed"


class TestModerationResult:
    def test_get_moderation_result_success(self, client: TestClient):
        mock_get_task = AsyncMock(return_value={
            "id": 1,
            "item_id": 100,
            "status": "completed",
            "is_violation": True,
            "probability": 0.85,
            "error_message": None,
            "created_at": None,
            "processed_at": None,
        })
        with patch(
            "routes.predict_router.get_moderation_task", mock_get_task
        ):
            response = client.get("/moderation_result/1")
            assert response.status_code == 200
            body = response.json()
            assert body["task_id"] == 1
            assert body["status"] == "completed"
            assert body["is_violation"] is True
            assert body["probability"] == 0.85

    def test_get_moderation_result_not_found(self, client: TestClient):
        mock_get_task = AsyncMock(return_value=None)
        with patch(
            "routes.predict_router.get_moderation_task", mock_get_task
        ):
            response = client.get("/moderation_result/999")
            assert response.status_code == 404

    def test_get_moderation_result_cache_hit(self, client: TestClient):
        mock_get_cached = AsyncMock(return_value=ModerationResultResponse(
            task_id=1,
            status="completed",
            is_violation=False,
            probability=0.1,
            error_message=None,
        ))
        mock_get_task = AsyncMock()
        with patch(
            "routes.predict_router.get_cached_moderation_result", mock_get_cached
        ), patch(
            "routes.predict_router.get_moderation_task", mock_get_task
        ):
            response = client.get("/moderation_result/1")
            assert response.status_code == 200
            assert response.json()["probability"] == 0.1
            mock_get_task.assert_not_called()


class TestCloseUnit:

    def test_close_success(self, client: TestClient):
        mock_get_item = AsyncMock(return_value={"item_id": 100, "seller_id": 1})
        mock_del_mod = AsyncMock()
        mock_del_item = AsyncMock(return_value=True)
        mock_del_cache = AsyncMock()
        with patch(
            "routes.predict_router.get_item_by_item_id", mock_get_item
        ), patch(
            "routes.predict_router.delete_moderation_results_by_item_id", mock_del_mod
        ), patch(
            "routes.predict_router.delete_item_by_item_id", mock_del_item
        ), patch(
            "routes.predict_router.delete_cached_prediction_for_item", mock_del_cache
        ):
            response = client.post("/close?item_id=100")
            assert response.status_code == 200
            mock_get_item.assert_called_once_with(100)
            mock_del_mod.assert_called_once_with(100)
            mock_del_item.assert_called_once_with(100)
            mock_del_cache.assert_called_once_with(100)

    def test_close_not_found(self, client: TestClient):
        mock_get_item = AsyncMock(return_value=None)
        with patch(
            "routes.predict_router.get_item_by_item_id", mock_get_item
        ):
            response = client.post("/close?item_id=999")
            assert response.status_code == 404


@pytest.mark.asyncio
class TestModerationWorker:
    async def test_process_message_success_then_commit(self):
        mock_model = MagicMock()
        message_data = {"item_id": 1}
        item_data = {
            "item_id": 1,
            "seller_id": 1,
            "name": "x",
            "description": "y",
            "category": 1,
            "images_qty": 0,
            "is_verified_seller": False,
        }

        with patch(
            "app.workers.moderation_worker.get_item_by_item_id",
            new_callable=AsyncMock,
            return_value=item_data,
        ), patch(
            "app.workers.moderation_worker.get_pending_task_by_item_id",
            new_callable=AsyncMock,
            return_value=10,
        ), patch(
            "app.workers.moderation_worker.update_moderation_result",
            new_callable=AsyncMock,
        ) as mock_update, patch(
            "app.workers.moderation_worker.predict_moderation",
            return_value=PredictResponse(is_violation=False, probability=0.1),
        ):
            await process_moderation_message(message_data, mock_model)

        mock_update.assert_called_once()
        call_kw = mock_update.call_args[1]
        assert call_kw["status"] == "completed"
        assert call_kw["is_violation"] is False

    async def test_process_message_retry_then_dlq(self):
        from app.workers.moderation_worker import MAX_RETRIES

        mock_model = MagicMock()
        message_data = {"item_id": 2}
        get_item = AsyncMock(side_effect=Exception("DB error"))
        get_pending = AsyncMock(return_value=20)
        update_result = AsyncMock()
        send_dlq = AsyncMock()

        with patch(
            "app.workers.moderation_worker.get_item_by_item_id", get_item
        ), patch(
            "app.workers.moderation_worker.get_pending_task_by_item_id", get_pending
        ), patch(
            "app.workers.moderation_worker.update_moderation_result", update_result
        ), patch(
            "app.workers.moderation_worker.send_to_dlq", send_dlq
        ):
            await process_moderation_message(message_data, mock_model)

        assert get_item.call_count == MAX_RETRIES
        update_result.assert_called_once()
        call_kw = update_result.call_args[1]
        assert call_kw["task_id"] == 20
        assert call_kw["status"] == "failed"
        send_dlq.assert_called_once()
        assert send_dlq.call_args[1].get("retry_count") == MAX_RETRIES
