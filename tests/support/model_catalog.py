"""The models the tests offer, as the model gateway describes those of the enabled providers (ADR 0103)."""

from decimal import Decimal

from autotrading.domain.agent.model_catalog import ModelCatalog
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_parameter import ChoiceParameter, ModelParameter, RangeParameter

EFFORT = ChoiceParameter("reasoning_effort", ("basso", "medio", "alto"), "medio")


def _temperature(maximum: int) -> RangeParameter:
    return RangeParameter("temperature", Decimal(0), Decimal(maximum), Decimal(1))


def _max_tokens(maximum: int, default: int = 4096) -> RangeParameter:
    return RangeParameter("max_tokens", Decimal(1), Decimal(maximum), Decimal(default), whole=True)


def _model(name: str, *parameters: ModelParameter) -> ModelDefinition:
    return ModelDefinition(name, parameters)


PLATFORM_MODELS = ModelCatalog(
    (
        _model("anthropic/claude-sonnet-5-5", _temperature(1), _max_tokens(64000), EFFORT),
        _model("anthropic/claude-haiku-5-5", _temperature(1), _max_tokens(64000)),
        _model("openai/gpt-4.1-mini", _temperature(2), _max_tokens(32768)),
        _model("deepseek/deepseek-chat", _temperature(2), _max_tokens(8192)),
        _model("deepseek/deepseek-reasoner", _max_tokens(32768, default=8192)),
        _model("openrouter/deepseek/deepseek-chat", _temperature(2), _max_tokens(8192)),
    )
)
