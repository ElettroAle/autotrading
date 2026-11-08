from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import HealthReport, create_api


def test_health_reports_version_and_environment() -> None:
    client = TestClient(create_api(HealthReport(version="1.2.1-dev.57", environment="dev")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"version": "1.2.1-dev.57", "environment": "dev"}
