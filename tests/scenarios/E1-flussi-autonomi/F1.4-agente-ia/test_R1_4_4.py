import pytest
from pytest_bdd import scenarios

from tests.support.decision_steps import *  # noqa: F403 - the steps of the decisions of the agent
from tests.support.flow_cycle_steps import *  # noqa: F403 - the steps of the cycles of the worker
from tests.support.opening_steps import *  # noqa: F403 - the steps of the register of the openings
from tests.support.opening_steps import SealedFlowCycles

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.4-decisione-per-asset.feature")


@pytest.fixture(name="flow_cycles")
def sealed_flow_cycles() -> SealedFlowCycles:
    """The keys of the AI providers sealed and opened with libsodium, as an installation does (Bug 179)."""
    return SealedFlowCycles()
