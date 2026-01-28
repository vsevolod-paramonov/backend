import pytest
from fastapi.testclient import TestClient
from main import app
from model import get_or_train_model

try:
    app.state.model = get_or_train_model()
except Exception:
    app.state.model = None

client = TestClient(app)


class TestSuccessfulPredictions:
    """Тесты для успешных предсказаний"""
    
    def test_prediction_with_violation(self):
        """Тест успешного предсказания (is_violation = True)"""
        data = {
            "seller_id": 1,
            "is_verified_seller": False,
            "item_id": 100,
            "name": "Товар",
            "description": "Короткое описание",
            "category": 1,
            "images_qty": 0
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "is_violation" in result
        assert "probability" in result
        assert isinstance(result["is_violation"], bool)
        assert isinstance(result["probability"], float)
        assert 0.0 <= result["probability"] <= 1.0
    
    def test_prediction_without_violation(self):
        """Тест успешного предсказания (is_violation = False)"""
        data = {
            "seller_id": 2,
            "is_verified_seller": True,
            "item_id": 101,
            "name": "Товар 2",
            "description": "Длинное описание товара с подробностями",
            "category": 50,
            "images_qty": 5
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 200
        result = response.json()
        assert "is_violation" in result
        assert "probability" in result
        assert isinstance(result["is_violation"], bool)
        assert isinstance(result["probability"], float)
        assert 0.0 <= result["probability"] <= 1.0


class TestValidation:
    """Тесты для валидации входных данных"""
    
    def test_missing_required_field(self):
        """Проверка отсутствия обязательного поля"""
        data = {
            "seller_id": 1,
            "is_verified_seller": True,
            # item_id отсутствует
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 2
        }
        response = client.post("/predict", json=data)
        assert response.status_code == 422
    
    @pytest.mark.parametrize("field,invalid_value,expected_status", [
        ("seller_id", "not_an_int", 422),
        ("seller_id", 0, 422),
        ("seller_id", -1, 422),
        ("is_verified_seller", "not_a_bool", 422),
        ("item_id", "not_an_int", 422),
        ("item_id", 0, 422),
        ("item_id", -1, 422),
        ("name", 123, 422),
        ("name", "", 422),
        ("description", 123, 422),
        ("description", "", 422),
        ("category", "not_an_int", 422),
        ("category", 0, 422),
        ("category", -1, 422),
        ("images_qty", "not_an_int", 422),
        ("images_qty", -1, 422),
    ])
    def test_validation_wrong_types_and_values(self, field, invalid_value, expected_status):
        """Параметризованный тест для проверки валидации типов и значений"""
        data = {
            "seller_id": 1,
            "is_verified_seller": True,
            "item_id": 100,
            "name": "Товар",
            "description": "Описание",
            "category": 1,
            "images_qty": 2
        }
        data[field] = invalid_value
        response = client.post("/predict", json=data)
        assert response.status_code == expected_status
    
    def test_empty_request_body(self):
        """Проверка пустого тела запроса"""
        response = client.post("/predict", json={})
        assert response.status_code == 422


class TestModelUnavailable:
    """Тесты для обработки ошибок при недоступной модели"""
    
    def test_model_unavailable(self):
        """Тест обработки ошибки при недоступной модели"""
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
                "images_qty": 2
            }
            response = client.post("/predict", json=data)
            assert response.status_code == 503
            assert "detail" in response.json()
            assert "Service Unavailable" in response.json()["detail"]
        finally:
            app.state.model = original_model
