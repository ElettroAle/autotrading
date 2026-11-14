# Loaded only here, when the worker composes the gateway: the API never pays for the library (ADR 0148).
lazy import litellm

from autotrading.adapters.outbound.litellm.configuration import _LiteLlmSettings
from autotrading.adapters.outbound.litellm.model_gateway import LiteLlmModelGatewayAdapter

GATEWAY_NAME = "litellm"


def litellm_adapters() -> dict[str, LiteLlmModelGatewayAdapter]:
    """The gateway of the LiteLLM library inside the worker, by its name (ADR 0109, ADR 0148)."""
    settings = _LiteLlmSettings()
    _keep_the_library_to_itself()
    gateway = LiteLlmModelGatewayAdapter(
        litellm.completion,
        litellm.model_cost,
        litellm.get_supported_openai_params,
        settings.providers,
        settings.timeout_seconds,
    )
    return {GATEWAY_NAME: gateway}


def _keep_the_library_to_itself() -> None:
    """Messages and answers never reach the logs of the library, and the library calls back nobody (ADR 0148)."""
    litellm.turn_off_message_logging = True
    litellm.suppress_debug_info = True
    litellm.callbacks = []
    litellm.success_callback = []
    litellm.failure_callback = []
