"""R3.4.3: the return of a flow compounded across the changes of its capital, on the use cases of the API and of the
worker with the fake adapters (ADR rendimento-composto-tra-le-variazioni-di-capitale). playwright-bdd draws the change
on the equity curve of the dashboard; here the same scenario proves that the API gives the curve what it marks.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsCommand
from autotrading.application.flows.rank_flows import RankFlowsCommand
from autotrading.application.flows.read_flow_equity import ReadFlowEquityCommand
from autotrading.application.flows.read_flow_results import ReadFlowResultsCommand
from autotrading.domain.flows.capital_history import CapitalHistoryEntry
from autotrading.domain.flows.equity_snapshot import FlowEquity
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_ranking import FlowRanking
from autotrading.domain.flows.flow_results import FlowResults
from autotrading.domain.flows.ledger import FlowTotals
from autotrading.domain.flows.statistics_period import TimeWindow
from autotrading.domain.italian_text import money_text
from tests.support.activity import an_activity
from tests.support.flow_cycles import FlowCycles, at
from tests.support.steps import quoted

scenarios(
    "E3-rischio-capitale-e-qualita/F3.4-capitale/R3.4.3-rendimento-corretto-dopo-incassi-e-variazioni/api/R3.4.3-rendimento-corretto-dopo-incassi-e-variazioni.feature"
)

# The account holds far more than the flow, so an increase always finds free capital (R1.1.7).
ACCOUNT_BALANCE = Decimal(10000)
STARTED = "10:00"
NEXT_CYCLE = "10:15"


def number(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


@dataclass
class Returns:
    """One flow of a user, read by the API and run by the worker on the same fakes; without positions the state the
    API reads and the one the cycle reads are the same."""

    flow_cycles: FlowCycles
    user: str = ""
    name: str = ""
    moved_at: datetime | None = None
    ranking: tuple[FlowRanking, ...] = ()
    curve: FlowEquity | None = None
    curve_changes: tuple[CapitalHistoryEntry, ...] = ()
    currency: str = ""

    @property
    def flow(self) -> Flow:
        return self.flow_cycles.flow(self.name)

    def start(self, user: str, name: str, capital: Decimal) -> None:
        self.user, self.name = user, name
        self.flow_cycles.add_flow(user, name, started=STARTED)
        self.flow_cycles.reconfigure(name, lambda configuration: replace(configuration, allocated_capital=capital))
        platform = self.flow_cycles.platform
        platform.flows.save_version(self.flow)
        platform.account_activity.activities[self.flow.assigned_account_id] = an_activity(
            balance=ACCOUNT_BALANCE, available_margin=ACCOUNT_BALANCE
        )
        # The first cycle runs when the flow starts: its equity opens the curve.
        self.flow_cycles.run(name, STARTED)

    def results(self) -> FlowResults:
        command = ReadFlowResultsCommand(self.flow.id.value)
        return self.flow_cycles.platform.use_cases_of(self.user).read_flow_results.execute(command)

    def worth(self, value: Decimal) -> None:
        """The flow worth the value without positions: what it gained is the realized PnL of its ledger."""
        ledger = self.flow_cycles.platform.ledger
        totals = ledger.totals.get(self.flow.id) or FlowTotals(self.flow.id)
        gained = value - self.results().state.total_value
        ledger.totals[self.flow.id] = replace(totals, realized_pnl=totals.realized_pnl + gained)

    def act(self) -> None:
        """The user acts a few minutes after the last cycle and before the next one."""
        self.moved_at = self.flow_cycles.clock.now() + timedelta(minutes=5)
        self.flow_cycles.platform.now = self.moved_at

    def cash_out(self) -> Decimal:
        self.act()
        platform = self.flow_cycles.platform
        command = CashOutProfitsCommand(self.flow.id, platform.user_id_of(self.user), None)
        outcome = platform.use_cases_of(self.user).cash_out_profits.execute(command)
        assert outcome.freed is not None, outcome.left_open
        return outcome.freed

    def change_capital(self, amount: Decimal) -> None:
        self.act()
        platform = self.flow_cycles.platform
        capital = self.flow.configuration.assigned_capital + amount
        command = ChangeAllocatedCapitalCommand(self.flow.id, capital, platform.user_id_of(self.user))
        platform.use_cases_of(self.user).change_allocated_capital.execute(command)

    def shown_returns(self) -> set[Decimal | None]:
        """The return as the list of the flows and the summary of the flow show it (R2.2.2, R6.4.2)."""
        use_cases = self.flow_cycles.platform.use_cases_of(self.user)
        overviews = use_cases.list_flow_overviews.execute(ListFlowOverviewsCommand())
        (overview,) = [each for each in overviews if each.summary.name == self.name]
        assert overview.capital is not None
        return {overview.capital.percent, self.results().total_gain_percent}


@pytest.fixture
def returns() -> Returns:
    flow_cycles = FlowCycles()
    # The equity the worker records is the one the API reads.
    flow_cycles.equity_snapshots = flow_cycles.platform.equity_snapshots
    return Returns(flow_cycles)


@given(quoted('che "{user}" ha il flusso "{name}" avviato con capitale allocato {capital} USDC'))
def started_flow(returns: Returns, user: str, name: str, capital: str) -> None:
    returns.start(user, name, number(capital))


@given(quoted('che il valore di "{name}" è {value} USDC senza posizioni aperte'))
def worth_without_positions(returns: Returns, name: str, value: str) -> None:
    assert name == returns.name
    returns.worth(number(value))
    assert returns.results().state.positions == ()


@given(quoted('che il valore di "{name}" è {value} USDC'))
def worth(returns: Returns, name: str, value: str) -> None:
    assert name == returns.name
    returns.worth(number(value))


@given(quoted('che "{user}" ha incassato {amount} USDC da "{name}" quando valeva {value} USDC'))
def cashed_out_at(returns: Returns, user: str, amount: str, name: str, value: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.worth(number(value))
    assert returns.cash_out() == number(amount)


@given(
    quoted(
        'che "{user}" ha incassato {amount} USDC da "{name}" quando valeva {value} USDC e il valore di "{again}" è '
        "ora {now} USDC"
    )
)
def cashed_out_and_worth(  # noqa: PLR0917 - one argument per value of the step
    returns: Returns, user: str, amount: str, name: str, value: str, again: str, now: str
) -> None:
    assert (user, name, again) == (returns.user, returns.name, returns.name)
    returns.worth(number(value))
    assert returns.cash_out() == number(amount)
    returns.worth(number(now))


@given(quoted('che "{user}" ha incassato {amount} USDC da "{name}"'))
def cashed_out(returns: Returns, user: str, amount: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.worth(returns.flow.configuration.assigned_capital + number(amount))
    assert returns.cash_out() == number(amount)


@given(quoted('che "{user}" ha aumentato di {amount} USDC il capitale di "{name}" quando valeva {value} USDC'))
def increased_at(returns: Returns, user: str, amount: str, name: str, value: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.worth(number(value))
    returns.change_capital(number(amount))


@when(quoted('"{user}" incassa i profitti di "{name}"'))
def cash_out(returns: Returns, user: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.cash_out()


@when(quoted('"{user}" aumenta di {amount} USDC il capitale allocato di "{name}"'))
def increase(returns: Returns, user: str, amount: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.change_capital(number(amount))


@when(quoted('"{user}" riduce di {amount} USDC il capitale allocato di "{name}"'))
def reduce(returns: Returns, user: str, amount: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.change_capital(-number(amount))


@when(quoted('il valore di "{name}" passa da {before} a {after} USDC'))
def value_moves(returns: Returns, name: str, before: str, after: str) -> None:
    assert name == returns.name
    assert returns.results().state.total_value == number(before)
    returns.worth(number(after))


@when(quoted('"{user}" apre la classifica dei flussi e parte un ciclo di "{name}"'))
def ranking_and_cycle(returns: Returns, user: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    # The cycle records the equity of now, the last point the ranking reads: the user reads it from then on.
    returns.flow_cycles.run(name, NEXT_CYCLE)
    returns.flow_cycles.platform.now = returns.flow_cycles.clock.now()
    use_cases = returns.flow_cycles.platform.use_cases_of(user)
    returns.ranking = use_cases.rank_flows.execute(RankFlowsCommand())


@when(quoted('"{user}" apre l\'equity curve di "{name}"'))
def open_curve(returns: Returns, user: str, name: str) -> None:
    assert (user, name) == (returns.user, returns.name)
    returns.flow_cycles.run(name, NEXT_CYCLE)
    returns.flow_cycles.platform.now = returns.flow_cycles.clock.now()
    use_cases = returns.flow_cycles.platform.use_cases_of(user)
    returns.curve = use_cases.read_flow_equity.execute(ReadFlowEquityCommand(returns.flow.id.value))
    instants = [snapshot.planned_at for snapshot in returns.curve.snapshots]
    window = TimeWindow(min(instants), max(instants) + timedelta(seconds=1))
    page = use_cases.list_capital_changes.execute(ListCapitalChangesCommand(returns.flow.id, window=window))
    returns.curve_changes, returns.currency = page.entries, page.currency


@then(quoted('il rendimento di "{name}" è {percent}%'))
def flow_return(returns: Returns, name: str, percent: str) -> None:
    assert name == returns.name
    assert returns.shown_returns() == {number(percent)}


@then(quoted('il PnL di "{name}" è {pnl} USDC'))
def flow_pnl(returns: Returns, name: str, pnl: str) -> None:
    assert name == returns.name
    assert returns.results().total_gain == number(pnl)


@then(quoted('la classifica mostra per "{name}" il rendimento {percent}%'))
def ranking_return(returns: Returns, name: str, percent: str) -> None:
    (row,) = [row for row in returns.ranking if row.flow_name == name]
    assert row.return_percent == number(percent)


@then(quoted("lo stato del flusso inviato all'agente riporta il rendimento {percent}%"))
def agent_return(returns: Returns, percent: str) -> None:
    state = returns.flow_cycles.context()["stato_del_flusso"]
    assert isinstance(state, dict)
    assert Decimal(str(state["rendimento_dall_avvio_percento"])) == number(percent)


@then(quoted("la curva segna sull'istante dell'incasso \"{label}\""))
def change_on_curve(returns: Returns, label: str) -> None:
    marks = [
        (entry.occurred_at, f"{entry.reason}, {money_text(entry.amount)} {returns.currency}")
        for entry in returns.curve_changes
    ]
    assert marks == [(returns.moved_at, label)]
    assert at(STARTED) < marks[0][0] < at(NEXT_CYCLE)
