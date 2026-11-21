"""The scenarios of R1.7.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_7_1 import *  # noqa: F403 - the steps of R1.7.1, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.1-registrazione-del-ciclo/api/R1.7.1-registrazione-del-ciclo.feature"
)
