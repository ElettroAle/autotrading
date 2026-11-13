"""A cycle is taken and recorded in the tenant its flow was planned for, never in another one (ADR 0046)."""

from collections.abc import Iterator
from uuid import uuid4

import pytest

from autotrading.application.cycles.run_cycle import RunCycleCommand
from autotrading.domain.cycles.cycle_record import CycleOutcome
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.cycles import Cycles, at


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    yield world
    world.release()


def test_a_cycle_is_recorded_in_the_tenant_of_its_flow(cycles: Cycles) -> None:
    other = TenantId(uuid4())
    cycles.add_flow("alfa", anchor="10:22:00")
    cycles.add_flow("beta", anchor="10:22:00", tenant_id=other)
    cycles.clock.current = at("10:22:00")

    cycles.run_cycle().execute(RunCycleCommand(cycles.id_of("beta"), cycles.flow("beta").schedule, at("10:22:00")))

    assert [record.flow_id for record in cycles.records_of_tenants[other].records] == [cycles.id_of("beta")]
    assert cycles.records.records == []
    assert cycles.records_of_tenants[other].records[0].outcome is CycleOutcome.COMPLETED


def test_a_cycle_already_taken_in_the_tenant_of_its_flow_is_not_run_again(cycles: Cycles) -> None:
    cycles.add_flow("alfa", anchor="10:22:00")
    cycles.clock.current = at("10:22:00")
    command = RunCycleCommand(cycles.id_of("alfa"), cycles.flow("alfa").schedule, at("10:22:00"))

    first = cycles.run_cycle().execute(command)
    second = cycles.run_cycle().execute(command)

    assert first is not None
    assert second is None
