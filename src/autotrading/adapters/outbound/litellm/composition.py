from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.litellm.configuration import _settings_of
from autotrading.adapters.outbound.litellm.model_call import LiteLlmModelCallAdapter, litellm_model_call
from autotrading.adapters.outbound.litellm.model_catalog import LiteLlmModelCatalogAdapter, litellm_model_catalog


def litellm_adapters(source: ConfigurationSource) -> tuple[LiteLlmModelCallAdapter, LiteLlmModelCatalogAdapter]:
    """The model call and the catalog of the models, through the proxy of the installation (ADR 0101, ADR 0103)."""
    settings = _settings_of(source)
    model_call = litellm_model_call(settings.url, settings.master_key)
    return model_call, litellm_model_catalog(settings.url, settings.master_key)
