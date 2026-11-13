from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.litellm.configuration import _settings_of
from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter, litellm_model_call


def litellm_adapters(source: ConfigurationSource) -> LiteLlmModelCallAdapter:
    """The model call of the worker, through the proxy of the installation (ADR 0101)."""
    settings = _settings_of(source)
    return litellm_model_call(settings.url, settings.master_key)
