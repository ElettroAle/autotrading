from pytest_bdd import scenarios

from tests.support.decision_steps import *  # noqa: F403 - the steps of the decisions of the agent
from tests.support.flow_cycle_steps import *  # noqa: F403 - the steps of the cycles of the worker

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.4-decisione-per-asset.feature")
