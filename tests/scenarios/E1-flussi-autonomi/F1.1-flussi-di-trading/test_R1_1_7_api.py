"""The scenarios of R1.1.7 that the api realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_1_7 import *  # noqa: F403 - the steps of R1.1.7, shared by its files

scenarios("E1-flussi-autonomi/F1.1-flussi-di-trading/R1.1.7-capitale-allocato/api/R1.1.7-capitale-allocato.feature")
