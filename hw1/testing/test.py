from fastapi.testclient import TestClient
from hw1.models.main import app

client = TestClient(app)

def test_positive_verified_seller():
    data = {
        "seller_id": 1,
        "is_verified_seller": True,
        "item_id": 100,
        "name": "Товар",
        "description": "Описание",
        "category": 1,
        "images_qty": 0
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    assert response.json() is True


def test_positive_unverified_with_images():
    data = {
        "seller_id": 2,
        "is_verified_seller": False,
        "item_id": 200,
        "name": "Товар",
        "description": "Описание",
        "category": 2,
        "images_qty": 3
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    assert response.json() is True


def test_negative_unverified_without_images():
    data = {
        "seller_id": 3,
        "is_verified_seller": False,
        "item_id": 300,
        "name": "Товар",
        "description": "Описание",
        "category": 3,
        "images_qty": 0
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 200
    assert response.json() is False


def test_validation_missing_field():
    data = {
        "seller_id": 1,
        "is_verified_seller": True,
        # item_id: X,
        "name": "Товар",
        "description": "Описание",
        "category": 1,
        "images_qty": 2
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 422


def test_validation_wrong_type():
    data = {
        "seller_id": "something",
        "is_verified_seller": True,
        "item_id": 100,
        "name": "Товар",
        "description": "Описание",
        "category": 1,
        "images_qty": 2
    }
    response = client.post("/predict", json=data)
    assert response.status_code == 422