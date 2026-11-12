"""The steps of the record and the consultation of the cycles (R1.7.1, R1.7.3, R1.4.6), shared by their modules."""

from collections.abc import Callable, Iterator
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.cycles.errors import CycleFlowNotFoundError
from autotrading.application.cycles.list_cycles import ListCyclesCommand
from autotrading.application.cycles.read_cycle import ReadCycleCommand
from autotrading.application.cycles.read_flow_cost import ReadFlowCostCommand
from autotrading.domain.cycles.call_cost import CallCost
from autotrading.domain.cycles.cycle_page import CyclePage
from autotrading.domain.cycles.cycle_record import CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.cycles.cycle_step import CycleStep
from autotrading.domain.cycles.flow_cost import DailyCost, FlowCost
from autotrading.domain.errors import AutotradingError
from tests.fakes.cycles import FakeTransientError
from tests.support.cycles import DAY, at
from tests.support.records import Records
from tests.support.steps import quoted

TIME = r"(?P<instant>\d\d:\d\d:\d\d)"


def amount(text: str) -> Decimal:
    return Decimal(text.replace(",", "."))


@pytest.fixture
def records() -> Iterator[Records]:
    world = Records()
    yield world
    world.release()


def consult(records: Records, query: Callable[[], object]) -> None:
    try:
        records.consulted = query()
    except AutotradingError as error:
        records.consulted = error


def a_recorded_cycle(flow_id: UUID, planned_at_text: str, back: timedelta = timedelta(0)) -> CycleRecord:
    planned_at = at(planned_at_text) - back
    documents = (
        StepDocument(CycleStep.COMPOSE_CONTEXT, {"messaggi": ["regole", "stato"]}),
        StepDocument(CycleStep.AGENT_DECISION, {"risposta": '{"decisioni": []}', "decisioni": []}),
        StepDocument(CycleStep.ORDER_EXECUTION, {"ordini": [{"asset": "BTC", "esito": "eseguito"}]}),
    )
    return CycleRecord(
        flow_id,
        planned_at,
        CycleOutcome.COMPLETED,
        started_at=planned_at,
        steps=tuple(CycleStep),
        documents=documents,
        cost=CallCost(1000, 200, Decimal("0.002")),
    )


# Given


@given(quoted('che "{user}" ha il flusso "{flow}" alla versione di configurazione {version} con modello "{model}"'))
def flow_at_version(records: Records, user: str, flow: str, version: str, model: str) -> None:
    records.add_flow(user, flow, int(version), model)


@given(quoted('che "{user}" ha il flusso "{flow}"'))
def flow_of_user(records: Records, user: str, flow: str) -> None:
    records.add_flow(user, flow)


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" attivo con intervallo di 15 minuti e '
        rf"(?P<count>\d+) cicli registrati, l'ultimo concluso alle {TIME}$"
    )
)
def flow_with_recorded_cycles(records: Records, user: str, flow: str, count: str, instant: str) -> None:
    flow_id = records.add_flow(user, flow)
    records.add_records(*(a_recorded_cycle(flow_id, instant, k * timedelta(minutes=15)) for k in range(int(count))))


@given("che il fornitore IA non risponde")
def provider_silent(records: Records) -> None:
    for flow_id in records.cycles.flows.flows:
        error = FakeTransientError("fornitore IA non raggiungibile: openrouter")
        records.cycles.failures.fail_once(flow_id, CycleStep.AGENT_DECISION, error)


@given(
    parsers.re(rf'^che il ciclo delle {TIME} del flusso "(?P<flow>[^"]+)" è saltato perché il precedente era in corso$')
)
def skipped_cycle(records: Records, instant: str, flow: str) -> None:
    cycles = records.cycles
    cycles.start(flow, "10:07:00")
    cycles.hold(flow, "10:07:00")
    cycles.tick(instant)
    cycles.record_at(flow, instant)


@given(
    quoted(
        'che il flusso "{flow}" ha registrato {count} cicli con costo {cost} USD ciascuno, {yesterday} ieri e '
        "{today} oggi"
    )
)
def cycles_with_cost(records: Records, *, flow: str, count: str, cost: str, yesterday: str, today: str) -> None:
    flow_id = records.cycles.id_of(flow)
    instants = [DAY - timedelta(hours=k + 1) for k in range(int(yesterday))]
    instants += [DAY + timedelta(hours=k + 1) for k in range(int(today))]
    assert len(instants) == int(count)
    records.add_records(
        *(
            CycleRecord(flow_id, instant, CycleOutcome.COMPLETED, cost=CallCost(1000, 200, amount(cost)))
            for instant in instants
        )
    )


# When


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def flow_runs_cycle(records: Records, flow: str) -> None:
    records.cycles.run_now(flow)


@when(quoted('"{user}" consulta i cicli del flusso "{flow}"'))
def consult_cycles(records: Records, user: str, flow: str) -> None:
    flow_id = records.cycles.id_of(flow)
    consult(records, lambda: records.use_cases_of(user).list_cycles.execute(ListCyclesCommand(flow_id)))


@when(quoted('"{user}" consulta la prima pagina dei cicli del flusso "{flow}"'))
def consult_first_page(records: Records, user: str, flow: str) -> None:
    flow_id = records.cycles.id_of(flow)
    consult(records, lambda: records.use_cases_of(user).list_cycles.execute(ListCyclesCommand(flow_id, 1)))


@when(quoted('"{user}" consulta il dettaglio dell\'ultimo ciclo del flusso "{flow}"'))
def consult_last_cycle(records: Records, user: str, flow: str) -> None:
    flow_id = records.cycles.id_of(flow)
    last = records.cycles.records.newest(flow_id, 0, 1)[0]
    consult(records, lambda: records.use_cases_of(user).read_cycle.execute(ReadCycleCommand(flow_id, last.planned_at)))


@when(quoted('"{user}" consulta il costo del flusso "{flow}"'))
def consult_cost(records: Records, user: str, flow: str) -> None:
    flow_id = records.cycles.id_of(flow)
    consult(records, lambda: records.use_cases_of(user).read_flow_cost.execute(ReadFlowCostCommand(flow_id)))


# Then


def recorded(records: Records) -> CycleRecord:
    return records.cycles.records.records[-1]


def page(records: Records) -> CyclePage:
    assert isinstance(records.consulted, CyclePage), records.consulted
    return records.consulted


def cost(records: Records) -> FlowCost:
    assert isinstance(records.consulted, FlowCost), records.consulted
    return records.consulted


@then(quoted('il ciclo registrato ha esito fallito al passo "{step}"'))
def failed_at_step(records: Records, step: str) -> None:
    record = recorded(records)
    assert record.outcome is CycleOutcome.FAILED
    assert record.failure is not None
    assert record.failure.step.value == step


@then("il ciclo registrato contiene i dati raccolti e il contesto inviato all'agente")
def contains_data_and_context(records: Records) -> None:
    record = recorded(records)
    assert record.document(CycleStep.COLLECT_SOURCES) is not None
    assert record.document(CycleStep.COMPOSE_CONTEXT) is not None


@then("il ciclo registrato non contiene decisioni né ordini")
def contains_no_decisions(records: Records) -> None:
    record = recorded(records)
    steps = (CycleStep.AGENT_DECISION, CycleStep.RISK_CHECK, CycleStep.ORDER_EXECUTION)
    assert [record.document(step) for step in steps] == [None, None, None]


@then(parsers.re(rf"^il ciclo delle {TIME} compare con esito saltato$"))
def appears_skipped(records: Records, instant: str) -> None:
    found = [cycle for cycle in page(records).cycles if cycle.planned_at == at(instant)]
    assert [cycle.outcome for cycle in found] == [CycleOutcome.SKIPPED]


@then(parsers.re(r"^la pagina contiene (?P<count>\d+) cicli dal più recente$"))
def page_from_newest(records: Records, count: str) -> None:
    cycles = page(records).cycles
    instants = [cycle.planned_at for cycle in cycles]
    assert len(cycles) == int(count)
    assert instants == sorted(instants, reverse=True)
    assert instants[0] == at("10:07:00")


@then("ogni ciclo riporta istante, esito e decisioni")
def every_cycle_has_decisions(records: Records) -> None:
    assert all(cycle.started_at and cycle.outcome for cycle in page(records).cycles)
    assert all(cycle.document(CycleStep.AGENT_DECISION) for cycle in page(records).cycles)


@then("il dettaglio contiene il contesto inviato all'agente, la risposta integrale e gli ordini con il loro esito")
def detail_complete(records: Records) -> None:
    detail = records.consulted
    assert isinstance(detail, CycleRecord), detail
    decision = detail.document(CycleStep.AGENT_DECISION)
    assert detail.document(CycleStep.COMPOSE_CONTEXT) == {"messaggi": ["regole", "stato"]}
    assert decision is not None
    assert decision["risposta"] == '{"decisioni": []}'
    assert detail.document(CycleStep.ORDER_EXECUTION) == {"ordini": [{"asset": "BTC", "esito": "eseguito"}]}


@then("la consultazione risponde che il flusso non esiste")
def flow_not_found(records: Records) -> None:
    assert isinstance(records.consulted, CycleFlowNotFoundError)


@then(quoted("il costo totale dall'avvio è {total} USD"))
def total_cost(records: Records, total: str) -> None:
    assert cost(records).total_usd == amount(total)


@then(quoted("il costo di ieri è {yesterday} USD e quello di oggi {today} USD"))
def daily_costs(records: Records, yesterday: str, today: str) -> None:
    assert cost(records).days == (
        DailyCost((DAY - timedelta(days=1)).date(), amount(yesterday)),
        DailyCost(DAY.date(), amount(today)),
    )
