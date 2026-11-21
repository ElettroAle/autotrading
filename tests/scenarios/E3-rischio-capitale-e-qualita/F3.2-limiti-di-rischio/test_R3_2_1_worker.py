"""The scenarios of R3.2.1 that the worker realizes; the steps are shared by every file of the requirement."""

from pytest_bdd import scenarios

from tests.support.steps_r3_2_1 import *  # noqa: F403 - the steps of R3.2.1, shared by its files

scenarios(
    "E3-rischio-capitale-e-qualita/F3.2-limiti-di-rischio/R3.2.1-esposizione-complessiva-massima/worker/R3.2.1-esposizione-complessiva-massima.feature"
)
