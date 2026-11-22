import re
from collections.abc import Mapping
from decimal import Decimal
from urllib.parse import quote

from pydantic import BaseModel, Field

from autotrading.adapters.inbound.api.source_parameters import ParameterBody, parameters_body, parameters_of
from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.application.flows.ports import AdapterRequest
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.flows.openings_resume import OpeningsResume

FORMAT = "autotrading-strategy"
FORMAT_VERSION = 2
# The first version had a weight and parameters per source, before the adapters: a file of it is still read (R4.1.1).
VERSION_BEFORE_THE_ADAPTERS = 1
# The source and the adapter each source of the first version became: the correspondence of the migration of the flows,
# which this adapter cannot import (ADR migrazione-delle-fonti-al-modello-ad-adapter, ADR fonti-con-adapter-dichiarati).
SOURCE_AND_ADAPTER = {
    "indicatori": ("indicatori", "Hyperliquid"),
    "pivot": ("pivot", "Hyperliquid"),
    "forecast": ("forecast", "Prophet"),
    "sentiment-alternative-me": ("sentiment", "alternative.me"),
    "sentiment-coinmarketcap": ("sentiment", "CoinMarketCap"),
    "notizie": ("notizie", "RSS"),
}
FILE_EXTENSION = ".json"
# What every client reads in the plain file name; the full name travels encoded beside it (RFC 6266).
UNSAFE_IN_PLAIN_NAME = re.compile(r"[^A-Za-z0-9 ._-]")


class StrategyFormatNotSupportedError(AutotradingError):
    """A file that is not a strategy of the platform, or of a version of the format it does not read (ADR 0140)."""

    def __init__(self, format_name: str, version: int) -> None:
        super().__init__(f"formato del file non supportato: {format_name} versione {version}")
        self.format_name = format_name
        self.version = version

    @property
    def details(self) -> Mapping[str, object]:
        return {"format": self.format_name, "format_version": self.version}


class StrategyModel(BaseModel):
    name: str = ""
    # Numbers travel as strings, so no precision is lost on the way (ADR 0018).
    parameters: dict[str, Decimal | str] = Field(default_factory=dict)


class StrategyAdapter(BaseModel):
    name: str
    weight: int | None = None
    parameters: dict[str, ParameterBody] = Field(default_factory=dict)


class StrategySource(BaseModel):
    """A source with the adapters the strategy chose (R4.1.1)."""

    name: str
    adapters: list[StrategyAdapter]


class StrategySourceBeforeTheAdapters(BaseModel):
    """A source of a file of the first version: its weight and parameters pass to the adapter it became."""

    name: str
    weight: int | None = None
    parameters: dict[str, int] = Field(default_factory=dict)


class StrategyRiskLimits(BaseModel):
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    # Null or missing: no overall limit on the sum of the open positions (R3.2.1).
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None


class StrategyBody(BaseModel):
    """What a flow does, without account, capital, assets, keys or cycles (R2.5.2).

    A missing model or limit arrives empty, so the domain answers with the reason.
    """

    cycle_minutes: int | None = None
    model: StrategyModel | None = None
    sources: list[StrategySource | StrategySourceBeforeTheAdapters] = Field(default_factory=list)
    instructions: str = ""
    risk_limits: StrategyRiskLimits = Field(default_factory=StrategyRiskLimits)
    bring_to_minimum: bool = False
    # Null follows the default system prompt of the platform (R1.4.8).
    system_prompt: str | None = None
    # Null or missing: no maximum of failed cycles in a row (R3.2.4).
    max_consecutive_failures: int | None = None
    # Null or missing: no maximum loss; missing resume: by hand (R3.2.2).
    max_daily_loss_percent: Decimal | None = None
    max_drawdown_percent: Decimal | None = None
    openings_resume: OpeningsResume = OpeningsResume.MANUAL
    # Missing in the files written before them: a stop loss of 5% and no take profit (R3.1.2).
    default_stop_loss_percent: Decimal | None = None
    default_take_profit_percent: Decimal | None = None
    # Missing in the files written before it: no minimum confidence (R3.1.4).
    minimum_confidence: int | None = None


class StrategyDocument(BaseModel):
    """The strategy file: its format and version, so a file of another kind or of a later version is recognized."""

    format: str
    format_version: int
    strategy: StrategyBody

    @classmethod
    def of(cls, strategy: FlowStrategy) -> StrategyDocument:
        limits = strategy.risk_limits
        return cls(
            format=FORMAT,
            format_version=FORMAT_VERSION,
            strategy=StrategyBody(
                cycle_minutes=strategy.cycle_interval.minutes,
                model=StrategyModel(
                    name=strategy.model.name,
                    parameters={key: str(value) for key, value in strategy.model.parameters.items()},
                ),
                sources=[
                    StrategySource(
                        name=source.name,
                        adapters=[
                            StrategyAdapter(
                                name=adapter.name, weight=adapter.weight, parameters=parameters_body(adapter.parameters)
                            )
                            for adapter in source.adapters
                        ],
                    )
                    for source in strategy.sources
                ],
                instructions=strategy.instructions,
                risk_limits=StrategyRiskLimits(
                    max_leverage=limits.max_leverage,
                    max_margin_exposure_percent=limits.max_margin_exposure_percent,
                    max_value_exposure_percent=limits.max_value_exposure_percent,
                    max_total_margin_exposure_percent=limits.max_total_margin_exposure_percent,
                    max_total_value_exposure_percent=limits.max_total_value_exposure_percent,
                ),
                bring_to_minimum=strategy.bring_to_minimum,
                system_prompt=strategy.system_prompt,
                max_consecutive_failures=strategy.max_consecutive_failures,
                max_daily_loss_percent=strategy.max_daily_loss_percent,
                max_drawdown_percent=strategy.max_drawdown_percent,
                openings_resume=strategy.openings_resume,
                default_stop_loss_percent=strategy.protection_defaults.stop_loss_percent,
                default_take_profit_percent=strategy.protection_defaults.take_profit_percent,
                minimum_confidence=None if strategy.minimum_confidence is None else strategy.minimum_confidence.value,
            ),
        )

    def command(self, name: str) -> ImportFlowStrategyCommand:
        self._require_supported()
        strategy, limits = self.strategy, self.strategy.risk_limits
        model = strategy.model
        return ImportFlowStrategyCommand(
            name=name,
            model=None if model is None else model.name,
            max_leverage=limits.max_leverage,
            max_margin_exposure_percent=limits.max_margin_exposure_percent,
            max_value_exposure_percent=limits.max_value_exposure_percent,
            max_total_margin_exposure_percent=limits.max_total_margin_exposure_percent,
            max_total_value_exposure_percent=limits.max_total_value_exposure_percent,
            model_parameters={} if model is None else model.parameters,
            sources=_source_requests(strategy.sources),
            instructions=strategy.instructions,
            cycle_minutes=strategy.cycle_minutes,
            bring_to_minimum=strategy.bring_to_minimum,
            system_prompt=strategy.system_prompt,
            max_consecutive_failures=strategy.max_consecutive_failures,
            max_daily_loss_percent=strategy.max_daily_loss_percent,
            max_drawdown_percent=strategy.max_drawdown_percent,
            openings_resume=strategy.openings_resume,
            default_stop_loss_percent=strategy.default_stop_loss_percent,
            default_take_profit_percent=strategy.default_take_profit_percent,
            minimum_confidence=strategy.minimum_confidence,
        )

    def _require_supported(self) -> None:
        if self.format != FORMAT or self.format_version not in {VERSION_BEFORE_THE_ADAPTERS, FORMAT_VERSION}:
            raise StrategyFormatNotSupportedError(self.format, self.format_version)


def _source_requests(
    sources: list[StrategySource | StrategySourceBeforeTheAdapters],
) -> tuple[SourceRequest, ...]:
    """The sources of the file with their adapters; two sources of the first version that became one are one source
    with both adapters, in their order. A source without adapters reaches the flow, which refuses it with the reason."""
    adapters_of: dict[str, list[AdapterRequest]] = {}
    for source in sources:
        if isinstance(source, StrategySource):
            adapters_of.setdefault(source.name, []).extend(
                AdapterRequest(adapter.name, adapter.weight, parameters_of(adapter.parameters))
                for adapter in source.adapters
            )
            continue
        name, adapter = SOURCE_AND_ADAPTER.get(source.name, (source.name, source.name))
        adapters_of.setdefault(name, []).append(AdapterRequest(adapter, source.weight, source.parameters))
    return tuple(SourceRequest(name, tuple(adapters)) for name, adapters in adapters_of.items())


def attachment_of(flow_name: str) -> str:
    """The Content-Disposition of the file, named after the flow (ADR 0140)."""
    file_name = flow_name + FILE_EXTENSION
    plain = UNSAFE_IN_PLAIN_NAME.sub("_", file_name)
    return f"attachment; filename=\"{plain}\"; filename*=UTF-8''{quote(file_name, safe='')}"
