"""The steps of the cycle scenarios (F1.2), shared by the requirement modules that import them."""

import re
from collections.abc import Iterator

import pytest
from pytest_bdd import given, parsers, then, when

from autotrading.domain.cycles.cycle_record import CycleOutcome
from autotrading.domain.cycles.cycle_step import CycleStep
from tests.fakes.cycles import ACTIVE, FakePermanentError, FakeTransientError
from tests.support.cycles import Cycles, at
from tests.support.steps import quoted

TIME = r"(?P<instant>\d\d:\d\d:\d\d)"


def instants_of(text: str) -> list[str]:
    return re.split(r", | e ", text)


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    yield world
    world.release()


# Given: the flows as the cycle sees them


@given(quoted('che "{user}" ha il flusso "{flow}" con intervallo di ciclo di {minutes} minuti'))
def flow_with_interval(cycles: Cycles, user: str, flow: str, minutes: str) -> None:  # noqa: ARG001 - the user owns it
    cycles.add_flow(flow, int(minutes))


@given(
    parsers.re(
        r'^che "(?P<user>[^"]+)" ha il flusso "(?P<flow>[^"]+)" attivo con intervallo di ciclo di '
        rf"(?P<minutes>\d+) minuti e un ciclo previsto alle {TIME}$"
    )
)
def active_flow_with_planned_cycle(cycles: Cycles, user: str, flow: str, minutes: str, instant: str) -> None:  # noqa: ARG001
    cycles.add_flow(flow, int(minutes), instant)


@given(
    quoted('che "{user}" ha il flusso "{flow}" attivo con intervallo di ciclo di {minutes} minuti e fonti "{sources}"')
)
def active_flow_with_sources(cycles: Cycles, user: str, flow: str, minutes: str, sources: str) -> None:  # noqa: ARG001
    cycles.add_flow(flow, int(minutes), sources=tuple(name.strip() for name in sources.split(",")))


@given(quoted('che "{user}" ha i flussi "{first}" e "{second}" attivi'))
def two_active_flows(cycles: Cycles, user: str, first: str, second: str) -> None:  # noqa: ARG001
    cycles.add_flow(first)
    cycles.add_flow(second)


@given(
    parsers.re(
        r'^che "[^"]+" ha i flussi "(?P<first>[^"]+)" e "(?P<second>[^"]+)" attivi sul conto "(?P<account>[^"]+)" '
        r'con modelli del fornitore "(?P<provider>[^"]+)"$'
    )
)
def two_flows_on_account(cycles: Cycles, first: str, second: str, account: str, provider: str) -> None:
    for name in (first, second):
        cycles.add_flow(name)
        cycles.flow(name).account, cycles.flow(name).provider = account, provider


@given(quoted('che "{user}" ha anche il flusso "{flow}" attivo con un modello del fornitore "{provider}"'))
def flow_of_other_provider(cycles: Cycles, user: str, flow: str, provider: str) -> None:  # noqa: ARG001
    cycles.add_flow(flow)
    cycles.flow(flow).account, cycles.flow(flow).provider = "altro-conto", provider


@given(parsers.re(rf'^che "(?P<user>[^"]+)" ha anche il flusso "(?P<flow>[^"]+)" con un ciclo previsto alle {TIME}$'))
def other_flow_planned(cycles: Cycles, user: str, flow: str, instant: str) -> None:  # noqa: ARG001
    cycles.add_flow(flow, anchor=instant)


@given(parsers.re(rf'^che il flusso "(?P<flow>[^"]+)" ha un ciclo previsto alle {TIME}$'))
def flow_planned(cycles: Cycles, flow: str, instant: str) -> None:
    cycles.start(flow, instant)


@given(
    parsers.re(
        rf'^che il flusso "(?P<flow>[^"]+)" è stato avviato alle {TIME} e messo in pausa alle '
        r"(?P<paused>\d\d:\d\d:\d\d)$"
    )
)
def flow_started_and_paused(cycles: Cycles, flow: str, instant: str, paused: str) -> None:
    cycles.start(flow, instant)
    cycles.tick(instant)
    cycles.record_at(flow, instant)
    cycles.clock.current = at(paused)
    cycles.pause(flow)


@given(quoted('che il flusso "{flow}" ha intervallo di ciclo di {minutes} minuti'))
def flow_interval(cycles: Cycles, flow: str, minutes: str) -> None:
    cycles.set_interval(flow, int(minutes))


@given(quoted('che il flusso "{flow}" ha una posizione aperta su "{asset}"'))
def open_position(cycles: Cycles, flow: str, asset: str) -> None:
    cycles.flow(flow).positions.add(asset)


@given("che due esecutori dei cicli sono in funzione")
def two_executors(cycles: Cycles) -> None:
    cycles.add_executor()


# Given: cycles in progress, completed or failed


@given(
    parsers.re(
        rf'^che il ciclo del flusso "(?P<flow>[^"]+)" iniziato alle {TIME} è ancora in corso alle '
        r"(?P<later>\d\d:\d\d:\d\d)$"
    )
)
def cycle_in_progress(cycles: Cycles, flow: str, instant: str, later: str) -> None:  # noqa: ARG001 - the When says it
    cycles.start(flow, instant)
    cycles.hold(flow, instant)


@given(
    parsers.re(
        rf'^che il ciclo del flusso "(?P<flow>[^"]+)" iniziato alle {TIME} si è concluso alle '
        r"(?P<ended>\d\d:\d\d:\d\d)$"
    )
)
def cycle_completed(cycles: Cycles, flow: str, instant: str, ended: str) -> None:
    cycles.start(flow, instant)
    cycles.tick(instant)
    assert cycles.record_at(flow, instant).outcome is CycleOutcome.COMPLETED
    cycles.clock.current = at(ended)


@given(parsers.re(rf'^che il ciclo delle {TIME} del flusso "(?P<flow>[^"]+)" è fallito per un errore transitorio$'))
def cycle_failed(cycles: Cycles, flow: str, instant: str) -> None:
    cycles.start(flow, instant)
    cycles.failures.fail_once(cycles.id_of(flow), CycleStep.AGENT_DECISION, FakeTransientError("timeout"))
    cycles.tick(instant)
    assert cycles.record_at(flow, instant).outcome is CycleOutcome.FAILED


@given(quoted('che il ciclo del flusso "{flow}" fallisce per un errore transitorio'))
def cycle_will_fail(cycles: Cycles, flow: str) -> None:
    cycles.failures.fail_once(cycles.id_of(flow), CycleStep.AGENT_DECISION, FakeTransientError("timeout"))


@given(quoted('che {system} non risponde durante il passo "{step}" del ciclo del flusso "{flow}"'))
def system_not_answering(cycles: Cycles, system: str, step: str, flow: str) -> None:
    cycles.failures.fail_once(cycles.id_of(flow), CycleStep(step), FakeTransientError(f"{system} non risponde"))


@given(quoted('che l\'agente decide di aprire su "{first}" e su "{second}"'))
def agent_opens(cycles: Cycles, first: str, second: str) -> None:
    cycles.agent.decisions[cycles.id_of("alfa")] = [first, second]


@given(quoted("che l'exchange non risponde all'ordine su \"{asset}\""))
def order_not_answered(cycles: Cycles, asset: str) -> None:
    cycles.orders.unanswered.add(asset)


@given(quoted('che il fornitore "{provider}" risponde credito esaurito'))
def credit_exhausted(cycles: Cycles, provider: str) -> None:
    error = FakePermanentError(f"credito esaurito presso {provider}", provider=provider)
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)


@given(quoted('che il fornitore "{provider}" rifiuta la chiave'))
def key_rejected(cycles: Cycles, provider: str) -> None:
    error = FakePermanentError(f"chiave del fornitore non valida: {provider}", provider=provider)
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.AGENT_DECISION, error)


@given(quoted('che l\'exchange rifiuta le credenziali del conto "{account}"'))
def credentials_rejected(cycles: Cycles, account: str) -> None:
    error = FakePermanentError(f"credenziali del conto non valide: {account}", account=account)
    cycles.failures.fail_once(cycles.id_of("alfa"), CycleStep.READ_FLOW_STATE, error)


@given(quoted('che la fonte "{source}" non risponde'))
def source_silent(cycles: Cycles, source: str) -> None:
    cycles.sources.silent.add(source)


@given(quoted('che le fonti "{first}" e "{second}" non rispondono'))
def sources_silent(cycles: Cycles, first: str, second: str) -> None:
    cycles.sources.silent.update({first, second})


@given(quoted('che la fonte "{source}" risponde dopo {seconds} secondi'))
def source_late(cycles: Cycles, source: str, seconds: str) -> None:
    cycles.sources.late[source] = float(seconds)


# When


@when(parsers.re(rf'^"(?P<user>[^"]+)" (?:avvia|riprende) il flusso "(?P<flow>[^"]+)" alle {TIME}$'))
def start_flow(cycles: Cycles, user: str, flow: str, instant: str) -> None:  # noqa: ARG001
    cycles.start(flow, instant)


@when(parsers.re(rf"^arrivano le {TIME}$"))
def time_comes(cycles: Cycles, instant: str) -> None:
    cycles.tick(instant)


@when(parsers.re(rf"^il ciclo parte alle {TIME}$"))
def cycle_starts_at(cycles: Cycles, instant: str) -> None:
    cycles.tick(instant)


@when(quoted('il flusso "{flow}" esegue un ciclo'))
def flow_runs_cycle(cycles: Cycles, flow: str) -> None:
    cycles.run_now(flow)


@when(quoted('i flussi "{first}" e "{second}" eseguono un ciclo'))
def flows_run_cycle(cycles: Cycles, first: str, second: str) -> None:
    cycles.run_now(first)
    cycles.run_now(second)


# Then: when the cycles run


@then(parsers.re(r'^il flusso "(?P<flow>[^"]+)" esegue cicli alle (?P<instants>.+)$'))
def flow_runs_cycles_at(cycles: Cycles, flow: str, instants: str) -> None:
    for instant in instants_of(instants):
        cycles.tick(instant)
        assert cycles.record_at(flow, instant).outcome is CycleOutcome.COMPLETED
    planned = [record.planned_at for record in cycles.records_of(flow) if record.outcome is CycleOutcome.COMPLETED]
    assert planned[-len(instants_of(instants)) :] == [at(instant) for instant in instants_of(instants)]


@then(parsers.re(rf'^il flusso "(?P<flow>[^"]+)" esegue il ciclo delle {TIME}$'))
def flow_runs_cycle_of(cycles: Cycles, flow: str, instant: str) -> None:
    assert cycles.record_at(flow, instant).outcome is CycleOutcome.COMPLETED


@then(parsers.re(r"^il ciclo è registrato con un ritardo di (?P<seconds>\d+) secondi$"))
def recorded_late(cycles: Cycles, seconds: str) -> None:
    cycles.launcher.settle()
    assert cycles.last_record("alfa").delay_seconds == int(seconds)


@then("il ciclo è registrato senza ritardo")
def recorded_punctual(cycles: Cycles) -> None:
    cycles.launcher.settle()
    record = cycles.last_record("alfa")
    assert record.outcome is CycleOutcome.COMPLETED
    assert record.delay_seconds is None


@then(quoted('il ciclo del flusso "{flow}" parte puntuale'))
def starts_punctual(cycles: Cycles, flow: str) -> None:
    record = cycles.record_at(flow, "10:22:00")
    assert (record.outcome, record.delay_seconds) == (CycleOutcome.COMPLETED, None)


@then(parsers.re(rf'^il ciclo delle {TIME} del flusso "(?P<flow>[^"]+)" è registrato come saltato$'))
def recorded_skipped(cycles: Cycles, instant: str, flow: str) -> None:
    assert cycles.record_at(flow, instant).outcome is CycleOutcome.SKIPPED


@then(parsers.re(rf'^il prossimo ciclo del flusso "(?P<flow>[^"]+)" è previsto alle {TIME}$'))
def next_planned(cycles: Cycles, flow: str, instant: str) -> None:
    assert cycles.flow(flow).schedule.next_after(cycles.clock.now()) == at(instant)


@then(parsers.re(rf'^il ciclo delle {TIME} del flusso "(?P<flow>[^"]+)" è eseguito una sola volta$'))
def run_once(cycles: Cycles, instant: str, flow: str) -> None:
    cycles.launcher.settle()
    assert [record.planned_at for record in cycles.records_of(flow)] == [at(instant)]
    assert cycles.agent.calls == [cycles.id_of(flow)]


@then("il ciclo registra i passi in quest'ordine:")
def steps_in_order(cycles: Cycles, datatable: list[list[str]]) -> None:
    assert [step.value for step in cycles.last_record("alfa").steps] == [row[0].strip() for row in datatable[1:]]


# Then: failures and pauses


@then(quoted('il ciclo è registrato come fallito al passo "{step}" con il messaggio originale'))
def failed_with_original_message(cycles: Cycles, step: str) -> None:
    failure = cycles.last_record("alfa").failure
    assert failure is not None
    assert (failure.step.value, failure.error_type) == (step, "FakeTransientError")
    assert failure.message.endswith(" non risponde")


@then(quoted('il ciclo è registrato come fallito al passo "{step}"'))
def failed_at_step(cycles: Cycles, step: str) -> None:
    record = cycles.last_record("alfa")
    assert record.outcome is CycleOutcome.FAILED
    assert record.failure is not None
    assert record.failure.step.value == step


@then(quoted('il ciclo è registrato come fallito con il motivo "{reason}"'))
def failed_with_reason(cycles: Cycles, reason: str) -> None:
    failure = cycles.last_record("alfa").failure
    assert failure is not None
    assert failure.message == reason
    assert cycles.raised is not None
    assert str(cycles.raised) == reason


@then("il ciclo non invia ordini all'exchange")
def no_orders(cycles: Cycles) -> None:
    assert cycles.orders.sent == []


@then(quoted('l\'ordine su "{asset}" non viene inviato'))
def order_not_sent(cycles: Cycles, asset: str) -> None:
    assert asset not in [order for _, _, order in cycles.orders.sent]


@then(quoted('il flusso "{flow}" è nello stato "{status}" con il motivo "{reason}"'))
def flow_status_with_reason(cycles: Cycles, flow: str, status: str, reason: str) -> None:
    assert (cycles.flow(flow).status, cycles.flow(flow).pause_reason) == (status, reason)


@then(quoted('il flusso "{flow}" è nello stato "{status}"'))
def flow_status(cycles: Cycles, flow: str, status: str) -> None:
    assert cycles.flow(flow).status == status


@then(quoted('il ciclo del flusso "{flow}" si conclude regolarmente'))
def completes(cycles: Cycles, flow: str) -> None:
    assert cycles.last_record(flow).outcome is CycleOutcome.COMPLETED
    assert cycles.flow(flow).status == ACTIVE


@then(quoted('la posizione su "{asset}" resta aperta sull\'exchange'))
def position_stays_open(cycles: Cycles, asset: str) -> None:
    assert asset in cycles.flow("alfa").positions
    assert cycles.orders.sent == []


# Then: sources


@then(quoted('il contesto inviato all\'agente contiene i dati della fonte "{source}"'))
def context_has_source(cycles: Cycles, source: str) -> None:
    assert [reading.source for reading in cycles.context.composed[cycles.id_of("alfa")].readings] == [source]


@then("il contesto inviato all'agente contiene lo stato del flusso")
def context_has_state(cycles: Cycles) -> None:
    composed = cycles.context.composed[cycles.id_of("alfa")]
    assert composed.snapshot.state == {"flow": "alfa", "positions": []}
    assert composed.readings == ()


@then(quoted('il contesto dichiara mancanti i dati della fonte "{source}"'))
def context_declares_missing(cycles: Cycles, source: str) -> None:
    assert [absent.source for absent in cycles.context.composed[cycles.id_of("alfa")].absent] == [source]


@then(quoted('il contesto dichiara mancanti i dati delle fonti "{first}" e "{second}"'))
def context_declares_both_missing(cycles: Cycles, first: str, second: str) -> None:
    assert [absent.source for absent in cycles.context.composed[cycles.id_of("alfa")].absent] == [first, second]


@then(quoted('il ciclo registra la fonte "{source}" come assente con il motivo "{reason}"'))
def source_recorded_absent(cycles: Cycles, source: str, reason: str) -> None:
    absent = cycles.last_record("alfa").absent_sources
    assert [(item.source, item.reason) for item in absent] == [(source, reason)]


@then("il ciclo prosegue fino alla decisione dell'agente")
def reaches_decision(cycles: Cycles) -> None:
    record = cycles.last_record("alfa")
    assert CycleStep.AGENT_DECISION in record.steps
    assert record.outcome is CycleOutcome.COMPLETED
