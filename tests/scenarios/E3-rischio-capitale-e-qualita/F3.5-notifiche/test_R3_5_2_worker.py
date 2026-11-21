"""The scenarios of R3.5.2 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_5_2 import *  # noqa: F403 - the steps of R3.5.2, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.2-notifiche-via-email/worker/R3.5.2-notifiche-via-email.feature"
)
