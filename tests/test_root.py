from fastapi.testclient import TestClient

from app.main import app


def test_root_welcome_endpoint():
    """Тестування головного кореневого ендпоінту вітання."""
    testing_client = TestClient(app)
    response_payload = testing_client.get("/")

    assert response_payload.status_code == 200
    response_json_data = response_payload.json()
    assert "message" in response_json_data
    assert "docs" in response_json_data
    assert "health" in response_json_data
