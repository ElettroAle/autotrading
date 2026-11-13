from collections.abc import Iterator

import pytest

from autotrading.domain.flows.cycle_record import CycleOutcome
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.cycles import Cycles, at


@pytest.fixture
def cycles() -> Iterator[Cycles]:
    world = Cycles()
    yield world
    world.release()


def test_no_cycle_is_launched_before_the_first_planned_instant(cycles: Cycles) -> None:
    cycles.add_flow("alfa", anchor="10:22:00")

    cycles.tick("10:21:59")

    assert cycles.launcher.threads == []


def test_every_active_flow_runs_its_due_cycle(cycles: Cycles) -> None:
    cycles.add_flow("alfa", anchor="10:00:00")
    cycles.add_flow("beta", minutes=10, anchor="10:05:00")

    cycles.tick("10:16:00")

    assert cycles.record_at("alfa", "10:15:00").outcome is CycleOutcome.COMPLETED
    assert cycles.record_at("beta", "10:15:00").outcome is CycleOutcome.COMPLETED


def test_a_flow_not_yet_due_does_not_stop_the_next_one(cycles: Cycles) -> None:
    cycles.add_flow("alfa", anchor="11:00:00")
    cycles.add_flow("beta")

    cycles.tick("10:15:00")

    assert cycles.record_at("beta", "10:15:00").outcome is CycleOutcome.COMPLETED
    assert cycles.records_of("alfa") == []


def test_a_paused_flow_runs_no_cycle(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.pause("alfa")

    cycles.tick("10:15:00")

    assert cycles.launcher.threads == []


def test_a_missed_backlog_runs_only_the_latest_due_cycle(cycles: Cycles) -> None:
    cycles.add_flow("alfa")

    cycles.tick("11:01:00")
    cycles.launcher.settle()

    assert [record.planned_at for record in cycles.records_of("alfa")] == [at("11:00:00")]


def test_a_slow_flow_does_not_hold_the_others(cycles: Cycles) -> None:
    cycles.add_flow("alfa")
    cycles.add_flow("beta")

    cycles.hold("alfa", "10:15:00")

    assert cycles.record_at("beta", "10:15:00").outcome is CycleOutcome.COMPLETED
    assert cycles.records_of("alfa") == []


def test_each_cycle_runs_on_the_ports_of_the_tenant_of_its_flow(cycles: Cycles) -> None:
    anna, bruno = TenantId.new(), TenantId.new()
    cycles.add_flow("alfa", tenant_id=anna)
    cycles.add_flow("beta", tenant_id=bruno)
    cycles.add_flow("gamma", anchor="11:00:00", tenant_id=bruno)

    cycles.tick("10:15:00")

    assert sorted(cycles.cycle_tenants, key=str) == sorted([anna, bruno], key=str)
    assert cycles.planned.tenants() == {anna, bruno}
