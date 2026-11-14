import logging
from decimal import Decimal
from uuid import uuid4

import pytest

from autotrading.application.flows.assign_draft_flow import AssignDraftFlowCommand
from autotrading.application.flows.errors import (
    AssetNotTradableError,
    FlowAccountNotFoundError,
)
from autotrading.domain.flows.errors import (
    AssetsRequiredError,
    CapitalAboveFreeCapitalError,
    FlowNotDraftError,
)
from autotrading.domain.flows.flow import FIRST_VERSION
from tests.support.drafts import Drafts


@pytest.fixture
def drafts() -> Drafts:
    return Drafts()


def test_the_assignment_saves_account_capital_and_assets_as_the_next_version(
    drafts: Drafts, caplog: pytest.LogCaptureFixture
) -> None:
    draft = drafts.draft()
    command = AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ("eth", "sol"))

    with caplog.at_level(logging.INFO, logger="autotrading.flows"):
        assigned = drafts.assign.execute(command)

    assert assigned == draft.assigned(drafts.account_id, Decimal(200), ("ETH", "SOL"))
    assert drafts.repository.get(draft.id) == assigned
    assert drafts.repository.version(draft.id, FIRST_VERSION) == draft.configuration
    assert [(record.getMessage(), record.__dict__["version"]) for record in caplog.records] == [("bozza assegnata", 2)]


def test_an_assignment_on_an_account_of_another_tenant_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowAccountNotFoundError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, uuid4(), Decimal(200), ("ETH",)))

    assert drafts.repository.get(draft.id) == draft


def test_an_assignment_without_assets_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetsRequiredError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ()))


def test_an_assignment_with_an_asset_the_exchange_does_not_trade_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(AssetNotTradableError):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(200), ("DOGE",)))


def test_an_assignment_above_the_free_capital_is_refused(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(CapitalAboveFreeCapitalError, match=r"900 USDC"):
        drafts.assign.execute(AssignDraftFlowCommand(draft.id, drafts.account_id, Decimal(901), ("ETH",)))


def test_a_flow_out_of_draft_is_not_assigned(drafts: Drafts) -> None:
    original = drafts.original()

    with pytest.raises(FlowNotDraftError):
        drafts.assign.execute(AssignDraftFlowCommand(original.id, drafts.account_id, Decimal(50), ("ETH",)))

    assert drafts.repository.get(original.id) == original
