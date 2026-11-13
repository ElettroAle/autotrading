import httpx

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.worker.account_state import TIMEOUT_SECONDS
from autotrading.adapters.outbound.worker.configuration import _settings_of


def worker_adapters(source: ConfigurationSource) -> tuple[httpx.Client, str]:
    """The client that reaches the worker and the token it presents; the adapters bound to a tenant use both."""
    settings = _settings_of(source)
    return httpx.Client(base_url=settings.url, timeout=TIMEOUT_SECONDS), settings.token
