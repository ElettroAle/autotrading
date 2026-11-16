from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal

from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow_state import ZERO, FlowState

HUNDRED = Decimal(100)
PERCENT_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class FlowReturn:
    """How the flow is doing: the return compounded across the changes of its capital (R2.2.2, R3.4.3, ADR
    rendimento-composto-tra-le-variazioni-di-capitale).

    The chain goes from the initial capital to the current one through the changes, oldest first: a period ends at the
    value of the flow before a change and the next one starts at that value plus or minus the money moved, so an
    increase, a reduction or a cash-out never moves the return when it happens. It is the only computation of the
    return of a flow: state, summary, ranking and context of the agent all read it.
    """

    initial_capital: Decimal
    current_capital: Decimal
    changes: tuple[CapitalChange, ...] = ()

    @classmethod
    def of(cls, state: FlowState) -> FlowReturn:
        """The return of the flow since it started, at its total value now (R1.6.1, ADR 0127).

        The changes recorded without the value of the flow before them cannot be chained: the chain starts at the
        capital allocated after the last of them, so a flow without changes recorded since keeps the return on the
        capital allocated now.
        """
        history = _in_order(state.capital_changes)
        unchained = [index for index, change in enumerate(history) if change.value_before is None]
        if unchained:
            last = unchained[-1]
            return cls(history[last].new, state.total_value, history[last + 1 :])
        initial = history[0].previous if history else state.allocated_capital
        return cls(initial, state.total_value, history)

    @classmethod
    def over(cls, curve: Sequence[EquitySnapshot], changes: Iterable[CapitalChange]) -> FlowReturn:
        """The return between the first and the last equity of a curve, through the changes after its first point and
        up to its last (R2.4.2); a change recorded without the value before is not chained."""
        first, last = curve[0], curve[-1]
        between = tuple(
            change
            for change in _in_order(changes)
            if first.planned_at < change.changed_at <= last.planned_at and change.value_before is not None
        )
        return cls(first.equity, last.equity, between)

    @property
    def percent(self) -> Decimal | None:
        """The return with two decimals; None when a period starts without value, against which no change is
        measured."""
        growth = Decimal(1)
        for start, end in self._periods():
            if start <= ZERO:
                return None
            growth *= end / start
        rounded = ((growth - 1) * HUNDRED).quantize(PERCENT_PLACES)
        # A change that rounds to zero is no loss: it never shows as -0.00.
        return rounded.copy_abs() if rounded == ZERO else rounded

    @property
    def gain(self) -> Decimal:
        """What the flow gained or lost across the periods, without the money the changes moved."""
        return sum((end - start for start, end in self._periods()), ZERO)

    def _periods(self) -> Iterator[tuple[Decimal, Decimal]]:
        start = self.initial_capital
        for change in self.changes:
            before = start if change.value_before is None else change.value_before
            yield start, before
            start = before + change.signed_amount
        yield start, self.current_capital


def _in_order(changes: Iterable[CapitalChange]) -> tuple[CapitalChange, ...]:
    return tuple(sorted(changes, key=lambda change: change.changed_at))
