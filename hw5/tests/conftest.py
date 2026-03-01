import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from model import get_or_train_model


@pytest.fixture(scope="module")
def client():
    try:
        app.state.model = get_or_train_model()
    except Exception:
        app.state.model = None
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_redis_for_unit_tests(request):
    if "test_integration_redis" in getattr(request.module, "__name__", ""):
        yield
        return
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock(return_value=None)
    mock.delete = AsyncMock(return_value=None)
    mock.ttl = AsyncMock(return_value=3600)
    with patch("app.storages.cache_storage.get_redis", new_callable=AsyncMock, return_value=mock):
        yield
