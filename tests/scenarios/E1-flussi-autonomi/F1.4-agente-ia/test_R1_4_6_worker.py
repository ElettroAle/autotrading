"""The scenarios of R1.4.6 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_4_6 import *  # noqa: F403 - the steps of R1.4.6, shared by its files

scenarios("E1-flussi-autonomi/F1.4-agente-ia/R1.4.6-costo-delle-chiamate/worker/R1.4.6-costo-delle-chiamate.feature")
