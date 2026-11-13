from openai import OpenAI

from autotrading.adapters.configuration.source import ConfigurationSource
from autotrading.adapters.outbound.litellm.configuration import _settings_of
from autotrading.adapters.outbound.litellm.model_call import TIMEOUT_SECONDS
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter

GATEWAY_NAME = "litellm"


def litellm_adapters(source: ConfigurationSource) -> dict[str, LiteLlmModelGatewayAdapter]:
    """The gateway of the proxy of the installation, by its name (ADR 0101, ADR 0103, ADR 0109).

    The proxy is reached at its internal address with the master key, with no retries: the next cycle retries.
    """
    settings = _settings_of(source)
    client = OpenAI(api_key=settings.master_key, base_url=settings.url, timeout=TIMEOUT_SECONDS, max_retries=0)
    return {GATEWAY_NAME: LiteLlmModelGatewayAdapter(client)}
