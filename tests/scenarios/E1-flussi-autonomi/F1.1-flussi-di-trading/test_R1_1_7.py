import threading
import uuid
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest
from pytest_bdd import given, scenarios, then, when

from autotrading.application.flows.change_allocated_capital import ChangeAllocatedCapitalCommand
from autotrading.application.flows.list_capital_changes import ListCapitalChangesCommand
from autotrading.application.flows.read_free_capital import ReadFreeCapitalCommand
from autotrading.domain.flows.capital_change import CapitalChange
from autotrading.domain.flows.cycle_record import CycleOutcome, CycleRecord
from autotrading.domain.flows.cycle_step import CycleStep
from autotrading.domain.flows.flow_status import FlowStatus
from tests.fakes.model_call import HELD_SECONDS
from tests.support.activity import a_fill
from tests.support.flow_cycles import FlowCycles
from tests.support.flow_steps import *  # noqa: F403 - the steps of flow creation, shared by the features
from tests.support.flows import account_id_of
from tests.support.lifecycle_steps import *  # noqa: F403 - the steps of the life of a flow, shared by the features
from tests.support.lifecycle_steps import Lifecycle, add_flow, attempt, flow_named, hold_position, put_in_status
from tests.support.platform import Platform
from tests.support.steps import quoted

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.7-capitale-allocato.feature")


@pytest.fixture(name="flow_cycles")
def flow_cycles_of_the_worker() -> FlowCycles:
    return FlowCycles()


@pytest.fixture
def platform(flow_cycles: FlowCycles) -> Platform:
    return flow_cycles.platform


@given(quoted('che "{user}" ha il conto "{account}" con saldo {balance} USDC'))
def account_with_balance(platform: Platform, lifecycle: Lifecycle, user: str, account: str, balance: str) -> None:
    lifecycle.user = user
    account_id_of(platform, user, account, Decimal(balance))


@given(
    quoted(
        'che "{user}" ha il flusso "{name}" sul conto "{account}" con capitale allocato {capital} USDC '
        "e {margin} USDC impegnati come margine"
    )
)
def flow_with_margin(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, account: str, capital: str, margin: str
) -> None:
    flow = add_flow(platform, lifecycle, user, name, account=account, capital=Decimal(capital))
    (asset,) = flow.configuration.assets
    hold_position(platform, user, account, asset, Decimal(margin))


@given(quoted('che l\'exchange dichiara {margin} USDC di margine per la posizione del flusso "{name}"'))
def margin_declared(platform: Platform, lifecycle: Lifecycle, margin: str, name: str) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    reading = platform.account_activity.activities[flow.account_id]
    positions = tuple(
        replace(position, margin=Decimal(margin)) if position.asset in flow.configuration.assets else position
        for position in reading.positions
    )
    platform.account_activity.activities[flow.account_id] = replace(reading, positions=positions)


@given(quoted('che il flusso "{name}" ha realizzato {pnl} USDC con {fees} USDC di commissioni'))
def flow_realized(platform: Platform, lifecycle: Lifecycle, name: str, pnl: str, fees: str) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    (asset,) = flow.configuration.assets
    order_id = uuid.uuid4()
    fill = a_fill(asset, order_id, realized_pnl=Decimal(pnl), fee=Decimal(fees), fill_id=str(order_id))
    # What the cycles of the worker recorded in the ledger of the flow (ADR 0063).
    platform.ledger.add(flow.account_id, flow.id, fill)


@when(quoted('"{user}" porta il capitale allocato del flusso "{name}" a {capital} USDC'))
def change_capital(platform: Platform, lifecycle: Lifecycle, user: str, name: str, capital: str) -> None:
    flow_id = flow_named(platform, user, name).id
    command = ChangeAllocatedCapitalCommand(flow_id, Decimal(capital), platform.user_id_of(user))
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_allocated_capital.execute(command))


@then(quoted('il flusso "{name}" ha capitale allocato {capital} USDC'))
def allocated_capital(platform: Platform, lifecycle: Lifecycle, name: str, capital: str) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.allocated_capital == Decimal(capital)


@then(quoted('il capitale libero del conto "{account}" è {amount} USDC'))
def account_free_capital(platform: Platform, lifecycle: Lifecycle, account: str, amount: str) -> None:
    command = ReadFreeCapitalCommand(account_id_of(platform, lifecycle.user, account))
    capital = platform.use_cases_of(lifecycle.user).read_free_capital.execute(command)
    assert (capital.amount, capital.currency) == (Decimal(amount), "USDC")


@then(quoted('la variazione da {previous} a {new} USDC è registrata nello storico del flusso "{name}"'))
def change_recorded(platform: Platform, lifecycle: Lifecycle, previous: str, new: str, name: str) -> None:
    flow = flow_named(platform, lifecycle.user, name)
    changes = platform.use_cases_of(lifecycle.user).list_capital_changes.execute(ListCapitalChangesCommand(flow.id))
    user_id = platform.user_id_of(lifecycle.user)
    assert changes == (CapitalChange(flow.id, platform.now, Decimal(previous), Decimal(new), user_id),)


@then(quoted('la variazione è rifiutata con il motivo "{reason}"'))
def change_refused(lifecycle: Lifecycle, reason: str) -> None:
    assert str(lifecycle.error) == reason


@given(quoted('che un ciclo del flusso "{name}" è in corso con capitale allocato {capital} USDC'))
def cycle_in_progress(
    flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, name: str, capital: str
) -> None:
    assert flow_named(platform, lifecycle.user, name).configuration.allocated_capital == Decimal(capital)
    put_in_status(platform, lifecycle.user, name, FlowStatus.ACTIVE)
    flow_cycles.model.gate = threading.Event()
    flow_cycles.running = threading.Thread(target=flow_cycles.plan_round, daemon=True)
    flow_cycles.running.start()
    assert flow_cycles.model.entered.wait(HELD_SECONDS)


@then(quoted("il ciclo in corso si conclude con capitale allocato {capital} USDC"))
def cycle_ends_with_capital(flow_cycles: FlowCycles, capital: str) -> None:
    assert flow_cycles.model.gate is not None
    flow_cycles.model.gate.set()
    assert flow_cycles.running is not None
    flow_cycles.running.join(HELD_SECONDS)
    [record] = flow_cycles.records.records
    assert record.outcome is CycleOutcome.COMPLETED
    assert capital_of(record) == Decimal(capital)


@then(quoted('il ciclo successivo del flusso "{name}" usa capitale allocato {capital} USDC'))
def next_cycle_uses_capital(
    flow_cycles: FlowCycles, platform: Platform, lifecycle: Lifecycle, name: str, capital: str
) -> None:
    flow_cycles.model.gate = None
    flow_cycles.clock.current = flow_cycles.clock.now() + timedelta(minutes=15)
    flow_cycles.plan_round()
    record = flow_cycles.records.records[-1]
    assert record.flow_id == flow_named(platform, lifecycle.user, name).id.value
    assert capital_of(record) == Decimal(capital)


def capital_of(record: CycleRecord) -> Decimal:
    """The allocated capital the cycle read at its start, as the agent received it."""
    document = record.document(CycleStep.READ_FLOW_STATE)
    assert document is not None
    state = document["stato"]
    assert isinstance(state, dict)
    return Decimal(state["allocated_capital"])
