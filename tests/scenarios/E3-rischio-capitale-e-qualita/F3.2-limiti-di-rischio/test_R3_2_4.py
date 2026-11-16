"""The pause of a flow after too many failed cycles in a row, on the cycles the worker runs (R3.2.4)."""

from dataclasses import replace
from datetime import timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.application.flows.modify_flow import ModifyFlowCommand
from autotrading.domain.errors import AutotradingError
from autotrading.domain.flows.flow_action import FlowAction
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.notifications.linked_chat import LinkedChat
from tests.fakes.cycles import FakeTransientError
from tests.support.flow_cycle_steps import position
from tests.support.flow_cycles import FlowCycles
from tests.support.notifications import chat_named
from tests.support.steps import quoted

scenarios("E3-rischio-capitale-e-qualita/F3.2-limiti-di-rischio/R3.2.4-pausa-dopo-cicli-falliti-consecutivi.feature")

INTERVAL = timedelta(minutes=15)
# The message of a failure the scenario does not name.
ANY_FAILURE = "fornitore IA lento"


@pytest.fixture
def flow_cycles() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def refusals() -> list[AutotradingError]:
    return []


def next_cycle(flow_cycles: FlowCycles, flow: str, failure: str | None) -> None:
    """Runs the cycle due now, failing with the message when one is given, and moves to the next instant."""
    flow_cycles.model.failure = None if failure is None else FakeTransientError(failure)
    flow_cycles.run(flow)
    flow_cycles.clock.current += INTERVAL


def failed_cycles(flow_cycles: FlowCycles, flow: str, count: int, failure: str = ANY_FAILURE) -> None:
    for _ in range(count):
        next_cycle(flow_cycles, flow, failure)


def link_telegram(flow_cycles: FlowCycles, user: str) -> None:
    tenant_id = flow_cycles.platform.tenant_of(user)
    flow_cycles.platform.chats[tenant_id] = LinkedChat(tenant_id, chat_named(user))


# Given


@given(
    quoted(
        'che "{user}" ha il flusso "{flow}" attivo con asset "{asset}" e al massimo {maximum} cicli falliti consecutivi'
    )
)
def flow_with_maximum(flow_cycles: FlowCycles, user: str, flow: str, asset: str, maximum: str) -> None:
    flow_cycles.add_flow(user, flow, assets=(asset,))
    flow_cycles.reconfigure(flow, lambda configuration: replace(configuration, max_consecutive_failures=int(maximum)))
    link_telegram(flow_cycles, user)


@given(quoted('che "{user}" ha il flusso "{flow}" attivo senza massimo di cicli falliti consecutivi'))
def flow_without_maximum(flow_cycles: FlowCycles, user: str, flow: str) -> None:
    flow_cycles.add_flow(user, flow, assets=("ETH",))
    assert flow_cycles.flow(flow).configuration.max_consecutive_failures is None


@given(parsers.re(r'^che gli ultimi (?P<count>\d+) cicli di "(?P<flow>[^"]+)" sono falliti$'))
def last_cycles_failed(flow_cycles: FlowCycles, count: str, flow: str) -> None:
    failed_cycles(flow_cycles, flow, int(count))
    assert flow_cycles.flow(flow).status is FlowStatus.ACTIVE


@given(parsers.re(r'^che il flusso "(?P<flow>[^"]+)" è in pausa per (?P<count>\d+) cicli falliti consecutivi$'))
def paused_after_failures(flow_cycles: FlowCycles, flow: str, count: str) -> None:
    failed_cycles(flow_cycles, flow, int(count))
    assert flow_cycles.flow(flow).status is FlowStatus.PAUSED


@given(
    parsers.re(
        r'^che "(?P<flow>[^"]+)" ha una posizione aperta su "(?P<asset>[^"]+)" e gli ultimi (?P<count>\d+) cicli di '
        r'"(?P=flow)" sono falliti$'
    )
)
def open_position_and_failures(flow_cycles: FlowCycles, flow: str, asset: str, count: str) -> None:
    flow_cycles.platform.hyperliquid.open_position(flow_cycles.credentials_of(flow), position(asset))
    failed_cycles(flow_cycles, flow, int(count))


# When


@when(quoted('il ciclo successivo di "{flow}" fallisce con "{message}"'))
def next_cycle_fails_with(flow_cycles: FlowCycles, flow: str, message: str) -> None:
    next_cycle(flow_cycles, flow, message)


@when(quoted('il ciclo successivo di "{flow}" fallisce'))
def next_cycle_fails(flow_cycles: FlowCycles, flow: str) -> None:
    next_cycle(flow_cycles, flow, ANY_FAILURE)


@when(parsers.re(r'^il ciclo successivo di "(?P<flow>[^"]+)" riesce e i (?P<count>\d+) cicli seguenti falliscono$'))
def one_completed_then_failures(flow_cycles: FlowCycles, flow: str, count: str) -> None:
    next_cycle(flow_cycles, flow, None)
    failed_cycles(flow_cycles, flow, int(count))


@when(parsers.re(r'^(?P<count>\d+) cicli di "(?P<flow>[^"]+)" falliscono di fila$'))
def failures_in_a_row(flow_cycles: FlowCycles, count: str, flow: str) -> None:
    failed_cycles(flow_cycles, flow, int(count))


@when(
    parsers.re(r'^"(?P<user>[^"]+)" riprende il flusso "(?P<flow>[^"]+)" e i (?P<count>\d+) cicli seguenti falliscono$')
)
def resumed_then_failures(flow_cycles: FlowCycles, user: str, flow: str, count: str) -> None:
    flow_id = flow_cycles.flow(flow).id
    flow_cycles.platform.use_cases_of(user).change_flow_status.execute(
        ChangeFlowStatusCommand(flow_id, FlowAction.RESUME)
    )
    # As the trigger of the database: every change into "active" moves the anchor of the cycles to that instant.
    flow_cycles.platform.flows.anchors[flow_id] = flow_cycles.clock.now()
    failed_cycles(flow_cycles, flow, int(count))


@when(
    parsers.re(
        r'^"(?P<user>[^"]+)" imposta il massimo di cicli falliti consecutivi di "(?P<flow>[^"]+)" a (?P<value>-?\d+)$'
    )
)
def set_maximum(flow_cycles: FlowCycles, refusals: list[AutotradingError], user: str, flow: str, value: str) -> None:
    command = ModifyFlowCommand(flow_cycles.flow(flow).id, max_consecutive_failures=int(value))
    try:
        flow_cycles.platform.use_cases_of(user).modify_flow.execute(command)
    except AutotradingError as error:
        refusals.append(error)


# Then


@then(quoted('il flusso "{flow}" è in pausa con motivo "{reason}"'))
def paused_with_reason(flow_cycles: FlowCycles, flow: str, reason: str) -> None:
    paused = flow_cycles.flow(flow)
    assert (paused.status, flow_cycles.platform.flows.pause_reasons.get(paused.id)) == (FlowStatus.PAUSED, reason)


@then(quoted('"{user}" riceve la notifica "{text}"'))
def notified(flow_cycles: FlowCycles, user: str, text: str) -> None:
    received = flow_cycles.platform.messenger.received_by(chat_named(user))
    assert text in received, received


@then(quoted('il flusso "{flow}" resta attivo'))
def still_active(flow_cycles: FlowCycles, flow: str) -> None:
    assert flow_cycles.flow(flow).status is FlowStatus.ACTIVE


@then(quoted('la posizione di "{flow}" su "{asset}" resta aperta'))
def position_still_open(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    state = flow_cycles.platform.hyperliquid.read_state(flow_cycles.credentials_of(flow))
    assert flow_cycles.flow(flow).status is FlowStatus.PAUSED
    assert asset in {held.coin for held in state.positions}
    assert flow_cycles.platform.order_exchange.sent == []


@then(quoted('la modifica viene rifiutata con "{reason}"'))
def modification_refused(flow_cycles: FlowCycles, refusals: list[AutotradingError], reason: str) -> None:
    assert [str(error) for error in refusals] == [reason]
    assert flow_cycles.flow("alfa").configuration.max_consecutive_failures == 3
