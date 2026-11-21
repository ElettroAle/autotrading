"""The scenarios of R1.6.1 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r1_6_1 import *  # noqa: F403 - the steps of R1.6.1, shared by its files

scenarios(
    "E1-flussi-autonomi/F1.6-capitale-dei-flussi/R1.6.1-stato-del-flusso-dall-exchange/worker/R1.6.1-stato-del-flusso-dall-exchange.feature"
)
