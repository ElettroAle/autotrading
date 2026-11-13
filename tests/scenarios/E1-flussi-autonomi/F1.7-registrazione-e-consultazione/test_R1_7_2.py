from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.list_closed_positions import ListClosedPositionsCommand
from autotrading.application.flows.reconcile_account import ReconcileAccountCommand, ReconcileAccountUseCase
from autotrading.application.flows.record_account_executions import RecordAccountExecutionsUseCase
from autotrading.application.flows.record_outside_closing import RecordOutsideClosingUseCase
from autotrading.application.flows.remove_account_with_flows import RemoveAccountWithFlowsCommand
from autotrading.application.flows.stop_flow import StopFlowCommand
from autotrading.application.notifications.notify_position_closed import NotifyPositionClosedUseCase
from autotrading.application.orders.close_position import ClosePositionCommand
from autotrading.domain.flows.account_reconciliation import AccountReading
from autotrading.domain.flows.closed_position import ClosedPosition, CloseReason, PositionEnd
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.trade_intent import TradeSide
from tests.fakes.closed_position_repository import InMemoryClosedPositionRepositoryAdapter
from tests.fakes.flow_openings import InMemoryFlowOpeningsAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.fakes.reconciliation_repository import InMemoryReconciliationRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, an_activity
from tests.support.flows import ACCOUNT, a_flow, account_id_of
from tests.support.lifecycle_steps import hold_position
from tests.support.orders import a_flow_order
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.2-storico-delle-posizioni-chiuse.feature")

DAY = datetime(2026, 11, 12, tzinfo=UTC)
# The flow order opens about 20 USDC of BTC at leverage 2: a liquidation loses about its margin of 10 USDC.
LIQUIDATION_LOSS = Decimal(-9)


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


def at(text: str) -> datetime:
    hours, minutes = (int(part) for part in text.split(":"))
    return DAY.replace(hour=hours, minute=minutes)


@dataclass(frozen=True)
class Opening:
    asset: str = "BTC"
    side: TradeSide = TradeSide.LONG
    leverage: int = 2
    margin: Decimal = Decimal(50)
    price: Decimal = Decimal(100)
    at: datetime = DAY


@dataclass
class History:
    platform: Platform = field(default_factory=Platform)
    flows: dict[str, Flow] = field(default_factory=dict)
    owners: dict[str, str] = field(default_factory=dict)
    opening: Opening = field(default_factory=Opening)
    consulted: list[ClosedPosition] = field(default_factory=list)

    def close(self, flow: str, reason: CloseReason, closing: PositionEnd, fees: Decimal = Decimal(0)) -> None:
        owner, opening = self.flows[flow], self.opening
        self.platform.closed_positions.positions.append(
            ClosedPosition(
                tenant_id=owner.tenant_id,
                flow_id=owner.id,
                asset=opening.asset,
                side=opening.side,
                leverage=opening.leverage,
                margin=opening.margin,
                opening=PositionEnd(opening.price, opening.at),
                closing=closing,
                fees=fees,
                reason=reason,
            )
        )

    def operating_with_open_position(self, flow: str) -> UUID:
        """The flow active on an account of its owner, holding the position its own executed order opened."""
        owner = self.owners[flow]
        account_id = account_id_of(self.platform, owner)
        operating = replace(self.flows[flow], account_id=account_id, status=FlowStatus.ACTIVE)
        self.platform.flows.flows[self.platform.flows.flows.index(self.flows[flow])] = operating
        self.flows[flow] = operating
        self.platform.orders_of(operating.tenant_id).add(a_flow_order(account_id, operating.id.value))
        hold_position(self.platform, owner, ACCOUNT, "BTC")
        return account_id

    def stop(self, flow: str) -> None:
        owner = self.owners[flow]
        self.operating_with_open_position(flow)
        command = StopFlowCommand(self.flows[flow].id, self.platform.user_id_of(owner))
        self.platform.use_cases_of(owner).stop_flow.execute(command)

    def remove_account(self, flow: str) -> None:
        owner = self.owners[flow]
        account_id = self.operating_with_open_position(flow)
        command = RemoveAccountWithFlowsCommand(account_id, self.platform.user_id_of(owner), confirmed=True)
        self.platform.use_cases_of(owner).remove_account_with_flows.execute(command)

    def close_by_hand(self, flow: str) -> None:
        owner = self.owners[flow]
        account_id = self.operating_with_open_position(flow)
        command = ClosePositionCommand(account_id, "BTC", self.platform.user_id_of(owner))
        self.platform.use_cases_of(owner).close_position.execute(command)

    def liquidate(self, flow: str) -> None:
        """The exchange liquidates the position: the reconciliation of the next cycle finds it gone (R1.6.2)."""
        account_id = self.operating_with_open_position(flow)
        operating = self.flows[flow]
        self.platform.account_activity.activities[account_id] = an_activity()
        self.platform.account_activity.executions[account_id] = [
            a_fill("BTC", None, realized_pnl=LIQUIDATION_LOSS, liquidation=True)
        ]
        readings = InMemoryReconciliationRepositoryAdapter()
        readings.save_reading(
            AccountReading(account_id, READ_AT - timedelta(minutes=5), {operating.id: frozenset({"BTC"})})
        )
        flows = InMemoryFlowRepositoryAdapter(self.platform.flows, operating.tenant_id)
        notify = self.platform.worker_for(operating.tenant_id).notify
        history = RecordOutsideClosingUseCase(
            flows,
            InMemoryFlowOpeningsAdapter(self.platform.orders_of(operating.tenant_id)),
            InMemoryClosedPositionRepositoryAdapter(self.platform.closed_positions, operating.tenant_id),
            NotifyPositionClosedUseCase(notify, "USDC"),
        )
        record = RecordAccountExecutionsUseCase(
            flows, self.platform.account_activity, self.platform.platform_orders, self.platform.ledger
        )
        reconciliation = ReconcileAccountUseCase(flows, self.platform.account_activity, readings, history, record)
        reconciliation.execute(ReconcileAccountCommand(operating.id))

    def position(self) -> ClosedPosition:
        assert len(self.consulted) == 1, self.consulted
        return self.consulted[0]


@pytest.fixture
def history() -> History:
    return History()


@given(quoted('che "{user}" ha il flusso "{flow}"'))
def flow_of_user(history: History, user: str, flow: str) -> None:
    created = a_flow(history.platform.tenant_of(user), name=flow)
    history.platform.flows.flows.append(created)
    history.flows[flow] = created
    history.owners[flow] = user


@given(
    parsers.re(
        r'^che il flusso "(?P<flow>[^"]+)" ha aperto alle (?P<opened>\d\d:\d\d) una posizione (?P<side>long|short) su '
        r'"(?P<asset>[^"]+)" con leva (?P<leverage>\d+) e margine (?P<margin>[\d,]+) USDC al prezzo (?P<price>[\d,]+)$'
    )
)
def opened_position(
    history: History, *, flow: str, opened: str, side: str, asset: str, leverage: str, margin: str, price: str
) -> None:
    assert flow in history.flows
    history.opening = Opening(asset, TradeSide(side), int(leverage), amount(margin), amount(price), at(opened))


@given(
    parsers.re(
        r"^che l'agente l'ha chiusa alle (?P<closed>\d\d:\d\d) al prezzo (?P<price>[\d,]+) con commissioni totali "
        r"(?P<fees>[\d,]+) USDC$"
    )
)
def agent_closed(history: History, closed: str, price: str, fees: str) -> None:
    (flow,) = history.flows
    history.close(flow, CloseReason.AGENT, PositionEnd(amount(price), at(closed)), amount(fees))


@given(parsers.re(r'^che una posizione del flusso "(?P<flow>[^"]+)" è stata chiusa per (?P<event>.+)$'))
def closed_for_event(history: History, flow: str, event: str) -> None:
    # The stop and the removal of the account close the position through the platform itself (R1.1.5, R1.1.8).
    if event == "stop del flusso":
        history.stop(flow)
        return
    if event == "rimozione del conto":
        history.remove_account(flow)
        return
    if event == "chiusura manuale dell'utente":
        history.close_by_hand(flow)
        return
    assert event == "liquidazione sull'exchange", event
    history.liquidate(flow)


@given(parsers.re(r'^che il flusso "(?P<flow>[^"]+)" ha chiuso posizioni alle (?P<instants>.+)$'))
def closed_at_instants(history: History, flow: str, instants: str) -> None:
    for instant in instants.replace(" e alle ", ", alle ").split(", alle "):
        history.close(flow, CloseReason.AGENT, PositionEnd(Decimal(100), at(instant.strip())))


@when(quoted('"{user}" consulta lo storico delle posizioni chiuse del flusso "{flow}"'))
def consult_history(history: History, user: str, flow: str) -> None:
    command = ListClosedPositionsCommand(history.flows[flow].id.value)
    history.consulted = history.platform.use_cases_of(user).list_closed_positions.execute(command)


@then(
    parsers.re(
        r'^lo storico contiene la posizione (?P<side>long|short) su "(?P<asset>[^"]+)" con leva (?P<leverage>\d+), '
        r"apertura (?P<opening>[\d,]+) e chiusura (?P<closing>[\d,]+)$"
    )
)
def history_contains(history: History, *, side: str, asset: str, leverage: str, opening: str, closing: str) -> None:
    position = history.position()
    assert (position.side.value, position.asset, position.leverage) == (side, asset, int(leverage))
    assert (position.opening.price, position.closing.price) == (amount(opening), amount(closing))


@then(parsers.re(r"^la posizione ha durata (?P<hours>\d+) ore e (?P<minutes>\d+) minuti$"))
def position_duration(history: History, hours: str, minutes: str) -> None:
    assert history.position().duration == timedelta(hours=int(hours), minutes=int(minutes))


@then(
    parsers.re(
        r"^la posizione ha PnL (?P<pnl>[\d,]+) USDC pari al (?P<percent>[\d,]+)% del margine e commissioni "
        r"(?P<fees>[\d,]+) USDC$"
    )
)
def position_result(history: History, pnl: str, percent: str, fees: str) -> None:
    position = history.position()
    assert position.pnl == amount(pnl)
    assert position.pnl_percent_of_margin == amount(percent)
    assert position.fees == amount(fees)


@then(quoted('la posizione ha motivo di chiusura "{reason}"'))
def position_reason(history: History, reason: str) -> None:
    assert history.position().reason.value == reason


@then(parsers.re(r"^lo storico elenca le posizioni chiuse alle (?P<instants>.+)$"))
def history_order(history: History, instants: str) -> None:
    expected = [at(instant.strip()) for instant in instants.replace(" e ", ", ").split(", ")]
    assert [position.closing.at for position in history.consulted] == expected
