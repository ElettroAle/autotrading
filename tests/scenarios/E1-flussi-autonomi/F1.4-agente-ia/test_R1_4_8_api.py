"""The scenarios of R1.4.8 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_4_8 import *  # noqa: F403 - the steps of R1.4.8, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.4-agente-ia/R1.4.8-system-prompt-personalizzabile/api/R1.4.8-system-prompt-personalizzabile.feature"
)
