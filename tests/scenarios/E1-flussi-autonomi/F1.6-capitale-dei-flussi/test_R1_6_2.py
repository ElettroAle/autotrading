import json
from datetime import timedelta
from uuid import uuid4

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.unattributable import UnattributableItem, UnattributableKind
from autotrading.domain.notifications.chat_id import ChatId
from autotrading.domain.notifications.linked_chat import LinkedChat
from tests.support.activity import READ_AT, a_fill, a_movement, a_position, an_activity
from tests.support.attribution import AttributionBench, amount, step
from tests.support.flow_cycles import FlowCycles

CHAT = ChatId(4242)

scenarios("E1-flussi-autonomi/F1.6-capitale-dei-flussi/R1.6.2-movimenti-non-attribuibili.feature")


@pytest.fixture
def bench() -> AttributionBench:
    return AttributionBench()


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    """The same flow run by the worker: the position it expects is compared at the start of its cycle (Bug 155)."""
    return FlowCycles()


def recorded(bench: AttributionBench, account: str, kind: UnattributableKind) -> list[UnattributableItem]:
    account_id = bench.account(account)
    return [item for item in bench.readings.items if item.account_id == account_id and item.kind is kind]


@given(step(r'che "anna" ha il conto "{account}" con il solo flusso "{flow}" con asset "{asset}"'))
def single_flow(bench: AttributionBench, flow_cycles: FlowCycles, account: str, flow: str, asset: str) -> None:
    bench.add_flow(account, flow, (asset,))
    flow_cycles.add_flow("anna", flow, assets=(asset,), account=account)


@given(step(r'che "anna" ha collegato Telegram'))
def telegram_linked(flow_cycles: FlowCycles) -> None:
    tenant_id = flow_cycles.platform.tenant_of("anna")
    flow_cycles.platform.chats[tenant_id] = LinkedChat(tenant_id, CHAT)


@given(step(r'che il flusso "{flow}" ha aperto {a} "{asset}" con i propri ordini'))
def opened_by_flow(flow_cycles: FlowCycles, flow: str, a: str, asset: str) -> None:
    order, owner = uuid4(), flow_cycles.flow(flow)
    flow_cycles.platform.platform_orders.add(order, owner.account_id, owner.id)
    address = flow_cycles.credentials_of(flow).account_address
    opening = a_fill(asset, order, size=amount(a), executed_at=READ_AT - timedelta(minutes=10))
    flow_cycles.platform.activity_reader.executions.setdefault(address, []).append(opening)


@given(step(r'che sull\'exchange il conto "{account}" ha una posizione di {a} "{asset}"'))
def position_on_account(flow_cycles: FlowCycles, account: str, a: str, asset: str) -> None:
    (flow,) = flow_cycles.platform.flows.flows
    address = flow_cycles.credentials_of(flow.name.value, account).account_address
    flow_cycles.platform.activity_reader.activities[address] = an_activity(
        positions=(a_position(asset, size=amount(a)),)
    )


@given(step(r'che sull\'exchange il conto "{account}" ha una posizione aperta su "{asset}"'))
def position_of_no_flow(bench: AttributionBench, account: str, asset: str) -> None:
    bench.extend(bench.account(account), positions=(a_position(asset),))


@given(step(r'che il flusso "{flow}" aveva una posizione aperta su "{asset}"'))
def position_seen_open(bench: AttributionBench, flow: str, asset: str) -> None:
    bench.previous_reading(bench.flow(flow).account_id, {flow: frozenset({asset})})


@given(step(r'che sull\'exchange la posizione su "{asset}" non c\'è più'))
def position_gone(bench: AttributionBench, asset: str) -> None:
    assert all(asset not in {p.asset for p in activity.positions} for activity in bench.exchange.activities.values())


@given(step(r'che il saldo del conto "{account}" è aumentato di {a} USDC senza esecuzioni dei flussi'))
def balance_increased(bench: AttributionBench, account: str, a: str) -> None:
    account_id = bench.account(account)
    bench.previous_reading(account_id)
    bench.extend(account_id, movements=(a_movement(amount(a)),))


@given(step(r'che per il conto "{account}" è già registrata una posizione non attribuibile su "{asset}"'))
def already_recorded(bench: AttributionBench, account: str, asset: str) -> None:
    bench.extend(bench.account(account), positions=(a_position(asset),))
    (flow,) = bench.store.flows
    bench.run_cycle(flow.name.value)
    assert len(recorded(bench, account, UnattributableKind.POSITION)) == 1


@when(step(r'il flusso "{flow}" esegue un ciclo'))
@when(step(r'il flusso "{flow}" esegue un altro ciclo'))
def run_cycle(bench: AttributionBench, flow: str) -> None:
    bench.run_cycle(flow)


@when(step(r'parte un ciclo del flusso "{flow}" in cui l\'agente apre "{asset}"'))
def cycle_opens(flow_cycles: FlowCycles, flow: str, asset: str) -> None:
    opening = {"asset": asset, "azione": "apri", "direzione": "long", "quota": 0.1, "leva": 1, "ragionamento": "r"}
    flow_cycles.model.text = json.dumps({"decisioni": [opening]})
    flow_cycles.run(flow)


@then("nessun ordine è inviato")
def no_order(flow_cycles: FlowCycles) -> None:
    assert flow_cycles.platform.order_exchange.sent == []


@then(step(r'il flusso "{flow}" è in pausa con il motivo "{reason}"'))
def paused_with_reason(flow_cycles: FlowCycles, flow: str, reason: str) -> None:
    paused = flow_cycles.flow(flow)
    assert (paused.status, flow_cycles.platform.flows.pause_reasons[paused.id]) == (FlowStatus.PAUSED, reason)


@then(step(r'"anna" riceve la notifica "{reason}"'))
def notified(flow_cycles: FlowCycles, reason: str) -> None:
    assert reason in flow_cycles.platform.messenger.received_by(CHAT)


@then(step(r'è registrata per il conto "{account}" una posizione non attribuibile su "{asset}"'))
def position_recorded(bench: AttributionBench, account: str, asset: str) -> None:
    assert [item.asset for item in recorded(bench, account, UnattributableKind.POSITION)] == [asset]


@then(step(r'la posizione su "{asset}" resta aperta sull\'exchange'))
def position_still_open(bench: AttributionBench, asset: str) -> None:
    assert any(asset in {p.asset for p in activity.positions} for activity in bench.exchange.activities.values())


@then(step(r'il flusso "{flow}" è nello stato "{status}"'))
def flow_status(bench: AttributionBench, flow: str, status: str) -> None:
    assert bench.flow(flow).status.value == status


@then(step(r'la posizione su "{asset}" compare nello storico del flusso "{flow}" come chiusa con il motivo "{reason}"'))
def closed_in_history(bench: AttributionBench, asset: str, flow: str, reason: str) -> None:
    flow_id = bench.flow(flow).id
    assert [(c.asset, c.reason) for c in bench.closed.closed if c.flow_id == flow_id] == [(asset, reason)]


@then(step(r'è registrata per il conto "{account}" una variazione del saldo non attribuibile di {a} USDC'))
def balance_change_recorded(bench: AttributionBench, account: str, a: str) -> None:
    assert [item.amount for item in recorded(bench, account, UnattributableKind.BALANCE_CHANGE)] == [amount(a)]


@then(step(r'per il conto "{account}" c\'è una sola registrazione della posizione non attribuibile su "{asset}"'))
def recorded_once(bench: AttributionBench, account: str, asset: str) -> None:
    items = recorded(bench, account, UnattributableKind.POSITION)
    assert [item.asset for item in items] == [asset]
    assert len(items) == 1
