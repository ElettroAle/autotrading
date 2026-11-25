from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_configuration import FlowConfiguration
from autotrading.domain.italian_text import number_text

HUNDRED = Decimal(100)
PERCENT_PLACES = Decimal("0.01")
DAILY = "perdita giornaliera"
DRAWDOWN = "perdita dal picco"


@dataclass(frozen=True, slots=True)
class LossReferences:
    """The recorded equities the losses of a flow are measured from (R3.2.2).

    The daily one is the last equity recorded at 00:00 UTC of the day, or at a later resume of the openings that day,
    or before, else the first after it (Bug 775); the peak is the highest recorded since the first start or the last
    resume of the openings. Either is missing without recorded equity.
    """

    daily: EquitySnapshot | None
    peak: EquitySnapshot | None


NO_REFERENCES = LossReferences(None, None)


def at_capital(snapshot: EquitySnapshot, capital: Decimal, cashed_profit: Decimal) -> Decimal:
    """The recorded equity brought to the capital allocated now and to the profits cashed out until now: a change of
    capital and a cash-out are neither a loss nor a gain, so they move the reference by the same amount (R3.2.2, ADR
    perdita-massima-al-netto-degli-incassi).
    """
    cashed_since = cashed_profit - snapshot.cashed_profit
    return snapshot.equity - snapshot.allocated_capital + capital - cashed_since


@dataclass(frozen=True, slots=True)
class LossGuard:
    """The losses of a flow against its thresholds: the reason the openings are suspended, if one is passed (R3.2.2).

    The value is the total value of the flow read now (R1.6.1); the profits cashed out are those of the flow until now
    (R3.4.1).
    """

    value: Decimal
    daily_reference: Decimal | None
    peak: Decimal
    max_daily_loss_percent: Decimal | None
    max_drawdown_percent: Decimal | None

    @classmethod
    def of(
        cls, configuration: FlowConfiguration, value: Decimal, references: LossReferences, cashed_profit: Decimal
    ) -> LossGuard:
        capital = configuration.assigned_capital
        daily = None if references.daily is None else at_capital(references.daily, capital, cashed_profit)
        peak = value if references.peak is None else max(at_capital(references.peak, capital, cashed_profit), value)
        return cls(value, daily, peak, configuration.max_daily_loss_percent, configuration.max_drawdown_percent)

    def breach(self) -> str | None:
        """The first threshold passed, the daily one before the one from the peak."""
        daily = _beyond(DAILY, self.value, self.daily_reference, self.max_daily_loss_percent)
        if daily is not None:
            return daily
        return _beyond(DRAWDOWN, self.value, self.peak, self.max_drawdown_percent)


def _beyond(loss: str, value: Decimal, reference: Decimal | None, threshold: Decimal | None) -> str | None:
    if threshold is None or reference is None or reference <= 0:
        return None
    percent = ((reference - value) / reference * HUNDRED).quantize(PERCENT_PLACES)
    if percent <= threshold:
        return None
    return f"{loss} {number_text(percent)}% oltre il {number_text(threshold)}%"
