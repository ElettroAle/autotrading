"""The scenarios of R1.4.1 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_4_1 import *  # noqa: F403 - the steps of R1.4.1, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.4-agente-ia/R1.4.1-chiavi-dei-fornitori-ia/worker/R1.4.1-chiavi-dei-fornitori-ia.feature"
)
