"""The steps of the record and the consultation of the cycles (R1.7.1, R1.7.3, R1.4.6), shared by their modules."""

import json
from collections.abc import Callable, Iterator, Mapping
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.application.agent.errors import ModelUnavailableError
from autotrading.application.flows.errors import CycleFlowNotFoundError
from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.list_flow_overviews import FlowOverview
from autotrading.application.flows.read_cycle import ReadCycleCommand
from autotrading.application.flows.read_flow_cost import ReadFlowCostCommand
from autotrading.domain.agent.model_definition import ModelDefinition
from autotrading.domain.agent.model_usage import ModelPrices, ModelUsage
from autotrading.domain.agent.provider_name import ProviderName
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.call_cost import CallCost
from autotrading.domain.flows.cycle_page import CyclePage
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord, StepDocument
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_cost import DailyCost, FlowCost
from autotrading.domain.flows.flow_id import FlowId
from tests.support.cycles import DAY, at
from tests.support.flows import ANTHROPIC_MODEL, OPENROUTER_MODEL, TEMPERATURE, scenario_catalog
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
    # The flow started with its first recorded cycle, and the user consults it within the interval of the last one.
    records.platform.flows.anchors[FlowId(flow_id)] = at(instant) - (int(count) - 1) * timedelta(minutes=15)
    records.platform.now = at(instant) + timedelta(minutes=1)


@given("che il fornitore IA non risponde")
def provider_silent(records: Records) -> None:
    records.flow_cycles.model.failure = ModelUnavailableError(ProviderName("openrouter"), "tempo di risposta scaduto")


@given(
    parsers.re(
        r"^che il fornitore riporta per la chiamata (?P<tokens_in>\d+) token in ingresso, (?P<tokens_out>\d+) in "
        r"uscita e costo (?P<cost>[\d,]+) USD$"
    )
)
def provider_reports_cost(records: Records, tokens_in: str, tokens_out: str, cost: str) -> None:
    records.flow_cycles.model.usage = ModelUsage(int(tokens_in), int(tokens_out), amount(cost))


@given(
    parsers.re(
        r"^che il fornitore non riporta il costo e riporta (?P<tokens_in>\d+) token in ingresso e "
        r"(?P<tokens_out>\d+) in uscita$"
    )
)
def provider_without_cost(records: Records, tokens_in: str, tokens_out: str) -> None:
    records.flow_cycles.model.usage = ModelUsage(int(tokens_in), int(tokens_out), None)


@given(
    parsers.re(
        r"^che il catalogo prezza il modello (?P<price_in>[\d,]+) USD per milione di token in ingresso e "
        r"(?P<price_out>[\d,]+) USD per milione in uscita$"
    )
)
def catalog_prices(records: Records, price_in: str, price_out: str) -> None:
    prices = ModelPrices(amount(price_in), amount(price_out))
    records.platform.model_catalog = scenario_catalog(
        ModelDefinition(OPENROUTER_MODEL, (TEMPERATURE,), prices), ModelDefinition(ANTHROPIC_MODEL, (TEMPERATURE,))
    )


@given("che né il fornitore né il catalogo riportano il prezzo")
def no_price(records: Records) -> None:
    records.flow_cycles.model.usage = ModelUsage(1000, 200, None)


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
    records.flow_cycles.run(flow)


@when(quoted('il flusso "{flow}" esegue un ciclo concluso con un\'apertura su "{asset}"'))
def flow_opens_in_cycle(records: Records, flow: str, asset: str) -> None:
    opening = {"asset": asset, "azione": "apri", "direzione": "long", "quota": 0.5, "leva": 2, "ragionamento": "r"}
    records.flow_cycles.model.text = json.dumps({"decisioni": [opening]})
    records.flow_cycles.run(flow)
    assert recorded(records).outcome is CycleOutcome.COMPLETED


@when(quoted('"{user}" consulta i propri flussi'))
def consult_own_flows(records: Records, user: str) -> None:
    consult(records, records.use_cases_of(user).list_flow_overviews.execute)


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


@then("il ciclo registrato contiene:")
def recorded_contents(records: Records, datatable: list[list[str]]) -> None:
    record = recorded(records)
    flow = record.document(CycleStep.READ_FLOW_STATE)
    assert flow is not None
    checks = {
        "utente, flusso, conto e ambiente": lambda: all(flow[key] for key in ("utente", "flusso", "conto", "ambiente")),
        "istante previsto e istante effettivo": lambda: record.started_at is not None and record.planned_at is not None,
        "esito concluso": lambda: record.outcome is CycleOutcome.COMPLETED,
        "pesi delle fonti": lambda: "pesi_fonti" in flow,
        "dati raccolti": lambda: record.document(CycleStep.COLLECT_SOURCES) is not None,
        "contesto integrale inviato all'agente": lambda: _context_sent(record),
        "risposta integrale dell'agente": lambda: _decisions(record)["risposta"] == records.flow_cycles.model.text,
        "decisioni interpretate": lambda: len(_list(_decisions(record)["decisioni"])) == 1,
        "esito del rischio per ogni decisione": lambda: (
            len(_list(_document(record, CycleStep.RISK_CHECK)["esiti"])) == 1
        ),
        "costo della chiamata al modello": lambda: record.cost is not None,
        "istantanea dello stato del flusso": lambda: "stato" in _document(record, CycleStep.UPDATE_FLOW_STATE),
    }
    for [element] in datatable[1:]:
        assert _element_holds(element, flow, record, checks), element


def _element_holds(
    element: str, flow: Mapping[str, object], record: CycleRecord, checks: Mapping[str, Callable[[], bool]]
) -> bool:
    if element.startswith("versione di configurazione "):
        return flow["versione"] == int(element.rpartition(" ")[2])
    if element.startswith("modello "):
        return flow["modello"] == element.partition(" ")[2]
    if element.startswith("ordine su "):
        asset = element.split(" ")[2]
        orders = _list(_document(record, CycleStep.ORDER_EXECUTION)["risultato"])
        return any(asset in json.dumps(order) and "status" in json.dumps(order) for order in orders)
    return checks[element]()


def _document(record: CycleRecord, step: CycleStep) -> Mapping[str, object]:
    document = record.document(step)
    assert document is not None, step
    return document


def _decisions(record: CycleRecord) -> Mapping[str, object]:
    return _document(record, CycleStep.AGENT_DECISION)


def _context_sent(record: CycleRecord) -> bool:
    messages = _list(_document(record, CycleStep.COMPOSE_CONTEXT)["messaggi"])
    return len(messages) == 2


def _list(value: object) -> list[object]:
    assert isinstance(value, list), value
    return value


@then(
    parsers.re(
        r"^il ciclo registra (?P<tokens_in>\d+) token in ingresso, (?P<tokens_out>\d+) in uscita e costo "
        r"(?P<cost>[\d,]+) USD$"
    )
)
def recorded_tokens_and_cost(records: Records, tokens_in: str, tokens_out: str, cost: str) -> None:
    assert recorded(records).cost == CallCost(int(tokens_in), int(tokens_out), amount(cost))


@then(parsers.re(r"^il ciclo registra costo (?P<cost>[\d,]+) USD$"))
def recorded_cost(records: Records, cost: str) -> None:
    call = recorded(records).cost
    assert call is not None
    assert call.cost_usd == amount(cost)


@then("il ciclo registra il costo come non disponibile")
def recorded_cost_unavailable(records: Records) -> None:
    call = recorded(records).cost
    assert call is not None
    assert call.cost_usd is None


def overviews(records: Records) -> list[FlowOverview]:
    assert isinstance(records.consulted, list), records.consulted
    return [overview for overview in records.consulted if isinstance(overview, FlowOverview)]


@then(
    parsers.re(
        r"^l'elenco contiene il flusso \"(?P<flow>[^\"]+)\" nello stato \"(?P<status>[^\"]+)\" con ultimo ciclo alle "
        r"(?P<last>\d\d:\d\d:\d\d) concluso e prossimo ciclo alle (?P<following>\d\d:\d\d:\d\d)$"
    )
)
def flow_in_overview(records: Records, flow: str, status: str, last: str, following: str) -> None:
    [overview] = [overview for overview in overviews(records) if overview.summary.name == flow]
    assert overview.summary.status == status
    assert overview.last_cycle is not None
    assert (overview.last_cycle.planned_at, overview.last_cycle.outcome) == (at(last), CycleOutcome.COMPLETED)
    assert overview.next_cycle_at == at(following)
    assert overview.environment == "dev"


@then(quoted('l\'elenco non contiene il flusso "{flow}"'))
def flow_not_in_overview(records: Records, flow: str) -> None:
    assert flow not in [overview.summary.name for overview in overviews(records)]
