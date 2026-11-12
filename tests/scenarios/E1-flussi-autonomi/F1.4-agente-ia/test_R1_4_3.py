from pytest_bdd import scenarios

# A cycle of a real flow on the bridges the worker uses (ADR 0042).
from tests.support.flow_cycle_steps import *  # noqa: F403

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.3-contesto-dell-agente.feature")
