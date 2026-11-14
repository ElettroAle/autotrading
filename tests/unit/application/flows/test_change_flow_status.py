from dataclasses import replace
from decimal import Decimal

import pytest

from autotrading.application.flows.errors import (
    AssetUnderVerificationError,
    FlowAccountNotFoundError,
)
from autotrading.domain.flows.errors import (
    AssetsAssignedToOtherFlowError,
    CapitalAboveFreeCapitalError,
    FlowAssignmentMissingError,
)
from autotrading.domain.flows.flow_status import FlowStatus
from tests.support.drafts import Drafts


@pytest.fixture
def drafts() -> Drafts:
    return Drafts()


def test_an_assigned_draft_starts(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()

    started = drafts.start(draft)

    assert started == replace(draft, status=FlowStatus.ACTIVE)
    assert drafts.repository.get(draft.id).status is FlowStatus.ACTIVE


def test_a_draft_without_assignment_does_not_start(drafts: Drafts) -> None:
    draft = drafts.draft()

    with pytest.raises(FlowAssignmentMissingError, match=r"^conto, capitale allocato e asset mancanti$"):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_sharing_an_asset_with_a_flow_of_its_account_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft(assets=("BTC",))

    with pytest.raises(AssetsAssignedToOtherFlowError) as refused:
        drafts.start(draft)

    assert (refused.value.flow, refused.value.assets) == ("alfa", ("BTC",))
    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_above_the_free_capital_of_now_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft(capital=800)
    drafts.accounts.balances[drafts.account_id] = Decimal(500)

    with pytest.raises(CapitalAboveFreeCapitalError):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT


def test_a_draft_whose_account_was_removed_does_not_start(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()
    del drafts.accounts.exchanges[drafts.account_id]

    with pytest.raises(FlowAccountNotFoundError):
        drafts.start(draft)


def test_a_draft_does_not_start_on_an_asset_under_verification(drafts: Drafts) -> None:
    draft = drafts.assigned_draft()
    drafts.running_verifications.add((drafts.account_id, "ETH"))

    with pytest.raises(AssetUnderVerificationError):
        drafts.start(draft)

    assert drafts.repository.get(draft.id).status is FlowStatus.DRAFT
