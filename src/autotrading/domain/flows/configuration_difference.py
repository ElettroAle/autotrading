from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.flows.risk_limits import (
    LEVERAGE,
    MARGIN_EXPOSURE,
    TOTAL_MARGIN_EXPOSURE,
    TOTAL_VALUE_EXPOSURE,
    VALUE_EXPOSURE,
)
from autotrading.domain.flows.selections import ActiveSource, AdapterParameterValue, SourceSelection
from autotrading.domain.italian_text import money_text, number_text

NONE = "nessuno"
DEFAULT = "predefinito"
DEFAULT_STOP_LOSS = "stop loss predefinito"
DEFAULT_TAKE_PROFIT = "take profit predefinito"
MINIMUM_CONFIDENCE = "confidenza minima"
NO_MINIMUM_CONFIDENCE = "nessuna"
MEMORY = "memoria"
TRAILING_DISTANCE = "distanza dello stop che segue"
TRAILING_ACTIVATION = "attivazione dello stop che segue"
TRAILING_BREAKEVEN = "pareggio"
TRAILING_MAX_PROFIT = "massimo profitto raggiunto nel contesto dell'agente"
CONSECUTIVE_LOSS_LIMIT = "blocco delle riaperture dopo perdite consecutive"
ACCOUNT_EXPOSURE_FOR_AGENT = "esposizione del conto nel contesto dell'agente"


@dataclass(frozen=True, slots=True)
class ConfigurationDifference:
    """One part of the configuration that changed between two versions, as text (R1.1.3)."""

    part: str
    before: str
    after: str


def differences(before: FlowConfiguration, after: FlowConfiguration) -> tuple[ConfigurationDifference, ...]:
    """The parts that differ, in the order of the configuration; the version number itself is not a part."""
    texts = ((part, text_of(before), text_of(after)) for part, text_of in _PARTS)
    return tuple(ConfigurationDifference(part, old, new) for part, old, new in texts if old != new)


def _parameters(parameters: Mapping[str, object]) -> str:
    return ", ".join(f"{key} {parameters[key]}" for key in sorted(parameters)) or NONE


def _source(source: SourceSelection) -> str:
    """Every adapter of the source with its weight and its parameters (R4.1.1)."""
    return "; ".join(
        f"{ActiveSource(source.name, adapter.name).label} (peso {adapter.weight}"
        + "".join(f", {key} {_parameter(adapter.parameters[key])}" for key in sorted(adapter.parameters))
        + ")"
        for adapter in source.adapters
    )


def _parameter(value: AdapterParameterValue) -> str:
    """A list as the user writes it: [7, 30, 90]."""
    if isinstance(value, tuple):
        return f"[{', '.join(str(each) for each in value)}]"
    return str(value)


def _money(amount: Decimal | None) -> str:
    return NONE if amount is None else money_text(amount)


def _count(count: int | None) -> str:
    return NONE if count is None else str(count)


def _percent(percent: Decimal | None) -> str:
    return NONE if percent is None else f"{number_text(percent)}%"


_PARTS: tuple[tuple[str, Callable[[FlowConfiguration], str]], ...] = (
    ("asset", lambda configuration: ", ".join(configuration.assets)),
    ("intervallo di ciclo", lambda configuration: f"{configuration.cycle_interval.minutes} minuti"),
    ("modello", lambda configuration: configuration.model.name),
    ("parametri del modello", lambda configuration: _parameters(configuration.model.parameters)),
    ("fonti", lambda configuration: "; ".join(_source(source) for source in configuration.sources) or NONE),
    ("istruzioni", lambda configuration: configuration.instructions),
    (LEVERAGE, lambda configuration: str(configuration.risk_limits.max_leverage)),
    (MARGIN_EXPOSURE, lambda configuration: _percent(configuration.risk_limits.max_margin_exposure_percent)),
    (VALUE_EXPOSURE, lambda configuration: _percent(configuration.risk_limits.max_value_exposure_percent)),
    (
        TOTAL_MARGIN_EXPOSURE,
        lambda configuration: _percent(configuration.risk_limits.max_total_margin_exposure_percent),
    ),
    (
        TOTAL_VALUE_EXPOSURE,
        lambda configuration: _percent(configuration.risk_limits.max_total_value_exposure_percent),
    ),
    ("capitale allocato", lambda configuration: _money(configuration.allocated_capital)),
    ("porta al minimo", lambda configuration: "sì" if configuration.bring_to_minimum else "no"),
    (
        "system prompt",
        lambda configuration: DEFAULT if configuration.system_prompt is None else configuration.system_prompt,
    ),
    (
        "cicli falliti consecutivi massimi",
        lambda configuration: _count(configuration.max_consecutive_failures),
    ),
    ("perdita giornaliera massima", lambda configuration: _percent(configuration.max_daily_loss_percent)),
    ("perdita massima dal picco", lambda configuration: _percent(configuration.max_drawdown_percent)),
    ("ripresa delle aperture", lambda configuration: configuration.openings_resume.label),
    (DEFAULT_STOP_LOSS, lambda configuration: _percent(configuration.protection_defaults.stop_loss_percent)),
    (DEFAULT_TAKE_PROFIT, lambda configuration: _percent(configuration.protection_defaults.take_profit_percent)),
    (
        MINIMUM_CONFIDENCE,
        lambda configuration: str(configuration.minimum_confidence or NO_MINIMUM_CONFIDENCE),
    ),
    (MEMORY, lambda configuration: str(configuration.memory)),
    (TRAILING_DISTANCE, lambda configuration: _percent(configuration.trailing_stop.distance_percent)),
    (TRAILING_ACTIVATION, lambda configuration: _percent(configuration.trailing_stop.activation_percent)),
    (TRAILING_BREAKEVEN, lambda configuration: _percent(configuration.trailing_stop.breakeven_percent)),
    (TRAILING_MAX_PROFIT, lambda configuration: "sì" if configuration.trailing_stop.max_profit_in_context else "no"),
    (CONSECUTIVE_LOSS_LIMIT, lambda configuration: str(configuration.consecutive_loss_limit or NONE)),
    (ACCOUNT_EXPOSURE_FOR_AGENT, lambda configuration: "sì" if configuration.account_exposure_for_agent else "no"),
)
