import re
from collections.abc import Mapping
from decimal import Decimal
from urllib.parse import quote

from pydantic import BaseModel, Field

from autotrading.application.flows.create_flow import SourceRequest
from autotrading.application.flows.import_flow_strategy import ImportFlowStrategyCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow_strategy import FlowStrategy

FORMAT = "autotrading-strategy"
FORMAT_VERSION = 1
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


class StrategySource(BaseModel):
    name: str
    weight: int | None = None
    parameters: dict[str, int] = Field(default_factory=dict)


class StrategyRiskLimits(BaseModel):
    max_leverage: int | None = None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None


class StrategyBody(BaseModel):
    """What a flow does, without account, capital, assets, keys or cycles (R2.5.2).

    A missing model or limit arrives empty, so the domain answers with the reason.
    """

    cycle_minutes: int | None = None
    model: StrategyModel | None = None
    sources: list[StrategySource] = Field(default_factory=list)
    instructions: str = ""
    risk_limits: StrategyRiskLimits = Field(default_factory=StrategyRiskLimits)
    bring_to_minimum: bool = False


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
                    StrategySource(name=source.name, weight=source.weight, parameters=dict(source.parameters))
                    for source in strategy.sources
                ],
                instructions=strategy.instructions,
                risk_limits=StrategyRiskLimits(
                    max_leverage=limits.max_leverage,
                    max_margin_exposure_percent=limits.max_margin_exposure_percent,
                    max_value_exposure_percent=limits.max_value_exposure_percent,
                ),
                bring_to_minimum=strategy.bring_to_minimum,
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
            model_parameters={} if model is None else model.parameters,
            sources=tuple(SourceRequest(source.name, source.weight, source.parameters) for source in strategy.sources),
            instructions=strategy.instructions,
            cycle_minutes=strategy.cycle_minutes,
            bring_to_minimum=strategy.bring_to_minimum,
        )

    def _require_supported(self) -> None:
        if (self.format, self.format_version) != (FORMAT, FORMAT_VERSION):
            raise StrategyFormatNotSupportedError(self.format, self.format_version)


def attachment_of(flow_name: str) -> str:
    """The Content-Disposition of the file, named after the flow (ADR 0140)."""
    file_name = flow_name + FILE_EXTENSION
    plain = UNSAFE_IN_PLAIN_NAME.sub("_", file_name)
    return f"attachment; filename=\"{plain}\"; filename*=UTF-8''{quote(file_name, safe='')}"
