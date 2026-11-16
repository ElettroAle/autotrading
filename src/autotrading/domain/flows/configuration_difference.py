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
from autotrading.domain.flows.selections import SourceSelection
from autotrading.domain.italian_text import money_text, number_text

NONE = "nessuno"
DEFAULT = "predefinito"
DEFAULT_STOP_LOSS = "stop loss predefinito"
DEFAULT_TAKE_PROFIT = "take profit predefinito"


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
    return (
        f"{source.name} (peso {source.weight}"
        + "".join(f", {key} {source.parameters[key]}" for key in sorted(source.parameters))
        + ")"
    )


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
)
