import pytest
from fastapi.testclient import TestClient

from autotrading.bootstrap import MissingConfigurationError, create_application


def test_application_exposes_configured_version_and_environment() -> None:
    application = create_application({"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": "prod"})

    response = TestClient(application).get("/health")

    assert response.json() == {"version": "1.2.1", "environment": "prod"}


@pytest.mark.parametrize("missing", ["APP_VERSION", "APP_ENVIRONMENT"])
def test_application_refuses_to_start_without_required_configuration(missing: str) -> None:
    configuration = {"APP_VERSION": "1.2.1", "APP_ENVIRONMENT": "prod"}
    configuration[missing] = "  "

    with pytest.raises(MissingConfigurationError) as raised:
        create_application(configuration)

    assert raised.value.name == missing
    assert str(raised.value) == f"configurazione mancante: {missing}"
