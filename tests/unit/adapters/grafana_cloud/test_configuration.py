"""The settings of Grafana Cloud: endpoint and instance are public, the token is a read-only file (ADR
telemetria-opentelemetry-verso-grafana-cloud); without any of the three the telemetry is off.
"""

from pathlib import Path

import pytest

from autotrading.adapters.configuration.errors import InvalidConfigurationError
from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.grafana_cloud.configuration import _GrafanaCloudSettings, _settings_of
from autotrading.domain.accounts.installation_environment import InstallationEnvironment

ENDPOINT = "https://otlp-gateway-prod-eu-north-0.grafana.net/otlp"
INSTANCE = "1932769"
TOKEN = "glc_secret-token"  # noqa: S105 - a made-up token of a fake stack


def configured(tmp_path: Path, stored: str = TOKEN, **overrides: str) -> dict[str, str]:
    location = tmp_path / "grafana_otlp_token"
    location.write_text(f"{stored}\n", encoding="utf-8")
    return {
        "APP_ENVIRONMENT": "dev",
        "APP_VERSION": "1.4.0",
        "GRAFANA_OTLP_ENDPOINT": ENDPOINT,
        "GRAFANA_INSTANCE_ID": INSTANCE,
        "GRAFANA_OTLP_TOKEN_FILE": str(location),
    } | overrides


def test_with_endpoint_instance_and_token_the_settings_carry_them_with_version_and_environment(tmp_path: Path) -> None:
    settings = _settings_of(ConfigurationSource(configured(tmp_path)))

    assert settings == _GrafanaCloudSettings(ENDPOINT, INSTANCE, TOKEN, "1.4.0", InstallationEnvironment.DEV)


@pytest.mark.parametrize(
    "missing",
    [
        {"GRAFANA_OTLP_ENDPOINT": ""},
        {"GRAFANA_OTLP_ENDPOINT": "  "},
        {"GRAFANA_INSTANCE_ID": ""},
        {"GRAFANA_OTLP_TOKEN_FILE": ""},
        {"GRAFANA_OTLP_TOKEN_FILE": "/run/secrets/absent"},
    ],
    ids=["no-endpoint", "blank-endpoint", "no-instance", "no-token-file", "absent-token-file"],
)
def test_without_any_of_the_three_settings_the_telemetry_is_off(tmp_path: Path, missing: dict[str, str]) -> None:
    assert _settings_of(ConfigurationSource(configured(tmp_path, **missing))) is None


def test_an_empty_token_file_leaves_the_telemetry_off(tmp_path: Path) -> None:
    assert _settings_of(ConfigurationSource(configured(tmp_path, stored=" "))) is None


def test_with_the_telemetry_off_the_environment_is_not_required(tmp_path: Path) -> None:
    configuration = configured(tmp_path, GRAFANA_OTLP_ENDPOINT="")
    del configuration["APP_ENVIRONMENT"]

    assert _settings_of(ConfigurationSource(configuration)) is None


def test_the_endpoint_loses_its_trailing_slash(tmp_path: Path) -> None:
    settings = _settings_of(ConfigurationSource(configured(tmp_path, GRAFANA_OTLP_ENDPOINT=f"{ENDPOINT}/")))

    assert settings is not None
    assert settings.endpoint == ENDPOINT


def test_without_a_version_the_settings_have_none(tmp_path: Path) -> None:
    settings = _settings_of(ConfigurationSource(configured(tmp_path, APP_VERSION="")))

    assert settings is not None
    assert settings.version is None


@pytest.mark.parametrize("endpoint", ["otlp-gateway.grafana.net/otlp", "ftp://otlp.grafana.net", "https://"])
def test_an_endpoint_that_is_not_a_web_address_refuses_to_start(tmp_path: Path, endpoint: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="GRAFANA_OTLP_ENDPOINT"):
        _settings_of(ConfigurationSource(configured(tmp_path, GRAFANA_OTLP_ENDPOINT=endpoint)))


@pytest.mark.parametrize("instance", ["stack-1932769", "19327 69", "-1"])
def test_an_instance_that_is_not_a_number_refuses_to_start(tmp_path: Path, instance: str) -> None:
    with pytest.raises(InvalidConfigurationError, match="GRAFANA_INSTANCE_ID"):
        _settings_of(ConfigurationSource(configured(tmp_path, GRAFANA_INSTANCE_ID=instance)))


def test_the_token_never_appears_in_the_settings_repr() -> None:
    settings = _GrafanaCloudSettings(ENDPOINT, INSTANCE, TOKEN, None, InstallationEnvironment.DEV)

    assert TOKEN not in repr(settings)
