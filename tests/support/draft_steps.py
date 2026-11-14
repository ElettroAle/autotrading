"""Steps shared by the features that make a draft: assigning account, capital and assets, and starting it.

A scenario module imports them all, beside those of the life of a flow; pytest-bdd keeps each step as a fixture of
that module. The module that makes the draft (a copy, an imported file) names it in the `draft` fixture.
"""

from decimal import Decimal

import pytest
from pytest_bdd import then, when

from autotrading.application.flows.assign_draft_flow import AssignDraftFlowCommand
from autotrading.application.flows.change_flow_status import ChangeFlowStatusCommand
from autotrading.domain.flows.errors import AssetsAssignedToOtherFlowError
from autotrading.domain.flows.flow_action import FlowAction
from tests.support.flows import account_id_of
from tests.support.lifecycle_steps import Lifecycle, attempt, flow_named
from tests.support.platform import Platform
from tests.support.steps import quoted


class Draft:
    """The draft a scenario talks about, by its name."""

    def __init__(self) -> None:
        self.name = ""


@pytest.fixture
def draft() -> Draft:
    return Draft()


@then("non ha conto, capitale allocato né asset")
def draft_without_assignment(platform: Platform, lifecycle: Lifecycle, draft: Draft) -> None:
    flow = flow_named(platform, lifecycle.user, draft.name)
    assert (flow.account_id, flow.configuration.allocated_capital, flow.configuration.assets) == (None, None, ())


@when(quoted('"{user}" assegna al flusso "{name}" il conto "{account}", {capital} USDC e l\'asset "{asset}"'))
def assign(
    platform: Platform, lifecycle: Lifecycle, user: str, name: str, *, account: str, capital: str, asset: str
) -> None:
    command = AssignDraftFlowCommand(
        flow_named(platform, user, name).id, account_id_of(platform, user, account), Decimal(capital), (asset,)
    )
    attempt(lifecycle, lambda: platform.use_cases_of(user).assign_draft_flow.execute(command))
    assert lifecycle.error is None


@when(quoted('"{user}" avvia il flusso "{name}" senza assegnare conto, capitale e asset'))
@when(quoted('"{user}" avvia il flusso "{name}"'))
def start(platform: Platform, lifecycle: Lifecycle, user: str, name: str) -> None:
    change = ChangeFlowStatusCommand(flow_named(platform, user, name).id, FlowAction.START)
    attempt(lifecycle, lambda: platform.use_cases_of(user).change_flow_status.execute(change))


@then(quoted('l\'avvio è rifiutato perché "{asset}" è già usato dal flusso "{other}" sul conto "{account}"'))
def start_refused_for_asset(
    platform: Platform, lifecycle: Lifecycle, draft: Draft, *, asset: str, other: str, account: str
) -> None:
    error = lifecycle.error
    assert isinstance(error, AssetsAssignedToOtherFlowError)
    assert (error.flow, error.assets) == (other, (asset,))
    account_id = account_id_of(platform, lifecycle.user, account)
    assert flow_named(platform, lifecycle.user, other).account_id == account_id
    assert flow_named(platform, lifecycle.user, draft.name).account_id == account_id
