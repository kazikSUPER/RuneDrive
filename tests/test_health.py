from fastapi.testclient import TestClient

from app.main import app


def test_liveness_health_check_endpoint():
    """Тестування ендпоінту перевірки працездатності мікросервісу."""
    testing_client = TestClient(app)
    response_payload = testing_client.get("/api/v1/health")

    assert response_payload.status_code == 200
    response_json_data = response_payload.json()
    assert response_json_data["status"] == "healthy"
    assert "version" in response_json_data
    assert "project" in response_json_data
