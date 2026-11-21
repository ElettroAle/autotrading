"""R3.4.2: the history of the changes of capital of a flow and of an account, on the use cases of the API with the fake
adapters (ADR storico-delle-variazioni-di-capitale). playwright-bdd runs the table of the dashboard on its build; here
the same scenario proves that the API gives the table what it shows.
"""

from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.cash_out_profits import CashOutProfitsCommand
from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.list_account_capital_changes import ListAccountCapitalChangesCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.domain.flows.capital_history import AccountTransfer, CapitalHistoryPage, TransferDirection
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.statistics_period import TimeWindow
from tests.support.activity import a_fill, an_activity
from tests.support.flows import a_configuration, a_flow, account_id_of
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.4-capitale/R3.4.2-storico-delle-variazioni-di-capitale.feature")

BALANCE = Decimal(10000)
DECLARED_AT = datetime(2026, 11, 9, 8, 30, tzinfo=UTC)
ASSETS = (("BTC",), ("ETH",), ("SOL",))


@dataclass
class History:
    platform: Platform
    user: str = ""
    account_id: UUID | None = None
    flows: dict[str, Flow] = field(default_factory=dict)
    page: CapitalHistoryPage | None = None

    def account(self) -> UUID:
        assert self.account_id is not None
        return self.account_id

    def flow(self, name: str) -> Flow:
        return next(flow for flow in self.platform.flows.of(self.flows[name].tenant_id) if flow.name.value == name)

    def add_flow(self, user: str, account: str, name: str, capital: Decimal) -> Flow:
        account_id = account_id_of(self.platform, user, account, BALANCE)
        configuration = a_configuration(assets=ASSETS[len(self.flows) % len(ASSETS)], allocated_capital=capital)
        flow = a_flow(self.platform.tenant_of(user), name=name, account_id=account_id, configuration=configuration)
        self.platform.flows.flows.append(flow)
        self.platform.flows.save_version(flow)
        self.flows[name] = flow
        return flow

    def change_capital(self, user: str, name: str, capital: Decimal) -> None:
        self.platform.now += timedelta(minutes=1)
        command = ChangeAllocatedCapitalCommand(self.flow(name).id, capital, self.platform.user_id_of(user))
        self.platform.use_cases_of(user).change_allocated_capital.execute(command)

    def read_flow(self, name: str, window: TimeWindow | None = None) -> CapitalHistoryPage:
        command = ListCapitalChangesCommand(self.flow(name).id, window=window or TimeWindow())
        return self.platform.use_cases_of(self.user).list_capital_changes.execute(command)

    def read_account(self, user: str, account: str) -> None:
        assert self.platform.account_named(user, account).id.value == self.account()
        command = ListAccountCapitalChangesCommand(self.account())
        self.page = self.platform.use_cases_of(user).list_account_capital_changes.execute(command)

    def read(self) -> CapitalHistoryPage:
        assert self.page is not None
        return self.page


@pytest.fixture
def history(platform: Platform) -> History:
    return History(platform)


@pytest.fixture
def platform() -> Platform:
    return Platform()


@given(
    quoted(
        'che "{user}" ha sul conto "{account}" i flussi "{first}" con capitale allocato {first_capital} USDC '
        'e "{second}" con capitale allocato {second_capital} USDC'
    )
)
def two_flows(
    history: History, *, user: str, account: str, first: str, first_capital: str, second: str, second_capital: str
) -> None:
    history.user = user
    history.add_flow(user, account, first, Decimal(first_capital))
    history.add_flow(user, account, second, Decimal(second_capital))
    history.account_id = account_id_of(history.platform, user, account)


@given(quoted('che "{name}" ha valore complessivo {value} USDC senza posizioni aperte'))
def worth_without_positions(history: History, platform: Platform, name: str, value: str) -> None:
    """The flow worth the value through the PnL it realized; the balance of the account holds it beside the capital."""
    flow = history.flow(name)
    realized = Decimal(value) - flow.configuration.assigned_capital
    platform.ledger.add(history.account(), flow.id, a_fill("BTC", None, realized_pnl=realized, size=Decimal(0)))
    reading = platform.account_activity.activities.get(history.account(), an_activity())
    balance = BALANCE + realized
    platform.account_activity.activities[history.account()] = replace(
        reading, balance=balance, available_margin=balance
    )


@given(
    quoted(
        'che "{user}" ha aumentato di {increase} USDC il capitale di "{first}" e ridotto di {reduction} USDC quello di '
        '"{second}"'
    )
)
def increased_and_reduced(
    history: History, *, user: str, increase: str, first: str, reduction: str, second: str
) -> None:
    history.change_capital(user, first, history.flow(first).configuration.assigned_capital + Decimal(increase))
    history.change_capital(user, second, history.flow(second).configuration.assigned_capital - Decimal(reduction))


@given(quoted('che "{user}" ha aumentato di {increase} USDC il capitale di "{name}"'))
def increased(history: History, user: str, increase: str, name: str) -> None:
    history.change_capital(user, name, history.flow(name).configuration.assigned_capital + Decimal(increase))


@given(quoted('che l\'exchange dichiara sul conto "{account}" un {movement} di {amount} USDC'))
def transfer_declared(history: History, platform: Platform, account: str, movement: str, amount: str) -> None:
    assert platform.account_named(history.user, account).id.value == history.account()
    transfer = AccountTransfer(DECLARED_AT, Decimal(amount), TransferDirection(movement))
    platform.account_transfers.declared.setdefault(history.account(), []).append(transfer)


@given(quoted('che "{name}" ha una variazione del {first} e una del {second}'))
def changes_on_days(history: History, platform: Platform, name: str, first: str, second: str) -> None:
    for day, capital in ((first, Decimal(600)), (second, Decimal(700))):
        platform.now = datetime.combine(_day(day), datetime.min.time(), UTC) + timedelta(hours=10)
        command = ChangeAllocatedCapitalCommand(history.flow(name).id, capital, platform.user_id_of(history.user))
        platform.use_cases_of(history.user).change_allocated_capital.execute(command)


@given(quoted('che "{user}" ha cambiato {times} volte il capitale di "{name}", di 1 USDC ogni volta'))
def many_changes(history: History, user: str, times: str, name: str) -> None:
    for _ in range(int(times)):
        history.change_capital(user, name, history.flow(name).configuration.assigned_capital + 1)


@given(quoted('che "{user}" ha una variazione di capitale su un suo flusso'))
def change_of_another_tenant(history: History, user: str) -> None:
    history.add_flow(user, "test-1", "gamma", Decimal(500))
    history.change_capital(user, "gamma", Decimal(600))


@when(quoted('"{user}" porta il capitale allocato di "{name}" a {capital} USDC'))
def change_capital(history: History, user: str, name: str, capital: str) -> None:
    history.change_capital(user, name, Decimal(capital))


@when(quoted('"{user}" incassa i profitti di "{name}"'))
def cash_out(history: History, platform: Platform, user: str, name: str) -> None:
    platform.now += timedelta(minutes=1)
    command = CashOutProfitsCommand(history.flow(name).id, platform.user_id_of(user), None)
    platform.use_cases_of(user).cash_out_profits.execute(command)


@when(quoted('"{user}" consulta lo storico delle variazioni del conto "{account}"'))
def read_account_history(history: History, user: str, account: str) -> None:
    history.read_account(user, account)


@when(quoted('"{user}" consulta lo storico delle variazioni di "{name}" dal {first} al {last}'))
def read_flow_history_in_period(history: History, user: str, name: str, first: str, last: str) -> None:
    assert user == history.user
    history.page = history.read_flow(name, _days(first, last))


@when(quoted('"{user}" consulta la seconda pagina dello storico delle variazioni di "{name}"'))
def read_second_page(history: History, user: str, name: str) -> None:
    command = ListCapitalChangesCommand(history.flow(name).id, page=2)
    history.page = history.platform.use_cases_of(user).list_capital_changes.execute(command)


@when(quoted('"{user}" apre nella dashboard lo storico delle variazioni di "{name}"'))
def open_flow_history(history: History, user: str, name: str) -> None:
    assert user == history.user
    history.page = history.read_flow(name)


@then(
    quoted(
        'lo storico delle variazioni di "{name}" contiene "{reason}" di {amount} USDC, da {previous} a {new} USDC, '
        "con data e ora"
    )
)
def flow_history_contains(
    history: History, platform: Platform, *, name: str, reason: str, amount: str, previous: str, new: str
) -> None:
    rows = [
        (entry.flow_name, entry.reason.value, entry.amount, entry.previous, entry.new, entry.occurred_at)
        for entry in history.read_flow(name).entries
    ]
    assert rows == [(name, reason, Decimal(amount), Decimal(previous), Decimal(new), platform.now)]


@then(quoted('lo storico contiene l\'aumento di "{first}" e la riduzione di "{second}", dalla più recente'))
def account_history_newest_first(history: History, first: str, second: str) -> None:
    rows = [(entry.flow_name, entry.reason.value) for entry in history.read().entries]
    assert rows == [(second, "riduzione"), (first, "aumento")]


@then(quoted('lo storico contiene "{movement}" di {amount} USDC con data e ora dell\'exchange'))
def account_history_transfer(history: History, movement: str, amount: str) -> None:
    rows = [(entry.reason.value, entry.amount, entry.occurred_at, entry.flow_name) for entry in history.read().entries]
    assert rows == [(movement, Decimal(amount), DECLARED_AT, None)]


@then(quoted("lo storico contiene solo la variazione del {day}"))
def only_change_of_day(history: History, day: str) -> None:
    assert [entry.occurred_at.date() for entry in history.read().entries] == [_day(day)]


@then(
    quoted(
        'la tabella mostra data e ora, motivo "{reason}", importo {amount} USDC, capitale prima {previous} USDC '
        "e dopo {new} USDC"
    )
)
def table_row(history: History, platform: Platform, *, reason: str, amount: str, previous: str, new: str) -> None:
    page = history.read()
    rows = [(entry.occurred_at, entry.reason.value, entry.amount, entry.previous, entry.new) for entry in page.entries]
    assert rows == [(platform.now, reason, Decimal(amount), Decimal(previous), Decimal(new))]
    assert page.currency == "USDC"


@then(quoted("la pagina contiene solo la prima variazione, da {previous} a {new} USDC"))
def only_first_change(history: History, previous: str, new: str) -> None:
    page = history.read()
    assert [(entry.previous, entry.new) for entry in page.entries] == [(Decimal(previous), Decimal(new))]
    assert not page.has_next


@then(quoted("la prima pagina contiene le {count} variazioni più recenti, dalla più recente"))
def first_page_newest(history: History, count: str) -> None:
    page = history.read_flow("alfa")
    instants = [entry.occurred_at for entry in page.entries]
    assert len(instants) == int(count)
    assert instants == sorted(instants, reverse=True)
    assert page.entries[0].new == Decimal(551)
    assert page.has_next


@then(quoted('lo storico non contiene la variazione di "{user}"'))
def without_other_tenant(history: History, platform: Platform, user: str) -> None:
    theirs = history.flow("gamma")
    command = ListCapitalChangesCommand(theirs.id)
    assert platform.use_cases_of(user).list_capital_changes.execute(command).total == 1
    assert theirs.id not in {entry.flow_id for entry in history.read().entries}


def _day(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").replace(tzinfo=UTC).date()


def _days(first: str, last: str) -> TimeWindow:
    """The minutes of the days from the first to the last, both whole (ADR periodo-al-minuto)."""
    start = datetime.combine(_day(first), time.min, tzinfo=UTC)
    end = datetime.combine(_day(last), time(23, 59), tzinfo=UTC)
    return TimeWindow.of_minutes(start, end)
