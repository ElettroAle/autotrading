from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import (
    ExposureLimitRequiredError,
    InvalidRiskLimitError,
    MaxLeverageRequiredError,
    TotalExposureOutOfRangeError,
)
from autotrading.domain.flows.flow_setting import FlowSetting

HUNDRED = Decimal(100)
LOWEST_LEVERAGE = 1
LOWEST_TOTAL_EXPOSURE = Decimal("0.1")
HIGHEST_TOTAL_EXPOSURE = Decimal(1000)
LEVERAGE = "leva massima"
MARGIN_EXPOSURE = "esposizione massima del margine"
VALUE_EXPOSURE = "esposizione massima del valore"
TOTAL_MARGIN_EXPOSURE = "esposizione complessiva massima del margine"
TOTAL_VALUE_EXPOSURE = "esposizione complessiva massima del valore"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """No defaults: the maximum leverage and at least one exposure per operation are the user's choice (R1.1.1).

    The overall exposures, on the sum of the open positions of the flow, are optional (R3.2.1).
    """

    max_leverage: int
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None
    max_total_margin_exposure_percent: Decimal | None = None
    max_total_value_exposure_percent: Decimal | None = None

    @classmethod
    def of(
        cls,
        max_leverage: int | None,
        max_margin_exposure_percent: Decimal | None = None,
        max_value_exposure_percent: Decimal | None = None,
        max_total_margin_exposure_percent: Decimal | None = None,
        max_total_value_exposure_percent: Decimal | None = None,
    ) -> RiskLimits:
        """The limits the user configures, where the maximum leverage may still be missing and is refused."""
        if max_leverage is None:
            raise MaxLeverageRequiredError
        return cls(
            max_leverage,
            max_margin_exposure_percent,
            max_value_exposure_percent,
            max_total_margin_exposure_percent,
            max_total_value_exposure_percent,
        )

    def __post_init__(self) -> None:
        if self.max_margin_exposure_percent is None and self.max_value_exposure_percent is None:
            raise ExposureLimitRequiredError
        if self.max_leverage < LOWEST_LEVERAGE:
            raise InvalidRiskLimitError(LEVERAGE, FlowSetting.MAX_LEVERAGE)
        _require_percent(self.max_margin_exposure_percent, MARGIN_EXPOSURE, FlowSetting.MAX_MARGIN_EXPOSURE)
        _require_percent(self.max_value_exposure_percent, VALUE_EXPOSURE, FlowSetting.MAX_VALUE_EXPOSURE)
        _require_total_percent(self.max_total_margin_exposure_percent, FlowSetting.MAX_TOTAL_MARGIN_EXPOSURE)
        _require_total_percent(self.max_total_value_exposure_percent, FlowSetting.MAX_TOTAL_VALUE_EXPOSURE)


def _require_percent(percent: Decimal | None, label: str, setting: FlowSetting) -> None:
    if percent is not None and not (percent.is_finite() and Decimal(0) < percent <= HUNDRED):
        raise InvalidRiskLimitError(label, setting)


def _require_total_percent(percent: Decimal | None, setting: FlowSetting) -> None:
    if percent is not None and not (percent.is_finite() and LOWEST_TOTAL_EXPOSURE <= percent <= HIGHEST_TOTAL_EXPOSURE):
        raise TotalExposureOutOfRangeError(setting)
