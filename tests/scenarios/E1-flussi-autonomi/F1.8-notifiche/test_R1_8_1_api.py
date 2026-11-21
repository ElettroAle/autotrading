"""The scenarios of R1.8.1 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_8_1 import *  # noqa: F403 - the steps of R1.8.1, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.8-notifiche/R1.8.1-collegamento-di-telegram/api/R1.8.1-collegamento-di-telegram.feature"
)
