"""R6.5.2: the cycle the user asks for now, from the use case of the API through the worker, which runs it as it
composes the planned cycles (ADR ciclo-su-richiesta-nel-worker, ADR comando-del-ciclo-su-richiesta-nell-api).
playwright-bdd runs the same scenarios on the build of the dashboard (ADR pulsante-esegui-ora-nella-pagina-del-flusso);
here opening the page of the flow is reading the status the API gives it, the only thing the command follows.
"""

from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import dataclass, replace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.list_cycles import ListCyclesCommand
from autotrading.application.flows.list_flow_overviews import ListFlowOverviewsCommand
from autotrading.application.flows.request_on_demand_cycle import RequestOnDemandCycleCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.cycle_interval import CycleInterval
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.cycle_trigger import CycleTrigger
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_cycles import FlowCycles, at
from tests.support.steps import quoted

scenarios("E6-piattaforma-e-operativita/F6.5-usabilita-della-dashboard/R6.5.2-ciclo-eseguito-su-richiesta.feature")


@dataclass
class Request:
    """What the last «Esegui ora» gave back: the cycle or the refusal, and the status of the flow the page read."""

    user: str = ""
    cycle: CycleRecord | None = None
    refusal: AutotradingError | None = None
    status: FlowStatus | None = None

    @property
    def refused(self) -> AutotradingError:
        assert self.refusal is not None, "la richiesta non è stata rifiutata"
        return self.refusal

    @property
    def ran(self) -> CycleRecord:
        assert self.cycle is not None, f"nessun ciclo eseguito: {self.refusal}"
        return self.cycle


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def request_now() -> Request:
    return Request()


@pytest.fixture
def held() -> Iterator[ExitStack]:
    with ExitStack() as stack:
        yield stack


def records_of(flow_cycles: FlowCycles, name: str) -> list[CycleRecord]:
    flow_id = flow_cycles.flow(name).id.value
    return [record for record in flow_cycles.records.records if record.flow_id == flow_id]


def ask_now(flow_cycles: FlowCycles, request_now: Request, user: str, name: str) -> None:
    request_now.user = user
    command = RequestOnDemandCycleCommand(flow_cycles.flow(name).id.value)
    try:
        request_now.cycle = flow_cycles.platform.use_cases_of(user).request_on_demand_cycle.execute(command)
    except AutotradingError as error:
        request_now.refusal = error


@given(quoted('che "{user}" ha il flusso attivo "{name}" con un ciclo ogni 60 minuti, il prossimo alle 11:00'))
def active_flow_every_hour(flow_cycles: FlowCycles, user: str, name: str) -> None:
    flow_cycles.add_flow(user, name, started="10:00")
    flow_cycles.reconfigure(name, lambda configuration: replace(configuration, cycle_interval=CycleInterval(60)))


@given(quoted('che un ciclo di "{name}" è in corso'))
def cycle_in_progress(flow_cycles: FlowCycles, held: ExitStack, name: str) -> None:
    acquired = held.enter_context(flow_cycles.lock.hold(flow_cycles.flow(name).id.value))
    assert acquired


@given(parsers.parse('che il flusso "{name}" è {status}'))
def flow_in_status(flow_cycles: FlowCycles, name: str, status: str) -> None:
    flows = flow_cycles.platform.flows.flows
    index = flows.index(flow_cycles.flow(name))
    flows[index] = replace(flows[index], status=FlowStatus(status))


@when(quoted('"{user}" sceglie «Esegui ora» sul flusso "{name}" alle {clock}'))
def run_now_at(flow_cycles: FlowCycles, request_now: Request, user: str, name: str, clock: str) -> None:
    flow_cycles.clock.current = flow_cycles.platform.now = at(clock)
    ask_now(flow_cycles, request_now, user, name)


@when(quoted('"{user}" sceglie «Esegui ora» sul flusso "{name}"'))
def run_now(flow_cycles: FlowCycles, request_now: Request, user: str, name: str) -> None:
    ask_now(flow_cycles, request_now, user, name)


@when(quoted('"{user}" apre la pagina del flusso "{name}"'))
def open_flow_page(flow_cycles: FlowCycles, request_now: Request, user: str, name: str) -> None:
    flows = flow_cycles.platform.use_cases_of(user).list_flows.execute()
    request_now.status = next(flow.status for flow in flows if flow.name.value == name)


@then(quoted('il worker esegue un ciclo completo di "{name}"'))
def complete_cycle(flow_cycles: FlowCycles, request_now: Request, name: str) -> None:
    [record] = records_of(flow_cycles, name)
    assert (record.outcome, record.steps) == (CycleOutcome.COMPLETED, tuple(CycleStep))
    assert request_now.ran == record


@then("il ciclo compare tra i cicli come eseguito su richiesta")
def listed_on_demand(flow_cycles: FlowCycles, request_now: Request) -> None:
    flow_id = request_now.ran.flow_id
    page = flow_cycles.platform.use_cases_of(request_now.user).list_cycles.execute(ListCyclesCommand(flow_id))
    assert [(cycle.planned_at, cycle.trigger) for cycle in page.cycles] == [(at("10:20"), CycleTrigger.ON_DEMAND)]


@then(quoted("il ciclo pianificato successivo resta alle {clock}"))
def next_planned_cycle(flow_cycles: FlowCycles, request_now: Request, clock: str) -> None:
    flow_id = request_now.ran.flow_id
    overviews = flow_cycles.platform.use_cases_of(request_now.user).list_flow_overviews.execute(
        ListFlowOverviewsCommand("all")
    )
    [overview] = [each for each in overviews if each.summary.flow_id == flow_id]
    assert overview.next_cycle_at == at(clock)


@then(quoted('la richiesta è rifiutata con stato 409 e il motivo "{reason}"'))
def refused_with_conflict(request_now: Request, reason: str) -> None:
    assert (request_now.refused.status_code, str(request_now.refused)) == (409, reason)


@then("non parte un secondo ciclo")
def no_second_cycle(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.records.records == []
    assert flow_cycles.model.calls == []


@then("non vede il comando «Esegui ora»")
def no_run_now_command(request_now: Request) -> None:
    # The page offers «Esegui ora» only to the flow the API says active (ADR
    # pulsante-esegui-ora-nella-pagina-del-flusso).
    assert request_now.status is not None
    assert not request_now.status.runs_cycles


@then(quoted('la richiesta dall\'interfaccia programmatica è rifiutata con il motivo "{reason}"'))
def refused_by_the_api(flow_cycles: FlowCycles, request_now: Request, reason: str) -> None:
    [flow] = flow_cycles.platform.flows.flows
    ask_now(flow_cycles, request_now, flow_cycles.users[flow.name.value], flow.name.value)
    assert str(request_now.refused) == reason
    assert flow_cycles.records.records == []
