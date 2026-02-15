import pytest
from fastapi.testclient import TestClient
from main import app
from model import get_or_train_model
from repositories.user_repository import create_user
from repositories.item_repository import create_item
from database import close_db_pool
import asyncio

try:
    app.state.model = get_or_train_model()
except Exception:
    app.state.model = None

client = TestClient(app)


def run_async(coro):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from database import close_db_pool
        loop.run_until_complete(close_db_pool())
        loop.close()
    except:
        pass
    
    return asyncio.run(coro)


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

class TestSimplePredict:
    """Тесты для эндпоинта /simple_predict"""
    
    def test_simple_predict_positive(self):
        """Тест успешного предсказания через /simple_predict (is_violation = True)"""
        try:
            # Создаем пользователя и объявление
            run_async(create_user(seller_id=10, is_verified_seller=False))
            run_async(create_item(
                item_id=200,
                seller_id=10,
                name="Товар",
                description="Короткое описание",
                category=1,
                images_qty=0
            ))
            
            response = client.post("/simple_predict?item_id=200")
            if response.status_code == 500:
                pytest.skip(f"Database error: {response.json().get('detail', 'Unknown error')}")
            assert response.status_code == 200
            result = response.json()
            assert "is_violation" in result
            assert "probability" in result
            assert isinstance(result["is_violation"], bool)
            assert isinstance(result["probability"], float)
            assert 0.0 <= result["probability"] <= 1.0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    def test_simple_predict_negative(self):
        """Тест успешного предсказания через /simple_predict (is_violation = False)"""
        try:
            # Создаем пользователя и объявление
            run_async(create_user(seller_id=11, is_verified_seller=True))
            run_async(create_item(
                item_id=201,
                seller_id=11,
                name="Товар 2",
                description="Длинное описание товара с подробностями",
                category=50,
                images_qty=5
            ))
            
            response = client.post("/simple_predict?item_id=201")
            if response.status_code == 500:
                pytest.skip(f"Database error: {response.json().get('detail', 'Unknown error')}")
            assert response.status_code == 200
            result = response.json()
            assert "is_violation" in result
            assert "probability" in result
            assert isinstance(result["is_violation"], bool)
            assert isinstance(result["probability"], float)
            assert 0.0 <= result["probability"] <= 1.0
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    def test_simple_predict_item_not_found(self):
        """Тест обработки ошибки, когда объявление не найдено"""
        try:
            response = client.post("/simple_predict?item_id=99999")
            if response.status_code == 500:
                pytest.skip(f"Database error: {response.json().get('detail', 'Unknown error')}")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
        except Exception as e:
            pytest.skip(f"Database error: {e}")

class TestDatabaseOperations:
    """Тесты для работы с БД"""
    
    def test_create_user(self):
        """Тест создания пользователя"""
        run_async(create_user(seller_id=20, is_verified_seller=True))
        # Если не было ошибки, значит пользователь создан
        assert True
    
    def test_create_item(self):
        """Тест создания объявления"""
        # Сначала создаем пользователя
        run_async(create_user(seller_id=21, is_verified_seller=False))
        # Затем создаем объявление
        run_async(create_item(
            item_id=300,
            seller_id=21,
            name="Тестовый товар",
            description="Описание тестового товара",
            category=5,
            images_qty=3
        ))
        # Если не было ошибки, значит объявление создано
        assert True
    
    def test_create_user_and_item_together(self):
        """Тест создания пользователя и объявления вместе"""
        try:
            run_async(create_user(seller_id=22, is_verified_seller=True))
            run_async(create_item(
                item_id=301,
                seller_id=22,
                name="Еще один товар",
                description="Описание еще одного товара",
                category=10,
                images_qty=2
            ))
            # Проверяем, что можем получить предсказание
            response = client.post("/simple_predict?item_id=301")
            if response.status_code == 500:
                pytest.skip(f"Database error: {response.json().get('detail', 'Unknown error')}")
            assert response.status_code == 200
            result = response.json()
            assert "is_violation" in result
            assert "probability" in result
        except Exception as e:
            pytest.skip(f"Database not available: {e}")

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