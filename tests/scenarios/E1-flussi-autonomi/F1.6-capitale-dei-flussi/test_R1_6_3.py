import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.export_account_operations import (
    ExportAccountOperationsCommand,
    ExportAccountOperationsUseCase,
)
from autotrading.application.flows.export_flow_operations import (
    ExportFlowOperationsCommand,
    ExportFlowOperationsUseCase,
)
from autotrading.application.flows.list_account_operations import (
    ListAccountOperationsCommand,
    ListAccountOperationsUseCase,
)
from autotrading.application.flows.list_flow_operations import ListFlowOperationsCommand, ListFlowOperationsUseCase
from autotrading.domain.flows.operations import AccountScope, Operation, OperationsQuery, OperationsReport
from tests.fakes.flow_operations import InMemoryFlowOperationsAdapter
from tests.fakes.flow_repository import InMemoryFlowRepositoryAdapter
from tests.support.activity import READ_AT, a_fill, a_payment
from tests.support.attribution import TENANT, AttributionBench, amount, step

scenarios("E1-flussi-autonomi/F1.6-capitale-dei-flussi/R1.6.3-registro-delle-operazioni.feature")

NO_FLOW = "nessun flusso"
CLOCK = r"(?P<{}>[0-9]{{2}}:[0-9]{{2}})"
CLOCKS = re.compile(r"[0-9]{2}:[0-9]{2}")
PURCHASES = re.compile(r'su "([^"]+)" alle ([0-9]{2}:[0-9]{2})')
ROWS = re.compile(r'([0-9]{2}:[0-9]{2}) di "([^"]+)"')
TODAY = READ_AT.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass
class Register:
    """What "anna" read of the register: the reports she consulted and the rows she exported."""

    reports: list[OperationsReport] = field(default_factory=list)
    exported: list[Operation] = field(default_factory=list)


@pytest.fixture
def bench() -> AttributionBench:
    return AttributionBench()


@pytest.fixture
def register() -> Register:
    return Register()


def at(clock: str) -> datetime:
    hours, minutes = clock.split(":")
    return TODAY + timedelta(hours=int(hours), minutes=int(minutes))


def clock(name: str) -> str:
    return CLOCK.format(name)


def operations_of(bench: AttributionBench) -> InMemoryFlowOperationsAdapter:
    return InMemoryFlowOperationsAdapter(
        bench.ledger, bench.accounts.values, lambda: {flow.id: flow.name.value for flow in bench.store.flows}
    )


def flows_of(bench: AttributionBench) -> InMemoryFlowRepositoryAdapter:
    return InMemoryFlowRepositoryAdapter(bench.store, TENANT)


def record_flow_fills(
    bench: AttributionBench, flow: str, asset: str, instants: list[datetime], *, realized_pnl: Decimal, fee: Decimal
) -> None:
    owner = bench.flow(flow)
    fills = []
    for number, instant in enumerate(instants):
        order = uuid4()
        bench.orders.add(order, owner.assigned_account_id, owner.id)
        fill_id = f"{flow}-{number}"
        fills.append(a_fill(asset, order, realized_pnl=realized_pnl, fee=fee, executed_at=instant, fill_id=fill_id))
    bench.extend(owner.assigned_account_id, fills=tuple(fills))
    bench.record_executions(owner.assigned_account_id)


def consult_flow(bench: AttributionBench, flow: str, query: OperationsQuery) -> OperationsReport:
    use_case = ListFlowOperationsUseCase(flows_of(bench), operations_of(bench))
    return use_case.execute(ListFlowOperationsCommand(bench.flow(flow).id.value, query))


def export_flow(bench: AttributionBench, flow: str, query: OperationsQuery) -> list[Operation]:
    use_case = ExportFlowOperationsUseCase(flows_of(bench), operations_of(bench))
    return list(use_case.execute(ExportFlowOperationsCommand(bench.flow(flow).id.value, query)))


def owners_of(operations: tuple[Operation, ...] | list[Operation]) -> list[tuple[datetime, str]]:
    return [(operation.occurred_at, operation.flow or NO_FLOW) for operation in operations]


def expected_rows(text: str) -> list[tuple[datetime, str]]:
    return [(at(found), owner) for found, owner in ROWS.findall(text)]


@given(step(r'che "anna" ha il conto "{account}" con i flussi "alfa" \(asset "BTC"\) e "beta" \(asset "ETH"\)'))
def two_flows(bench: AttributionBench, account: str) -> None:
    bench.add_flow(account, "alfa", ("BTC",))
    bench.add_flow(account, "beta", ("ETH",))


@given(
    step(
        r'che il flusso "{flow}" ha esecuzioni con PnL realizzato {a} USDC e commissione {b} USDC su "{asset}"'
        r" (?P<clocks>alle .+)"
    )
)
def fills_at(bench: AttributionBench, flow: str, *, a: str, b: str, asset: str, clocks: str) -> None:
    instants = [at(found) for found in CLOCKS.findall(clocks)]
    record_flow_fills(bench, flow, asset, instants, realized_pnl=amount(a), fee=amount(b))


@given(
    step(r'che il flusso "{flow}" ha (?P<count>\d+) esecuzioni con PnL realizzato {a} USDC su "{asset}", una al minuto')
)
def many_fills(bench: AttributionBench, flow: str, count: str, a: str, asset: str) -> None:
    instants = [at("09:00") + timedelta(minutes=minute) for minute in range(int(count))]
    record_flow_fills(bench, flow, asset, instants, realized_pnl=amount(a), fee=Decimal(0))


@given(step(r'che il flusso "{flow}" ha ricevuto un funding di {a} USDC su "{asset}" alle ' + clock("paid")))
def funding_at(bench: AttributionBench, flow: str, a: str, asset: str, paid: str) -> None:
    account_id = bench.flow(flow).assigned_account_id
    bench.exchange.funding.setdefault(account_id, []).append(a_payment(asset, amount(a), paid_at=at(paid)))
    bench.record_executions(account_id)


@given(step(r'che sul conto "{account}" ci sono acquisti fuori dalla piattaforma (?P<purchases>su .+)'))
def outside_purchases(bench: AttributionBench, account: str, purchases: str) -> None:
    account_id = bench.account(account)
    fills = tuple(
        a_fill(asset, None, executed_at=at(instant), fill_id=f"fuori-{number}")
        for number, (asset, instant) in enumerate(PURCHASES.findall(purchases))
    )
    bench.extend(account_id, fills=fills)
    bench.record_executions(account_id)


@when(step(r'"anna" consulta le operazioni del flusso "{flow}" dalle ' + clock("since") + " alle " + clock("until")))
def consult_period(bench: AttributionBench, register: Register, flow: str, since: str, until: str) -> None:
    register.reports.append(consult_flow(bench, flow, OperationsQuery(since=at(since), until=at(until))))


@when(step(r'"anna" consulta la seconda pagina delle operazioni del flusso "{flow}"'))
def consult_second_page(bench: AttributionBench, register: Register, flow: str) -> None:
    first = consult_flow(bench, flow, OperationsQuery())
    register.reports.append(consult_flow(bench, flow, OperationsQuery(after=first.page.next)))


@when(step(r'"anna" esporta le operazioni del flusso "{flow}" dalle ' + clock("since") + " alle " + clock("until")))
def export_period(bench: AttributionBench, register: Register, flow: str, since: str, until: str) -> None:
    register.exported = export_flow(bench, flow, OperationsQuery(since=at(since), until=at(until)))


@when(step(r'"anna" esporta le operazioni del flusso "{flow}"'))
def export_all(bench: AttributionBench, register: Register, flow: str) -> None:
    register.exported = export_flow(bench, flow, OperationsQuery())


@when(step(r'"anna" consulta tutte le operazioni del conto "{account}"'))
def consult_whole_account(bench: AttributionBench, register: Register, account: str) -> None:
    command = ListAccountOperationsCommand(bench.account(account), OperationsQuery(), AccountScope.ALL)
    register.reports.append(ListAccountOperationsUseCase(operations_of(bench)).execute(command))


@when(step(r'"anna" consulta le operazioni del conto "{account}" che non sono di nessun flusso'))
def consult_unattributed(bench: AttributionBench, register: Register, account: str) -> None:
    command = ListAccountOperationsCommand(bench.account(account), OperationsQuery(), AccountScope.UNATTRIBUTED)
    register.reports.append(ListAccountOperationsUseCase(operations_of(bench)).execute(command))


@when(step(r'"anna" esporta tutte le operazioni del conto "{account}"'))
def export_whole_account(bench: AttributionBench, register: Register, account: str) -> None:
    command = ExportAccountOperationsCommand(bench.account(account), OperationsQuery(), AccountScope.ALL)
    register.exported = list(ExportAccountOperationsUseCase(operations_of(bench)).execute(command))


@then(
    step(
        r"i totali riportano (?P<count>\d+) operazioni, PnL realizzato {a} USDC, commissioni {b} USDC"
        r" e funding {c} USDC"
    )
)
def totals(register: Register, count: str, a: str, b: str, c: str) -> None:
    found = register.reports[-1].totals
    assert (found.count, found.realized_pnl, found.fees, found.funding) == (int(count), amount(a), amount(b), amount(c))


@then(step(r"la pagina contiene (?P<count>\d+) operazioni"))
def page_size(register: Register, count: str) -> None:
    assert len(register.reports[-1].page.operations) == int(count)


@then(
    step(
        r"l'esportazione contiene le operazioni delle "
        + clock("first")
        + ", delle "
        + clock("second")
        + " e delle "
        + clock("third")
        + r', in quest\'ordine, del flusso "{flow}"'
    )
)
def exported_in_order(register: Register, first: str, second: str, third: str, flow: str) -> None:
    assert owners_of(register.exported) == [(at(first), flow), (at(second), flow), (at(third), flow)]


@then(step(r"l'esportazione contiene (?P<count>\d+) operazioni, dalla più vecchia"))
def exported_oldest_first(register: Register, count: str) -> None:
    instants = [operation.occurred_at for operation in register.exported]
    assert len(instants) == int(count)
    assert instants == sorted(instants)
    assert instants[0] == at("09:00")


@then(step(r"vede l'operazione (?P<rows>delle .+)"))
def rows_seen(register: Register, rows: str) -> None:
    assert owners_of(register.reports[-1].page.operations) == expected_rows(rows)


@then(step(r"l'esportazione contiene l'operazione (?P<rows>delle .+)"))
def rows_exported(register: Register, rows: str) -> None:
    assert owners_of(register.exported) == expected_rows(rows)
