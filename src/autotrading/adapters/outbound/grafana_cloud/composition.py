import logging

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.grafana_cloud.configuration import _settings_of
from autotrading.adapters.outbound.grafana_cloud.telemetry import (
    basic_authorization,
    install_telemetry,
    otlp_providers,
    telemetry_resource,
)

operations = logging.getLogger("autotrading.telemetry")


def grafana_cloud_telemetry_adapters(source: ConfigurationSource, service_name: str) -> None:
    """Traces, metrics and logs of the service exported to Grafana Cloud; called first, so the instrumentations see
    every application, client and engine the service creates (ADR telemetria-opentelemetry-verso-grafana-cloud).
    """
    settings = _settings_of(source)
    if settings is None:
        operations.info("telemetria Grafana Cloud non configurata: nessuna esportazione")
        return
    resource = telemetry_resource(service_name, settings.version, settings.environment.value)
    authorization = basic_authorization(settings.instance_id, settings.token)
    install_telemetry(otlp_providers(settings.endpoint, authorization, resource))
