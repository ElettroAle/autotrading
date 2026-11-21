from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.read_flow_statistics import ReadFlowStatisticsCommand
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.capital_change import CapitalChange, CapitalChangeReason
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.equity_snapshot import EquitySnapshot
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_statistics import FlowStatistics
from autotrading.domain.flows.trade_side import TradeSide
from autotrading.domain.tenancy.user_id import UserId
from tests.support.flows import a_flow
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios(
    "E2-dashboard-e-confronto/F2.2-monitoraggio/R2.2.6-statistiche-del-flusso/api/R2.2.6-statistiche-del-flusso.feature"
)

PERIODS = {"tutta la vita": "all", "7 giorni": "7d", "30 giorni": "30d"}
RECENT = timedelta(days=2)
LONG_AGO = timedelta(days=20)


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", ".").replace("+", ""))


def amounts(text: str) -> list[Decimal]:
    return [amount(item) for item in text.replace(" e ", ", ").split(", ")]


@dataclass
class ClosedTrade:
    """A position the flow closed: its net result, its fees and how long ago it was closed."""

    net_pnl: Decimal
    fees: Decimal = Decimal(0)
    age: timedelta = LONG_AGO


@dataclass
class CashOut:
    """Profits the user cashed out of the flow: how much, when, and what the flow was worth just before."""

    amount: Decimal
    age: timedelta
    value_before: Decimal


@dataclass
class FlowHistory:
    trades: list[ClosedTrade] = field(default_factory=list)
    model_cost: Decimal = Decimal(0)
    values: dict[timedelta, Decimal] = field(default_factory=dict)
    cash_outs: list[CashOut] = field(default_factory=list)


@dataclass
class Statistics:
    platform: Platform = field(default_factory=Platform)
    histories: dict[str, FlowHistory] = field(default_factory=dict)
    seen: FlowStatistics | None = None
    user_of_cash_outs: str = ""

    def history_of(self, flow: str) -> FlowHistory:
        return self.histories.setdefault(flow, FlowHistory())

    def open(self, user: str, flow: str, period: str = "all") -> None:
        created = self._flow_of(user, flow)
        command = ReadFlowStatisticsCommand(created.id.value, period)
        self.seen = self.platform.use_cases_of(user).read_flow_statistics.execute(command)

    def statistics(self) -> FlowStatistics:
        assert self.seen is not None
        return self.seen

    def _flow_of(self, user: str, name: str) -> Flow:
        """The flow of the user, with the positions and the model calls the scenario gave it."""
        created = a_flow(self.platform.tenant_of(user), name=name)
        self.platform.flows.flows.append(created)
        history = self.history_of(name)
        for trade in history.trades:
            self.platform.closed_positions.positions.append(self._position(created, trade))
        cost = CallCost(1000, 100, history.model_cost)
        planned_at = self.platform.now - LONG_AGO
        self.platform.cycles.record(CycleRecord(created.id.value, planned_at, CycleOutcome.COMPLETED, cost=cost))
        self._record_values(created, history)
        return created

    def _record_values(self, flow: Flow, history: FlowHistory) -> None:
        """The value every cycle recorded, and the cash-outs of the user with the value of the flow before each."""
        equity = self.platform.equity_snapshots.snapshots
        zero = Decimal(0)
        for age, value in history.values.items():
            planned_at = self.platform.now - age
            snapshot = EquitySnapshot(flow.id.value, planned_at, value, zero, zero, zero, zero)
            equity[flow.tenant_id, flow.id.value, planned_at] = snapshot
        capital = flow.configuration.assigned_capital
        changes = self.platform.flows.capital_changes.setdefault(flow.id, [])
        for cash_out in history.cash_outs:
            changes.append(
                CapitalChange(
                    flow.id,
                    self.platform.now - cash_out.age,
                    capital,
                    capital,
                    UserId(self.user_of_cash_outs),
                    CapitalChangeReason.CASH_OUT,
                    cash_out.amount,
                    value_before=cash_out.value_before,
                    cashed_profit=cash_out.amount,
                )
            )

    def _position(self, flow: Flow, trade: ClosedTrade) -> ClosedPosition:
        closed_at = self.platform.now - trade.age
        return ClosedPosition(
            tenant_id=flow.tenant_id,
            flow_id=flow.id,
            asset="BTC",
            side=TradeSide.LONG,
            leverage=2,
            margin=Decimal(50),
            opening=PositionEnd(Decimal(100), closed_at - timedelta(hours=1)),
            closing=PositionEnd(Decimal(100), closed_at),
            fees=trade.fees,
            reason=CloseReason.AGENT,
            realized_pnl=trade.net_pnl + trade.fees,
        )


@pytest.fixture
def statistics() -> Statistics:
    return Statistics()


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha chiuso \d+ posizioni con PnL netto (?P<results>.+) USDC e commissioni '
        r"totali (?P<fees>[\d,]+) USDC$"
    )
)
def closed_positions(statistics: Statistics, flow: str, results: str, fees: str) -> None:
    nets = amounts(results)
    share = amount(fees) / len(nets)
    statistics.history_of(flow).trades.extend(ClosedTrade(net, share) for net in nets)


@given(parsers.re(r"^che le chiamate al modello del flusso sono costate (?P<cost>[\d,]+) USD$"))
def model_cost(statistics: Statistics, cost: str) -> None:
    (flow,) = statistics.histories
    statistics.history_of(flow).model_cost = amount(cost)


@given(parsers.re(r"^che solo le posizioni con PnL (?P<results>.+) USDC sono state chiuse negli ultimi 7 giorni$"))
def recent_positions(statistics: Statistics, results: str) -> None:
    recent = amounts(results)
    (history,) = statistics.histories.values()
    for trade in history.trades:
        if trade.net_pnl in recent:
            trade.age = RECENT


@given(quoted('che il flusso "{flow}" chiude una quinta posizione con PnL netto {result} USDC'))
def even_position(statistics: Statistics, flow: str, result: str) -> None:
    statistics.history_of(flow).trades.append(ClosedTrade(amount(result), age=RECENT))


@given(quoted('che il flusso "{flow}" non ha posizioni chiuse'))
def no_positions(statistics: Statistics, flow: str) -> None:
    statistics.history_of(flow)


@given(
    quoted('che il flusso "{flow}" valeva {first} USDC {first_days} giorni fa e {second} USDC {second_days} giorni fa')
)
def values_in_the_past(
    statistics: Statistics, *, flow: str, first: str, first_days: str, second: str, second_days: str
) -> None:
    values = statistics.history_of(flow).values
    values[timedelta(days=int(first_days))] = amount(first)
    values[timedelta(days=int(second_days))] = amount(second)


@given(quoted('che "{user}" ha incassato {cashed} USDC da "{flow}" {days} giorni fa, quando valeva {value} USDC'))
def cashed_out(statistics: Statistics, *, user: str, cashed: str, flow: str, days: str, value: str) -> None:
    statistics.user_of_cash_outs = user
    cash_out = CashOut(amount(cashed), timedelta(days=int(days)), amount(value))
    statistics.history_of(flow).cash_outs.append(cash_out)


@given(quoted('che il flusso "{flow}" vale ora {value} USDC'))
def value_now(statistics: Statistics, flow: str, value: str) -> None:
    statistics.history_of(flow).values[timedelta(0)] = amount(value)


@when(quoted('"{user}" apre le statistiche del flusso "{flow}"'))
def open_statistics(statistics: Statistics, user: str, flow: str) -> None:
    statistics.open(user, flow)


@when(quoted('"{user}" sceglie il periodo "{period}"'))
def choose_period(statistics: Statistics, user: str, period: str) -> None:
    (flow,) = statistics.histories
    statistics.open(user, flow, PERIODS[period])


@then(
    parsers.re(
        r"^vede (?P<won>\d+) vinte, (?P<lost>\d+) perse, win rate (?P<rate>[\d,]+)%, PnL medio vincenti "
        r"(?P<winning>[+-][\d,]+) USDC, PnL medio perdenti (?P<losing>[+-][\d,]+) USDC, commissioni (?P<fees>[\d,]+) "
        r"USDC, (?P<operations>\d+) operazioni, costo del modello (?P<cost>[\d,]+) USD$"
    )
)
def sees_every_statistic(
    statistics: Statistics,
    *,
    won: str,
    lost: str,
    rate: str,
    winning: str,
    losing: str,
    fees: str,
    operations: str,
    cost: str,
) -> None:
    seen = statistics.statistics()
    assert (seen.won, seen.lost) == (int(won), int(lost))
    assert seen.win_rate_percent == amount(rate)
    assert (seen.average_winning_pnl, seen.average_losing_pnl) == (amount(winning), amount(losing))
    assert seen.total_fees == amount(fees)
    assert seen.operations == int(operations)
    assert seen.model_cost_usd == amount(cost)


@then(parsers.re(r"^vede (?P<won>\d+) vinta, (?P<lost>\d+) persa e (?P<operations>\d+) operazioni$"))
def sees_the_period(statistics: Statistics, won: str, lost: str, operations: str) -> None:
    seen = statistics.statistics()
    assert (seen.won, seen.lost) == (int(won), int(lost))
    assert seen.operations == int(operations)


@then(
    parsers.re(
        r"^vede (?P<won>\d+) vinte, (?P<lost>\d+) perse, win rate (?P<rate>[\d,]+)% e (?P<operations>\d+) operazioni$"
    )
)
def sees_the_even_position(statistics: Statistics, won: str, lost: str, rate: str, operations: str) -> None:
    seen = statistics.statistics()
    assert (seen.won, seen.lost) == (int(won), int(lost))
    assert seen.win_rate_percent == amount(rate)
    assert seen.operations == int(operations)


@then(parsers.re(r'^vede (?P<operations>\d+) operazioni e win rate "non disponibile"$'))
def sees_no_operations(statistics: Statistics, operations: str) -> None:
    seen = statistics.statistics()
    assert seen.operations == int(operations)
    assert seen.win_rate_percent is None


@then(parsers.re(r"^vede il rendimento (?P<percent>-?[\d,]+)%$"))
def sees_the_return(statistics: Statistics, percent: str) -> None:
    assert statistics.statistics().return_percent == amount(percent)
