import pytest

from autotrading.application.flows.errors import FlowNotFoundError
from autotrading.application.flows.export_flow_strategy import (
    ExportedFlowStrategy,
    ExportFlowStrategyCommand,
)
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.flows.flow_strategy import FlowStrategy
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.flows import a_flow
from tests.support.strategies import Strategies


@pytest.fixture
def strategies() -> Strategies:
    return Strategies()


def test_the_export_gives_the_strategy_of_the_version_in_force_with_the_flow_name(strategies: Strategies) -> None:
    original = strategies.original()

    exported = strategies.export.execute(ExportFlowStrategyCommand(original.id))

    assert exported == ExportedFlowStrategy(original.name, FlowStrategy.of(original.configuration))


def test_an_archived_flow_still_exports_its_strategy(strategies: Strategies) -> None:
    original = strategies.original(FlowStatus.ARCHIVED)

    exported = strategies.export.execute(ExportFlowStrategyCommand(original.id))

    assert exported.strategy == FlowStrategy.of(original.configuration)


def test_a_flow_of_another_tenant_is_not_exported(strategies: Strategies) -> None:
    stranger = a_flow(TenantId.new())

    with pytest.raises(FlowNotFoundError):
        strategies.export.execute(ExportFlowStrategyCommand(stranger.id))
