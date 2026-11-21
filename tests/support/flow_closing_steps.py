"""Steps shared by the features whose closings of a flow reach the ledger after the asset passed to another flow:
stop (R1.1.5), emergency closing (R3.2.3) and cash-out (R3.4.1), Bug 684.

A scenario module imports them all and declares the fixture `flow_closings` on its own platform; pytest-bdd keeps each
step as a fixture of that module.
"""

from decimal import Decimal

from pytest_bdd import given, then, when

from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.flow_closings import FlowClosings
from tests.support.steps import quoted


@given(quoted('che il registro del flusso "{name}" riporta le sue posizioni aperte'))
def positions_in_ledger(flow_closings: FlowClosings, name: str) -> None:
    flow_closings.positions_in_ledger(name)
    assert flow_closings.totals_of(name).positions


@when(quoted('"{user}" archivia il flusso "{name}" e aggiunge "{asset}" agli asset del flusso "{other}"'))
@when(quoted('"{user}" ferma e archivia il flusso "{name}" e aggiunge "{asset}" agli asset del flusso "{other}"'))
def asset_passes(flow_closings: FlowClosings, user: str, name: str, asset: str, other: str) -> None:
    flow_closings.asset_passes(user, name, asset, other)
    assert asset in flow_closings.flow(other).configuration.assets


@when(quoted('il flusso "{name}" esegue un ciclo che registra le esecuzioni delle chiusure'))
def cycle_records(flow_closings: FlowClosings, name: str) -> None:
    flow_closings.run_cycle(name)


@then(
    quoted('il registro del flusso "{name}" riporta le chiusure su "{first}" e "{second}" e nessuna posizione aperta')
)
def closings_of_flow(flow_closings: FlowClosings, name: str, first: str, second: str) -> None:
    assert flow_closings.closings_recorded_for(name) == sorted((first, second))
    assert set(flow_closings.totals_of(name).positions.values()) <= {Decimal(0)}


@then(quoted('il registro del flusso "{name}" riporta la chiusura su "{asset}" e nessuna posizione aperta'))
def closing_of_flow(flow_closings: FlowClosings, name: str, asset: str) -> None:
    assert flow_closings.closings_recorded_for(name) == [asset]
    assert set(flow_closings.totals_of(name).positions.values()) <= {Decimal(0)}


@then(quoted('il registro del flusso "{name}" non ha una posizione su "{asset}"'))
def no_position_of_flow(flow_closings: FlowClosings, name: str, asset: str) -> None:
    assert flow_closings.totals_of(name).expected(asset) == 0


@then(quoted('il flusso "{name}" non è in pausa'))
def not_paused(flow_closings: FlowClosings, name: str) -> None:
    flow = flow_closings.flow(name)
    assert flow.status is FlowStatus.ACTIVE
    assert flow.id not in flow_closings.platform.flows.pause_reasons
