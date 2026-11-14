from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import ExposureLimitRequiredError, InvalidRiskLimitError, MaxLeverageRequiredError
from autotrading.domain.flows.flow_setting import FlowSetting

HUNDRED = Decimal(100)
LEVERAGE = "leva massima"
MARGIN_EXPOSURE = "esposizione massima del margine"
VALUE_EXPOSURE = "esposizione massima del valore"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """No defaults: the maximum leverage and at least one exposure per operation are the user's choice (R1.1.1)."""

    max_leverage: int
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None

    @classmethod
    def of(
        cls,
        max_leverage: int | None,
        max_margin_exposure_percent: Decimal | None = None,
        max_value_exposure_percent: Decimal | None = None,
    ) -> RiskLimits:
        """The limits the user configures, where the maximum leverage may still be missing and is refused."""
        if max_leverage is None:
            raise MaxLeverageRequiredError
        return cls(max_leverage, max_margin_exposure_percent, max_value_exposure_percent)

    def __post_init__(self) -> None:
        if self.max_margin_exposure_percent is None and self.max_value_exposure_percent is None:
            raise ExposureLimitRequiredError
        if self.max_leverage < 1:
            raise InvalidRiskLimitError(LEVERAGE, FlowSetting.MAX_LEVERAGE)
        _require_percent(self.max_margin_exposure_percent, MARGIN_EXPOSURE, FlowSetting.MAX_MARGIN_EXPOSURE)
        _require_percent(self.max_value_exposure_percent, VALUE_EXPOSURE, FlowSetting.MAX_VALUE_EXPOSURE)


def _require_percent(percent: Decimal | None, label: str, setting: FlowSetting) -> None:
    if percent is not None and not (percent.is_finite() and Decimal(0) < percent <= HUNDRED):
        raise InvalidRiskLimitError(label, setting)
