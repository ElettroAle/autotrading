from fastapi.testclient import TestClient

from autotrading.adapters.inbound.api.app import ENVIRONMENT_HEADER, HealthReport, create_api


def client_for(environment: str) -> TestClient:
    return TestClient(create_api(HealthReport(version="1.2.1-dev.57", environment=environment)))


def test_health_reports_version_and_environment() -> None:
    response = client_for("dev").get("/health")

    assert response.status_code == 200
    assert response.json() == {"version": "1.2.1-dev.57", "environment": "dev"}


def test_every_response_declares_the_environment() -> None:
    client = client_for("prod")

    responses = [client.get("/health"), client.get("/does-not-exist"), client.post("/health")]

    assert [response.status_code for response in responses] == [200, 404, 405]
    assert [response.headers[ENVIRONMENT_HEADER] for response in responses] == ["prod", "prod", "prod"]
