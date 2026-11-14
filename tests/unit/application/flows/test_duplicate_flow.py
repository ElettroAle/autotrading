import logging

import pytest

from autotrading.application.flows.duplicate_flow import DuplicateFlowCommand
from autotrading.application.flows.errors import (
    FlowNameInUseError,
    FlowNotFoundError,
)
from autotrading.domain.flows.flow import FIRST_VERSION
from autotrading.domain.flows.flow_name import FlowName
from autotrading.domain.flows.flow_status import FlowStatus
from autotrading.domain.tenancy.tenant_id import TenantId
from tests.support.drafts import Drafts
from tests.support.flows import a_flow


@pytest.fixture
def drafts() -> Drafts:
    return Drafts()


def test_the_copy_is_saved_as_a_draft_with_the_strategy_at_its_first_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture
) -> None:
    original = drafts.original()

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        copy = drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    assert drafts.repository.get(copy.id) == copy
    assert (copy.name, copy.status, copy.account_id, copy.configuration.version) == (
        FlowName("alfa (copia)"),
        FlowStatus.DRAFT,
        None,
        FIRST_VERSION,
    )
    assert drafts.repository.get(original.id) == original
    assert [(record.getMessage(), record.__dict__["flow_id"]) for record in caplog.records] == [
        ("flusso duplicato", str(copy.id.value))
    ]


def test_a_copy_whose_name_is_taken_is_refused(drafts: Drafts) -> None:
    original = drafts.original()
    drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    with pytest.raises(FlowNameInUseError):
        drafts.duplicate.execute(DuplicateFlowCommand(original.id))

    assert len(drafts.repository.list()) == 2


def test_a_flow_of_another_tenant_is_not_duplicated(drafts: Drafts) -> None:
    stranger = a_flow(TenantId.new())

    with pytest.raises(FlowNotFoundError):
        drafts.duplicate.execute(DuplicateFlowCommand(stranger.id))
