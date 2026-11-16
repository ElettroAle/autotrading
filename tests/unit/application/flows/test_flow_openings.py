from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.resume_flow_openings import ResumeFlowOpeningsCommand, ResumeFlowOpeningsUseCase
from autotrading.domain.flows.errors import OpeningsNotSuspendedError
from autotrading.domain.flows.flow import Flow
from autotrading.domain.flows.flow_id import FlowId
from autotrading.domain.flows.openings_resume import OpeningsResume
from autotrading.domain.flows.openings_suspension import OpeningsStatus, OpeningsSuspension
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.fakes.flow_repository import FlowStore, InMemoryFlowRepositoryAdapter
from tests.fakes.openings_suspension import InMemoryOpeningsSuspensionAdapter
from tests.support.flows import a_configuration, a_flow

TENANT = TenantId.new()
SUSPENDED_AT = datetime(2026, 11, 16, 10, tzinfo=UTC)
NEXT_MIDNIGHT = datetime(2026, 11, 17, tzinfo=UTC)
SUSPENSION = OpeningsSuspension("perdita giornaliera 6% oltre il 5%", SUSPENDED_AT)


class World:
    """A flow of the tenant with the suspension of its openings, resumed at the instant of the clock."""

    def __init__(self, resume: OpeningsResume = OpeningsResume.MANUAL) -> None:
        self.store = FlowStore()
        self.flow: Flow = a_flow(TENANT, configuration=replace(a_configuration(), openings_resume=resume))
        self.store.flows.append(self.flow)
        self.openings = InMemoryOpeningsSuspensionAdapter(self.store, TENANT)
        self.now = SUSPENDED_AT + timedelta(hours=1)
        flows = InMemoryFlowRepositoryAdapter(self.store, TENANT)
        self.resume = ResumeFlowOpeningsUseCase(flows, self.openings, lambda: self.now)

    def suspended(self) -> None:
        self.openings.suspend(self.flow.id.value, SUSPENSION)

    def suspension(self) -> OpeningsSuspension | None:
        return self.openings.status(self.flow.id.value).at(self.now, self.flow.configuration.openings_resume).suspension


def test_the_user_resumes_suspended_openings_and_the_peak_counts_again_from_now() -> None:
    world = World()
    world.suspended()

    resumed = world.resume.execute(ResumeFlowOpeningsCommand(world.flow.id))

    assert resumed == OpeningsStatus(None, world.now)
    assert world.openings.status(world.flow.id.value) == OpeningsStatus(None, world.now)
    assert world.suspension() is None


def test_the_user_may_resume_before_the_next_day() -> None:
    world = World(OpeningsResume.NEXT_DAY)
    world.suspended()

    world.resume.execute(ResumeFlowOpeningsCommand(world.flow.id))

    assert world.openings.status(world.flow.id.value) == OpeningsStatus(None, world.now)


def test_openings_not_suspended_cannot_be_resumed() -> None:
    world = World()

    with pytest.raises(OpeningsNotSuspendedError, match=r"^le aperture di alfa non sono sospese$"):
        world.resume.execute(ResumeFlowOpeningsCommand(world.flow.id))


def test_a_next_day_suspension_already_lifted_cannot_be_resumed_again() -> None:
    world = World(OpeningsResume.NEXT_DAY)
    world.suspended()
    world.now = NEXT_MIDNIGHT

    with pytest.raises(OpeningsNotSuspendedError):
        world.resume.execute(ResumeFlowOpeningsCommand(world.flow.id))


def test_the_openings_of_a_flow_of_another_tenant_are_not_found() -> None:
    world = World()
    stranger = FlowId.new()

    with pytest.raises(FlowNotFoundError):
        world.resume.execute(ResumeFlowOpeningsCommand(stranger))
