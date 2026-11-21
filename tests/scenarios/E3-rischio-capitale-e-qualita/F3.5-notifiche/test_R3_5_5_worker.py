"""The scenarios of R3.5.5 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_5_5 import *  # noqa: F403 - the steps of R3.5.5, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.5-notifiche/R3.5.5-server-di-posta-dell-utente/worker/R3.5.5-server-di-posta-dell-utente.feature"
)
