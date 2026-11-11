from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.errors import ExposureLimitRequiredError, InvalidRiskLimitError, MaxLeverageRequiredError

HUNDRED = Decimal(100)
LEVERAGE = "leva massima"
MARGIN_EXPOSURE = "esposizione massima del margine"
VALUE_EXPOSURE = "esposizione massima del valore"


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """No defaults: the maximum leverage and at least one exposure per operation are the user's choice (R1.1.1)."""

    max_leverage: int | None
    max_margin_exposure_percent: Decimal | None = None
    max_value_exposure_percent: Decimal | None = None

    def __post_init__(self) -> None:
        if self.max_leverage is None:
            raise MaxLeverageRequiredError
        if self.max_margin_exposure_percent is None and self.max_value_exposure_percent is None:
            raise ExposureLimitRequiredError
        if self.max_leverage < 1:
            raise InvalidRiskLimitError(LEVERAGE)
        _require_percent(self.max_margin_exposure_percent, MARGIN_EXPOSURE)
        _require_percent(self.max_value_exposure_percent, VALUE_EXPOSURE)


def _require_percent(percent: Decimal | None, label: str) -> None:
    if percent is not None and not (percent.is_finite() and Decimal(0) < percent <= HUNDRED):
        raise InvalidRiskLimitError(label)
